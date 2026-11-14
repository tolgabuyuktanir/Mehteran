"""The workflow file (YAML, schema_version 1) and its strict check.

check() collects every problem instead of stopping at the first, so that a user sees all of them at once.
A problem is (where, message key, values); the message is rendered in the request's language (i18n.py).

    schema_version: 1
    id: my-review                     # lower case letters, digits, "-" and "_"
    name: {tr: ..., en: ...}          # a string or a {tr, en} map; the same for description and labels
    description: ...
    version: "1.0"
    category: research
    inputs:  [{id, type: file|text|choice|provider|language, label, description, required, default, formats, multiple, options,
               multiline}]
    nodes:   [{id, type, label, config: {...}, retries, timeout}]
    connections: [{from: node.output (or node), to: node}]
    outputs: [{id, from: node.output, label}]
    layout:  {<node id>: {x, y}}      # optional: where the editor draws each node; the engine ignores it

Data passes between nodes only through {{inputs.<id>}} and {{nodes.<id>.<output>}} placeholders. A node may use
the output of another node only when a connection joins them, so the drawn graph is the real data flow.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field

from . import languages, placeholders, yamlio
from .i18n import t
from .nodes import FORMATS, ID_RE, OPERATORS, PROVIDER_RE, REGISTRY

SCHEMA_VERSION = 1
INPUT_TYPES = ("file", "text", "choice", "provider", "language", "url")  # url: a web page that document.extract reads
FILE_FORMATS = ("pdf", "docx", "epub", "md", "txt", "csv", "tsv", "xlsx",  # pipeline.documents, and tables.py
                "png", "jpg", "jpeg", "tif", "tiff",  # images: read by OCR (ocr.py)
                "odt", "rtf",  # read by Pandoc (pandoc.py)
                "mp3", "wav", "m4a", "ogg", "opus", "flac", "aac", "mp4", "webm", "mov", "mkv")  # speech to text (speech.py)
MAX_FILES = 20  # files of one input with "multiple: true"
TEXT_LIMIT = 200_000
LIMITS = {"nodes": 100, "inputs": 30, "connections": 400, "outputs": 30}

# The key orders are also the order in which the editor writes a workflow file (dump()).
TOP_ORDER = ("schema_version", "id", "based_on", "author", "name", "description", "version", "category", "tier", "privacy",
             "inputs", "nodes", "connections", "outputs", "layout")  # author: who shared the file ("Share", sharing.py)
# privacy: "local": every model call of a run stays on this computer (engine.start refuses any other provider)
INPUT_ORDER = ("id", "type", "label", "description", "required", "default", "formats", "multiple", "options",
               "multiline")
NODE_ORDER = ("id", "type", "label", "retries", "timeout", "fallback_provider", "config")
TOP_KEYS, INPUT_KEYS, NODE_KEYS = set(TOP_ORDER), set(INPUT_ORDER), set(NODE_ORDER)
CONNECTION_KEYS = {"from", "to"}
OUTPUT_KEYS = {"id", "from", "label"}
OPTION_KEYS = {"value", "label"}
POSITION_LIMIT = 100_000  # layout coordinates, in canvas pixels

# Credentials never belong in a workflow file: it is shared, exported and frozen into every run.
CREDENTIAL_KEY = re.compile(r"api[_-]?key|token|secret|passw|credential|private[_-]?key|bearer|\bauth\b|authorization|"
                            r"cookie|session[_-]?id", re.I)
CREDENTIAL_VALUE = re.compile(r"\b(sk-(ant-)?[A-Za-z0-9_-]{20,}|AIza[0-9A-Za-z_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|"
                              r"xox[abpr]-[A-Za-z0-9-]{10,}|AKIA[0-9A-Z]{16})")


@dataclass
class Problem:
    where: str
    key: str
    values: dict = field(default_factory=dict)

    def message(self) -> str:
        text = t(self.key, **self.values)
        return f"{self.where}: {text}" if self.where else text

    def item(self) -> dict:
        """For the editor: the place (marks the node or field) and the message without the place."""
        return {"where": self.where, "message": t(self.key, **self.values)}


class WorkflowError(ValueError):
    def __init__(self, problems: list[Problem]):
        self.problems = problems
        super().__init__("\n".join(p.message() for p in problems))

    def messages(self) -> list[str]:
        return [p.message() for p in self.problems]

    def items(self) -> list[dict]:
        return [p.item() for p in self.problems]


@dataclass
class Workflow:
    data: dict
    inputs: dict[str, dict]
    nodes: dict[str, dict]
    upstream: dict[str, set[str]]       # node -> the nodes it waits for
    order: list[str]                    # a topological order
    outputs: dict[str, str]             # workflow output id -> "node.port"

    @property
    def id(self) -> str:
        return self.data["id"]

    def incoming(self, node_id: str) -> list[tuple[str, str]]:
        """The connections into node_id as (source node, port or "")."""
        out = []
        for c in self.data.get("connections") or []:
            if c["to"] == node_id:
                source, _, port = str(c["from"]).partition(".")
                out.append((source, port))
        return out

    def ports(self, node_id: str) -> dict[str, str]:
        node = self.nodes[node_id]
        return REGISTRY[node["type"]].outputs(node.get("config") or {})

    def downstream(self, node_id: str) -> set[str]:
        """Every node that depends on node_id, directly or through others."""
        out, todo = set(), [node_id]
        while todo:
            current = todo.pop()
            for other, ups in self.upstream.items():
                if current in ups and other not in out:
                    out.add(other)
                    todo.append(other)
        return out

    def graph(self) -> dict:
        """Nodes with their layer (longest path from a start node) and the edges: for the drawing."""
        layer: dict[str, int] = {}
        for node_id in self.order:
            layer[node_id] = max((layer[u] + 1 for u in self.upstream[node_id]), default=0)
        edges = []
        for c in self.data.get("connections") or []:
            source, _, port = str(c["from"]).partition(".")
            edges.append({"from": source, "port": port, "to": c["to"]})
        return {"nodes": [{"id": n, "type": self.nodes[n]["type"], "label": self.nodes[n].get("label"),
                           "layer": layer[n], "ports": list(self.ports(n))} for n in self.order], "edges": edges,
                "layout": self.data.get("layout") or {}}


def parse(text: str) -> Workflow:
    """YAML text -> a checked Workflow. Raises WorkflowError with all problems."""
    if len(text) > 1_000_000:
        raise WorkflowError([Problem("", "yaml_too_large")])
    try:
        data = yamlio.load(text)
    except yamlio.YAMLError as e:
        raise WorkflowError([Problem("", "yaml_invalid", {"error": e})]) from None
    return check(data)


def check(data) -> Workflow:
    problems: list[Problem] = []
    add = lambda where, key, **values: problems.append(Problem(where, key, values))  # noqa: E731
    if not isinstance(data, dict):
        raise WorkflowError([Problem("", "not_a_mapping")])
    _credentials(data, "", add)

    _keys(data, TOP_KEYS, "", add)
    if data.get("schema_version") != SCHEMA_VERSION:
        add("schema_version", "bad_schema_version", version=SCHEMA_VERSION)
    _ident(data.get("id"), "id", add, required=True)
    _localized(data.get("name"), "name", add, required=True)
    _localized(data.get("description"), "description", add)
    for key in ("version", "category", "tier", "based_on", "author"):
        if key in data and not (isinstance(data[key], (str, int, float)) and not isinstance(data[key], bool)
                                and len(str(data[key])) <= 80):
            add(key, "bad_short_text")
    if "privacy" in data and data["privacy"] != "local":
        add("privacy", "bad_privacy")

    inputs = _inputs(data.get("inputs"), add)
    nodes = _nodes(data.get("nodes"), add)
    upstream, connected = _connections(data.get("connections"), nodes, add)
    _references(nodes, inputs, connected, add)
    _fallbacks(nodes, inputs, add)
    order = _order(nodes, upstream, add)
    outputs = _outputs(data.get("outputs"), nodes, add)
    _layout(data.get("layout"), nodes, add)
    if problems:
        raise WorkflowError(problems)
    return Workflow(data, inputs, nodes, upstream, order, outputs)


# --- helpers --------------------------------------------------------------------

def _credentials(value, where: str, add) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            here = f"{where}.{key}" if where else str(key)
            if isinstance(key, str) and CREDENTIAL_KEY.search(key):
                add(here, "credential_key")
            _credentials(item, here, add)
    elif isinstance(value, list):
        for n, item in enumerate(value):
            _credentials(item, f"{where}[{n}]", add)
    elif isinstance(value, str) and CREDENTIAL_VALUE.search(value):
        add(where, "credential_value")


def _keys(item: dict, allowed: set[str], where: str, add) -> None:
    for key in item:
        if key not in allowed:
            add(f"{where}.{key}" if where else str(key), "unknown_key", allowed=", ".join(sorted(allowed)))


def _ident(value, where: str, add, required: bool = False) -> bool:
    if value is None and not required:
        return True
    if not isinstance(value, str) or not ID_RE.match(value):
        add(where, "bad_id", value=value)
        return False
    return True


def _localized(value, where: str, add, required: bool = False) -> None:
    if value is None:
        if required:
            add(where, "missing")
        return
    if isinstance(value, str):
        if not value.strip() or len(value) > 2000:
            add(where, "bad_localized")
        return
    if not isinstance(value, dict) or not value or set(value) - {"tr", "en"} or \
            not all(isinstance(v, str) and v.strip() and len(v) <= 2000 for v in value.values()):
        add(where, "bad_localized")


def _list(value, where: str, add, required: bool = False) -> list:
    if value is None:
        if required:
            add(where, "missing")
        return []
    if not isinstance(value, list):
        add(where, "not_a_list")
        return []
    if len(value) > LIMITS.get(where, 1000):
        add(where, "too_many", limit=LIMITS[where])
    return value


def _entries(value, where: str, add, allowed: set[str], required: bool = False) -> dict[str, dict]:
    """A list of mappings that each have a unique id -> {id: mapping}."""
    out: dict[str, dict] = {}
    for n, item in enumerate(_list(value, where, add, required)):
        here = f"{where}[{n}]"
        if not isinstance(item, dict):
            add(here, "not_a_mapping")
            continue
        if isinstance(item.get("id"), str) and ID_RE.match(item["id"]):
            here = f"{where}.{item['id']}"
        _keys(item, allowed, here, add)
        if not _ident(item.get("id"), f"{here}.id", add, required=True):
            continue
        if item["id"] in out:
            add(here, "duplicate_id", id=item["id"])
            continue
        out[item["id"]] = item
    return out


def _inputs(value, add) -> dict[str, dict]:
    inputs = _entries(value, "inputs", add, INPUT_KEYS)
    for input_id, item in inputs.items():
        here = f"inputs.{input_id}"
        kind = item.get("type")
        if kind not in INPUT_TYPES:
            add(f"{here}.type", "bad_input_type", types=", ".join(INPUT_TYPES))
            continue
        _localized(item.get("label"), f"{here}.label", add)
        _localized(item.get("description"), f"{here}.description", add)
        if "required" in item and not isinstance(item["required"], bool):
            add(f"{here}.required", "not_a_bool")
        for key, only in (("formats", "file"), ("multiple", "file"), ("options", "choice"), ("multiline", "text")):
            if key in item and kind != only:
                add(f"{here}.{key}", "key_only_for", type=only)
        if kind == "file":
            if "default" in item:
                add(f"{here}.default", "file_no_default")
            formats = item.get("formats", list(FILE_FORMATS))
            if not isinstance(formats, list) or not formats or any(f not in FILE_FORMATS for f in formats):
                add(f"{here}.formats", "bad_formats", formats=", ".join(FILE_FORMATS))
            if "multiple" in item and not isinstance(item["multiple"], bool):
                add(f"{here}.multiple", "not_a_bool")
        elif kind == "choice":
            options = item.get("options")
            values = []
            if not isinstance(options, list) or not options:
                add(f"{here}.options", "missing_options")
            else:
                for n, option in enumerate(options):
                    if isinstance(option, dict):
                        _keys(option, OPTION_KEYS, f"{here}.options[{n}]", add)
                        _localized(option.get("label"), f"{here}.options[{n}].label", add)
                        option = option.get("value")
                    if not isinstance(option, str) or not option or len(option) > 200:
                        add(f"{here}.options[{n}]", "bad_option")
                    else:
                        values.append(option)
            if len(set(values)) != len(values):
                add(f"{here}.options", "duplicate_option")
            if "default" in item and item["default"] not in values:
                add(f"{here}.default", "default_not_option")
        elif kind == "provider":
            if "default" in item and not (isinstance(item["default"], str) and PROVIDER_RE.match(item["default"])):
                add(f"{here}.default", "bad_provider", value=item["default"])
        elif kind == "language":  # any language of the registry; without a default: the language of whoever runs it
            if "default" in item and item["default"] not in languages.BY_CODE:
                add(f"{here}.default", "bad_language", value=item["default"])
        elif kind == "text":
            if "default" in item and not (isinstance(item["default"], str) and len(item["default"]) <= TEXT_LIMIT):
                add(f"{here}.default", "bad_text")
            if "multiline" in item and not isinstance(item["multiline"], bool):
                add(f"{here}.multiline", "not_a_bool")
        elif kind == "url" and "default" in item:
            from .urlfetch import url_problem
            if not isinstance(item["default"], str) or (item["default"].strip() and url_problem(item["default"].strip())):
                add(f"{here}.default", "bad_url_default")
    return inputs


def _nodes(value, add) -> dict[str, dict]:
    nodes = _entries(value, "nodes", add, NODE_KEYS, required=True)
    if value is not None and isinstance(value, list) and not value:
        add("nodes", "no_nodes")
    for node_id, node in nodes.items():
        here = f"nodes.{node_id}"
        if not isinstance(node.get("type"), str):
            node["type"] = ""  # a list or a number here: reported below as an unknown type, like any other
        node_type = REGISTRY.get(node["type"])
        if node_type is None:
            add(f"{here}.type", "unknown_node_type", type=node.get("type"), types=", ".join(sorted(REGISTRY)))
            continue
        _localized(node.get("label"), f"{here}.label", add)
        for key, top in (("retries", 10), ("timeout", 86_400)):
            if key not in node:
                continue
            if not node_type.takes_retries:
                add(f"{here}.{key}", "no_retries_for", type=node_type.name)
            elif not isinstance(node[key], int) or isinstance(node[key], bool) or not (0 if key == "retries" else 1) <= node[key] <= top:
                add(f"{here}.{key}", "bad_number", low=0 if key == "retries" else 1, high=top)
        config = node.get("config", {})
        if not isinstance(config, dict):
            add(f"{here}.config", "not_a_mapping")
            node["config"] = {}  # the later checks read it as a mapping
            continue
        _keys(config, set(node_type.config), f"{here}.config", add)
        for key, spec in node_type.config.items():
            where, item = f"{here}.config.{key}", config.get(key)
            if item is None:
                if spec.required:
                    add(where, "missing")
                continue
            if spec.kind == "template" and not (isinstance(item, str) and len(item) <= TEXT_LIMIT):
                add(where, "bad_text")
            elif spec.kind == "localized":
                _localized(item, where, add)
            elif spec.kind == "int" and not (isinstance(item, int) and not isinstance(item, bool) and spec.low <= item <= spec.high):
                add(where, "bad_number", low=spec.low, high=spec.high)
            elif spec.kind == "bool" and not isinstance(item, bool):
                add(where, "not_a_bool")
            elif spec.kind == "choice" and item not in [value for value, _ in spec.options]:
                add(where, "bad_choice", options=", ".join(value for value, _ in spec.options))
            elif spec.kind == "id":
                _ident(item, where, add)
            elif spec.kind == "formats" and not (isinstance(item, list) and item and all(f in FORMATS for f in item)
                                                 and len(set(item)) == len(item)):
                add(where, "bad_formats", formats=", ".join(FORMATS))
    return nodes


def _connections(value, nodes: dict, add) -> tuple[dict[str, set[str]], set[tuple[str, str, str]]]:
    upstream = {node_id: set() for node_id in nodes}
    connected: set[tuple[str, str, str]] = set()   # (source, port or "", target)
    seen = set()
    for n, item in enumerate(_list(value, "connections", add)):
        here = f"connections[{n}]"
        if not isinstance(item, dict):
            add(here, "not_a_mapping")
            continue
        _keys(item, CONNECTION_KEYS, here, add)
        source, target = item.get("from"), item.get("to")
        if not isinstance(source, str) or not isinstance(target, str):
            add(here, "connection_needs_from_to")
            continue
        node_id, _, port = source.partition(".")
        ok = True
        if node_id not in nodes:
            add(f"{here}.from", "unknown_node", id=node_id)
            ok = False
        elif port and REGISTRY.get(nodes[node_id].get("type")) and \
                port not in REGISTRY[nodes[node_id]["type"]].outputs(nodes[node_id].get("config") or {}):
            add(f"{here}.from", "unknown_port", node=node_id, port=port)
            ok = False
        elif not port and nodes[node_id].get("type") == "condition":
            add(f"{here}.from", "condition_needs_port", node=node_id)
            ok = False
        if target not in nodes:
            add(f"{here}.to", "unknown_node", id=target)
            ok = False
        if ok and node_id == target:
            add(here, "self_connection", id=target)
            ok = False
        if ok and (source, target) in seen:
            add(here, "duplicate_connection", source=source, target=target)
        if ok:
            seen.add((source, target))
            upstream[target].add(node_id)
            connected.add((node_id, port, target))
    return upstream, connected


def _references(nodes: dict, inputs: dict, connected: set, add) -> None:
    for node_id, node in nodes.items():
        node_type = REGISTRY.get(node.get("type"))
        config = node.get("config", {})  # a node without config: its type's rules still apply
        if node_type is None or not isinstance(config, dict):
            continue
        for key, spec in node_type.config.items():
            if spec.kind != "template" or not isinstance(config.get(key), str):
                continue
            where = f"nodes.{node_id}.config.{key}"
            for ref in placeholders.references(config[key]):
                parsed = placeholders.parse(ref)
                if parsed is None:
                    add(where, "bad_reference", ref=ref)
                elif parsed[0] == "item":
                    if not spec.item:
                        add(where, "item_only_in_loop", ref=ref)
                elif parsed[0] == "inputs":
                    if parsed[1] not in inputs:
                        add(where, "unknown_input", ref=ref)
                else:
                    _, source, port = parsed
                    if source not in nodes:
                        add(where, "unknown_node_ref", ref=ref)
                    elif REGISTRY.get(nodes[source].get("type")) and \
                            port not in REGISTRY[nodes[source]["type"]].outputs(nodes[source].get("config") or {}):
                        add(where, "unknown_port_ref", ref=ref)
                    elif (source, port, node_id) not in connected and (source, "", node_id) not in connected:
                        add(where, "reference_not_connected", ref=ref, source=f"{source}.{port}", target=node_id)
        _type_rules(node_id, node_type.name, config, inputs, nodes, add)


def _type_rules(node_id: str, kind: str, config: dict, inputs: dict, nodes: dict, add) -> None:
    here = f"nodes.{node_id}.config"
    if kind == "document.extract" and not config.get("file") and \
            sum(spec.get("type") in ("file", "url") for spec in inputs.values()) != 1:
        add(f"{here}.file", "extract_needs_file")
    if kind == "document.extract" and isinstance(config.get("file"), str) and config["file"]:
        ref = placeholders.only_reference(config["file"])
        parsed = placeholders.parse(ref) if ref else None
        is_file = parsed and ((parsed[0] == "inputs" and inputs.get(parsed[1], {}).get("type") in ("file", "url")) or
                              (parsed[0] == "nodes" and parsed[1] in nodes and REGISTRY.get(nodes[parsed[1]].get("type"))
                               and REGISTRY[nodes[parsed[1]]["type"]].outputs(nodes[parsed[1]].get("config") or {}).get(parsed[2]) == "file"))
        if not is_file:
            add(f"{here}.file", "file_must_be_reference")
    if kind == "document.extract" and isinstance(config.get("ocr_languages"), str) \
            and not placeholders.references(config["ocr_languages"]) and config["ocr_languages"].strip():
        from .ocr import LANG_RE
        if not LANG_RE.match(config["ocr_languages"].strip()):
            add(f"{here}.ocr_languages", "ocr_bad_languages", value=config["ocr_languages"])
    if kind == "condition":
        operator = config.get("operator") or "contains"
        match = config.get("match")
        if operator == "ai":  # a model answers a yes-or-no question
            for key in ("question", "provider"):
                if not (isinstance(config.get(key), str) and config[key].strip()):
                    add(f"{here}.{key}", "missing")
        elif operator in OPERATORS and operator not in ("is_yes", "empty") and not (isinstance(match, str) and match):
            add(f"{here}.match", "condition_needs_match")
        elif operator == "regex" and isinstance(match, str) and not placeholders.references(match):
            try:
                re.compile(match)
            except re.error as e:
                add(f"{here}.match", "bad_regex", error=e)
    if kind == "ai.cli" and isinstance(config.get("json_schema"), str) and config["json_schema"].strip():
        import json
        try:
            if not isinstance(json.loads(config["json_schema"]), dict):
                raise ValueError("not an object")
        except ValueError as e:
            add(f"{here}.json_schema", "bad_json_schema", error=e)
    if "provider" in REGISTRY[kind].config and isinstance(config.get("provider"), str):
        provider = config["provider"].strip()
        ref = placeholders.only_reference(provider)
        if ref is not None:
            parsed = placeholders.parse(ref)
            if not parsed or parsed[0] != "inputs" or inputs.get(parsed[1], {}).get("type") != "provider":
                add(f"{here}.provider", "provider_reference")
        elif not PROVIDER_RE.match(provider):
            add(f"{here}.provider", "bad_provider", value=provider)


def _fallbacks(nodes: dict, inputs: dict, add) -> None:
    """fallback_provider: another model for a step whose model reports a usage limit; a name or a provider input."""
    for node_id, node in nodes.items():
        if "fallback_provider" not in node or REGISTRY.get(node.get("type")) is None:
            continue
        where, value = f"nodes.{node_id}.fallback_provider", node["fallback_provider"]
        ref = placeholders.only_reference(value) if isinstance(value, str) else None
        parsed = placeholders.parse(ref) if ref else None
        if "provider" not in REGISTRY[node["type"]].config:
            add(where, "fallback_needs_model")
        elif not isinstance(value, str):
            add(where, "bad_provider", value=value)
        elif ref is not None:
            if not parsed or parsed[0] != "inputs" or inputs.get(parsed[1], {}).get("type") != "provider":
                add(where, "provider_reference")
        elif not PROVIDER_RE.match(value.strip()):
            add(where, "bad_provider", value=value)


def _order(nodes: dict, upstream: dict, add) -> list[str]:
    """Kahn's algorithm in file order; the nodes left over form a cycle."""
    remaining = {n: set(ups) for n, ups in upstream.items()}
    order = []
    while True:
        ready = [n for n in nodes if n in remaining and not remaining[n]]
        if not ready:
            break
        for n in ready:
            order.append(n)
            del remaining[n]
        for ups in remaining.values():
            ups.difference_update(ready)
    if remaining:
        add("connections", "cycle", nodes=", ".join(sorted(remaining)))
    return order


