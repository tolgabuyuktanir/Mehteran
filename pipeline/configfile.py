"""Edits config.toml in place, keeping its comments and layout (Python has no TOML writer in the standard library)."""

from __future__ import annotations

import json
import re

from . import stages

STAGE_COMMENTS = {
    "align": "preparation: finds each Turkish segment in the reference translations",
    "glossary": "preparation: extracts the terminology glossary",
    "translate": "first translation",
    "review": "reviewers report findings (in parallel); the text is unchanged",
    "apply": "applies the findings reported since the last text",
    "source_check": "checks the text against the Turkish source from the start, and corrects it",
    "custom": "custom step (see [nodes] and prompts/custom/)",
    "gate": "checkpoint: sends a segment with serious problems back (see [nodes])",
}
NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}(/[A-Za-z0-9][A-Za-z0-9._:-]{0,79})?$")  # never starts with "-"
MODEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,79}$")


def _toml_list(values: list[str]) -> str:
    return "[" + ", ".join(f'"{v}"' for v in values) + "]"


def _section_span(text: str, section: str) -> tuple[int, int]:
    """Start and end offsets of a section's body (after its header line, up to the next header)."""
    m = re.search(rf"^\[{re.escape(section)}\][ \t]*\n", text, re.M)
    if not m:
        raise ValueError(f"[{section}] not found")
    nxt = re.compile(r"^\[", re.M).search(text, m.end())
    return m.end(), nxt.start() if nxt else len(text)


def set_stages(text: str, assignment: dict[str, list[str]], flow: list[str], nodes: dict | None = None) -> str:
    """Replaces the body of [stages] and of [nodes]. flow: the nodes after the first translation, in order.
    assignment: {stage: [names]} for every stage; nodes: the options of custom nodes and checkpoints.
    All are validated by the caller."""
    nodes = nodes or {}
    start, end = _section_span(text, "stages")
    order = stages.PREP_STAGES + ["translate"] + flow
    width = max(len(s) for s in order + ["flow"])
    lines = [
        "# The nodes after the first translation, in order: review<n> (findings), revise<n>/reconcile/apply<n> (applies",
        "# them), source_check[<n>], custom<n> and gate<n> (checkpoint). Each node works on the latest text.",
        f"{'flow'.ljust(width)} = {_toml_list(flow)}",
    ]
    cfg = {"nodes": nodes}
    for stage in order:
        names = assignment[stage]
        many = stages.role(cfg, stage) == "report" and stage not in ("align", "glossary", "translate")
        value = _toml_list(names) if many or len(names) > 1 else f'"{names[0]}"'
        lines.append(f"{stage.ljust(width)} = {value.ljust(24)} # {STAGE_COMMENTS[stages.kind(stage)]}")
    text = text[:start] + "\n".join(lines) + "\n\n" + text[end:].lstrip("\n")
    return set_nodes(text, {node: nodes[node] for node in flow if node in nodes})


def _toml_value(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(str(value), ensure_ascii=False)  # a JSON string is also a TOML basic string


def set_nodes(text: str, nodes: dict[str, dict]) -> str:
    """Replaces the body of [nodes] (added after [stages] when missing): one inline table per node."""
    if not re.search(r"^\[nodes\][ \t]*$", text, re.M):
        _, end = _section_span(text, "stages")
        text = text[:end] + "[nodes]\n\n" + text[end:]
    start, end = _section_span(text, "nodes")
    lines = ["# Options of custom steps (title, mode: report or rewrite) and checkpoints (back_to, max)."]
    for node, options in nodes.items():
        body = ", ".join(f"{key} = {_toml_value(value)}" for key, value in options.items())
        lines.append(f"{node} = {{ {body} }}")
    return text[:start] + "\n".join(lines) + "\n\n" + text[end:].lstrip("\n")


def set_key(text: str, section: str, key: str, value: str) -> str:
    """Sets key = value (value is TOML text) in a section; adds the line when the key is missing."""
    start, end = _section_span(text, section)
    body = text[start:end]
    # The value can be an array written over several lines: replace all of it.
    line = re.compile(rf"^{re.escape(key)}[ \t]*=[ \t]*(\[[^\]]*\]|.*)$", re.M)
    if line.search(body):
        body = line.sub(lambda _: f"{key} = {value}", body, count=1)
    else:
        body = f"{key} = {value}\n" + body
    return text[:start] + body + text[end:]


def set_models(text: str, provider: str, models: list[str]) -> str:
    return set_key(text, f"providers.{provider}", "models", _toml_list(models))
