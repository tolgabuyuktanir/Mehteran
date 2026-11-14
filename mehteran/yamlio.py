"""YAML in and out, through the vendored PyYAML's safe loader and safe dumper only.

The loader also rejects a key that appears twice in one mapping: PyYAML would silently keep the last value.
dump_readable() writes what the visual editor saves: multi-line texts as "|" blocks, short lists and mappings on
one line, indented lists. PyYAML drops comments; keep_comments() puts them back into a newly written file next to
the key or list entry they stood before (entries are found by their id), and counts the ones it cannot place.
"""

from __future__ import annotations

import re

from ._vendor import yaml


class YAMLError(ValueError):
    pass


class _StrictSafeLoader(yaml.SafeLoader):
    """SafeLoader that reports duplicate keys instead of overwriting them. No other constructors are added."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=True)
            try:
                duplicate = key in seen
            except TypeError:  # an unhashable key: the safe loader reports it itself
                continue
            if duplicate:
                raise yaml.constructor.ConstructorError(None, None, f"duplicate key {key!r}", key_node.start_mark)
            seen.add(key)
        return super().construct_mapping(node, deep)


def load(text: str):
    try:
        return yaml.load(text, Loader=_StrictSafeLoader)  # noqa: S506 - a SafeLoader subclass
    except yaml.YAMLError as e:
        raise YAMLError(str(e)) from None


def dump(data) -> str:
    return yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=110)


FLOW_LIMIT = 72  # a list or mapping of short scalars up to this many characters is written on one line


def _flow_size(value) -> int | None:
    """The approximate one-line length of value, or None when it must not be written on one line."""
    if isinstance(value, str):
        return None if "\n" in value or len(value) > FLOW_LIMIT else len(value) + 2
    if value is None or isinstance(value, (bool, int, float)):
        return 5
    if isinstance(value, dict):
        sizes = [_flow_size(k) for k in value] + [_flow_size(v) for v in value.values()]
    elif isinstance(value, list):
        sizes = [_flow_size(v) for v in value]
    else:
        return None
    return None if None in sizes else sum(sizes) + 2 * len(sizes) + 2


class _ReadableDumper(yaml.SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow, False)  # "  - item" under its key, as people write it


def _str(dumper, value):
    style = "|" if "\n" in value else None  # the emitter falls back to quotes when a block cannot hold the text
    return dumper.represent_scalar("tag:yaml.org,2002:str", value, style=style)


def _flow(value) -> bool:
    if isinstance(value, list) and any(isinstance(v, dict) for v in value):
        return False  # a list of entries (inputs, options): one entry per line
    size = _flow_size(value)
    return size is not None and size <= FLOW_LIMIT and bool(value)


_ReadableDumper.add_representer(str, _str)
_ReadableDumper.add_representer(dict, lambda d, v: d.represent_mapping("tag:yaml.org,2002:map", v.items(), flow_style=_flow(v)))
_ReadableDumper.add_representer(list, lambda d, v: d.represent_sequence("tag:yaml.org,2002:seq", v, flow_style=_flow(v)))


def dump_readable(data: dict, spaced: tuple = (), spaced_items: str = "") -> str:
    """data as readable YAML. spaced: top-level keys that get an empty line before them; spaced_items: a top-level
    list whose items are separated by empty lines. Empty lines change nothing in what the text means."""
    text = yaml.dump(data, Dumper=_ReadableDumper, allow_unicode=True, sort_keys=False, width=110,
                     default_flow_style=False)
    lines, section = [], ""
    for line in text.splitlines():
        if line and not line.startswith((" ", "-", "#")):
            section = line.split(":", 1)[0]
            if section in spaced and lines:
                lines.append("")
        elif section == spaced_items and line.startswith("  - ") and lines and not lines[-1].endswith(":"):
            lines.append("")
        lines.append(line)
    return "\n".join(lines) + "\n"


def _comment_starts(text: str) -> dict[int, int]:
    """{line: column} of each comment (from 0). Found with the scanner: a "#" inside a text value (a Markdown
    heading in a prompt) is content, not a comment. Empty for text that cannot be scanned."""
    try:
        spans = [(tok.start_mark.index, tok.end_mark.index) for tok in yaml.scan(text, Loader=yaml.SafeLoader)
                 if isinstance(tok, yaml.ScalarToken)]
    except yaml.YAMLError:
        return {}
    found, s = {}, 0
    for m in re.finditer(r"(?:^|(?<=\s))#", text, re.M):
        while s < len(spans) and spans[s][1] <= m.start():
            s += 1
        if s < len(spans) and spans[s][0] <= m.start() < spans[s][1]:
            continue
        line = text.count("\n", 0, m.start())
        if line not in found:
            found[line] = m.start() - (text.rfind("\n", 0, m.start()) + 1)
    return found


def comments(text: str) -> list[int]:
    """The line numbers (from 0) that hold a comment."""
    return sorted(_comment_starts(text))


def _anchors(text: str) -> list[tuple[int, tuple]]:
    """(line, path) of every mapping key and list entry. A list entry is named by its id (or "from->to" for a
    connection, or its value), so that it is found again after entries were added, removed or moved."""
    out: list[tuple[int, tuple]] = []

    def name(item, n: int) -> str:
        if isinstance(item, yaml.MappingNode):
            keys = {k.value: v.value for k, v in item.value
                    if isinstance(k, yaml.ScalarNode) and isinstance(v, yaml.ScalarNode)}
            if "id" in keys:
                return f"id={keys['id']}"
            if "from" in keys and "to" in keys:
                return f"{keys['from']}->{keys['to']}"
        elif isinstance(item, yaml.ScalarNode):
            return f"={item.value}"
        return f"#{n}"

    def walk(node, path: tuple) -> None:
        if isinstance(node, yaml.MappingNode):
            for key, value in node.value:
                here = path + (key.value if isinstance(key, yaml.ScalarNode) else "?",)
                out.append((key.start_mark.line, here))
                walk(value, here)
        elif isinstance(node, yaml.SequenceNode):
            for n, item in enumerate(node.value):
                here = path + (name(item, n),)
                out.append((item.start_mark.line, here))
                walk(item, here)

    walk(yaml.compose(text, Loader=yaml.SafeLoader), ())
    return out


def keep_comments(old: str, new: str) -> tuple[str, int]:
    """new (a file written anew from the same workflow) with the comments of old put back: a comment above a key or
    list entry goes above the same key or entry in new, a comment at the end of a line goes on its own line above
    that line's key, comments at the top or the end of the file stay there. Returns the text and the number of
    comment lines that could not be placed (their key or entry is gone). The result must load to the same data as
    new; otherwise new is returned unchanged with every comment counted as lost."""
    found = _comment_starts(old)
    if not found:
        return new, 0
    try:
        old_anchors, new_anchors = _anchors(old), _anchors(new)
    except yaml.YAMLError:
        return new, len(found)
    old_lines = old.splitlines()
    first_line = min((line for line, _ in old_anchors), default=len(old_lines))
    new_place: dict[tuple, int] = {}
    for line, path in new_anchors:
        new_place.setdefault(path, line)
    lines = new.splitlines()
    before: dict[int, list[str]] = {}
    head, tail, lost = [], [], 0
    for line, column in sorted(found.items()):
        comment = old_lines[line][column:].rstrip()
        if line < first_line and not old_lines[line][:column].strip():
            head.append(comment)
            continue
        own_line = not old_lines[line][:column].strip()
        at = min((l for l, _ in old_anchors if (l > line if own_line else l == line)), default=None)
        if at is None:
            tail.append(comment)
            continue
        path = min((len(p), p) for l, p in old_anchors if l == at)[1]  # the outermost key or entry on that line
        if path not in new_place:
            lost += 1
            continue
        target = new_place[path]
        indent = re.match(r"\s*", lines[target]).group(0)
        before.setdefault(target, []).append(indent + comment)
    out = list(head)
    for n, text in enumerate(lines):
        out += before.get(n, [])
        out.append(text)
    out += tail
    result = "\n".join(out) + "\n"
    try:
        if load(result) != load(new):
            return new, len(found)
    except YAMLError:
        return new, len(found)
    return result, lost


def header(text: str) -> str:
    """The comment lines at the very top of the text (a file's header note), with their line ends."""
    m = re.match(r"(?:#[^\n]*\n)+", text)
    return m.group(0) if m else ""