def _outputs(value, nodes: dict, add) -> dict[str, str]:
    outputs = _entries(value, "outputs", add, OUTPUT_KEYS)
    out = {}
    for output_id, item in outputs.items():
        here = f"outputs.{output_id}"
        _localized(item.get("label"), f"{here}.label", add)
        source = item.get("from")
        node_id, _, port = source.partition(".") if isinstance(source, str) else ("", "", "")
        if node_id not in nodes or not port:
            add(f"{here}.from", "bad_output_source")
        elif REGISTRY.get(nodes[node_id].get("type")) and \
                port not in REGISTRY[nodes[node_id]["type"]].outputs(nodes[node_id].get("config") or {}):
            add(f"{here}.from", "unknown_port", node=node_id, port=port)
        else:
            out[output_id] = source
    return out


def _layout(value, nodes: dict, add) -> None:
    """The editor's drawing positions: {node id: {x, y}} with whole numbers, only for nodes of this workflow."""
    if value is None:
        return
    if not isinstance(value, dict):
        add("layout", "not_a_mapping")
        return
    for node_id, position in value.items():
        here = f"layout.{node_id}"
        if node_id not in nodes:
            add(here, "unknown_node", id=node_id)
        elif not (isinstance(position, dict) and set(position) == {"x", "y"} and
                  all(isinstance(v, int) and not isinstance(v, bool) and abs(v) <= POSITION_LIMIT for v in position.values())):
            add(here, "bad_position", limit=POSITION_LIMIT)


# --- warnings: a valid workflow that probably does not do what its author wants ----------------------
# Shown by the editor and before a run; they never block saving or running. (What fails while a run works is the
# engine's part.)

def warnings(wf: Workflow) -> list[Problem]:
    """The warnings of a checked workflow, each with its place:
    - a step that needs a text but has no incoming connection and names no input of the run form,
    - a step whose result nobody uses: no connection leaves it and it is not a result of the workflow,
    - a workflow that saves nothing: no export step and no result."""
    out: list[Problem] = []
    sources = {source for c in wf.data.get("connections") or [] for source in [str(c["from"]).partition(".")[0]]}
    results = {source.partition(".")[0] for source in wf.outputs.values()}
    for node_id, node in wf.nodes.items():
        node_type = REGISTRY[node["type"]]
        config = node.get("config") or {}
        if node["type"] != "document.extract" and not wf.upstream[node_id]:
            named = [parsed for key, spec in node_type.config.items()
                     if spec.kind == "template" and spec.widget != "provider" and isinstance(config.get(key), str)
                     for ref in placeholders.references(config[key]) for parsed in [placeholders.parse(ref)]
                     if parsed and parsed[0] == "inputs"]
            if not named:
                out.append(Problem(f"nodes.{node_id}", "warn_step_no_input"))
        if node["type"] != "document.export" and node_id not in sources and node_id not in results:
            out.append(Problem(f"nodes.{node_id}", "warn_output_unused"))
    if not wf.outputs and not any(node["type"] == "document.export" for node in wf.nodes.values()):
        out.append(Problem("outputs", "warn_no_result"))
    return out


# --- the editor: ordered writing and renaming -------------------------------------

def _ordered(item, order) -> dict:
    """The mapping with the keys of order first (in that order), then any other key as it came."""
    if not isinstance(item, dict):
        return item
    return {**{k: item[k] for k in order if k in item}, **{k: v for k, v in item.items() if k not in order}}


def canonical(data) -> dict:
    """The workflow with its keys in the documented order. Unknown keys and wrong types are kept as they are, so
    that converting a workflow with problems loses nothing; the check reports them."""
    if not isinstance(data, dict):
        return data
    out = _ordered(data, TOP_ORDER)
    if isinstance(out.get("inputs"), list):
        out["inputs"] = [_ordered(i, INPUT_ORDER) if not isinstance(i, dict) or not isinstance(i.get("options"), list)
                         else {**_ordered(i, INPUT_ORDER), "options": [_ordered(o, ("value", "label")) for o in i["options"]]}
                         for i in out["inputs"]]
    if isinstance(out.get("nodes"), list):
        nodes = []
        for node in out["nodes"]:
            node = _ordered(node, NODE_ORDER)
            node_type = REGISTRY.get(node.get("type")) if isinstance(node, dict) and isinstance(node.get("type"), str) else None
            if node_type and isinstance(node.get("config"), dict):
                node["config"] = _ordered(node["config"], tuple(node_type.config))
            nodes.append(node)
        out["nodes"] = nodes
    for key, order in (("connections", ("from", "to")), ("outputs", ("id", "from", "label"))):
        if isinstance(out.get(key), list):
            out[key] = [_ordered(item, order) for item in out[key]]
    if isinstance(out.get("layout"), dict):
        out["layout"] = {k: _ordered(v, ("x", "y")) for k, v in out["layout"].items()}
    return out


def dump(data) -> str:
    """The workflow as readable YAML: keys in the documented order, multi-line texts as "|" blocks."""
    return yamlio.dump_readable(canonical(data), spaced=("inputs", "nodes", "connections", "outputs", "layout"),
                                spaced_items="nodes")


def rename(data: dict, kind: str, old: str, new: str) -> dict:
    """A copy of the workflow where the node (kind "nodes") or input (kind "inputs") old is called new: its entry,
    the connections, the outputs, the layout and every {{nodes.old.x}} / {{inputs.old}} placeholder."""
    if kind not in ("nodes", "inputs") or not isinstance(data, dict) or not isinstance(data.get(kind), list):
        raise WorkflowError([Problem("", "bad_rename")])
    if not isinstance(new, str) or not ID_RE.fullmatch(new):
        raise WorkflowError([Problem(f"{kind}.{old}.id", "bad_id", {"value": new})])
    ids = [item.get("id") for item in data[kind] if isinstance(item, dict)]
    if old not in ids:
        raise WorkflowError([Problem(f"{kind}.{old}", "unknown_node" if kind == "nodes" else "unknown_run_input", {"id": old})])
    if new != old and new in ids:
        raise WorkflowError([Problem(f"{kind}.{old}.id", "duplicate_id", {"id": new})])
    data = copy.deepcopy(data)
    for item in data[kind]:
        if isinstance(item, dict) and item.get("id") == old:
            item["id"] = new

    def fix(match):
        parsed = placeholders.parse(match.group(1).strip())
        if not parsed or parsed[0] != kind or parsed[1] != old:
            return match.group(0)
        return match.group(0).replace(f"{kind}.{old}", f"{kind}.{new}", 1)

    for node in data.get("nodes") or []:
        node_type = REGISTRY.get(node.get("type")) if isinstance(node, dict) and isinstance(node.get("type"), str) else None
        config = node.get("config") if node_type else None
        if isinstance(config, dict):
            for key, spec in node_type.config.items():
                if spec.kind == "template" and isinstance(config.get(key), str):
                    config[key] = placeholders.TOKEN.sub(fix, config[key])
    if kind == "nodes":
        def moved(ref):
            node_id, dot, port = ref.partition(".") if isinstance(ref, str) else ("", "", "")
            return f"{new}{dot}{port}" if node_id == old else ref
        for item in data.get("connections") or []:
            if isinstance(item, dict) and "from" in item:
                item["from"] = moved(item["from"])
            if isinstance(item, dict) and item.get("to") == old:
                item["to"] = new
        for item in data.get("outputs") or []:
            if isinstance(item, dict) and "from" in item:
                item["from"] = moved(item["from"])
        if isinstance(data.get("layout"), dict) and old in data["layout"]:
            data["layout"] = {new if k == old else k: v for k, v in data["layout"].items()}
    return data
