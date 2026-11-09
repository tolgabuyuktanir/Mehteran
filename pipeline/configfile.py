"""Edits config.toml in place, keeping its comments and layout (Python has no TOML writer in the standard library)."""

from __future__ import annotations

import re

from . import stages

STAGE_COMMENTS = {
    "align": "preparation: finds each Turkish segment in the reference translations",
    "glossary": "preparation: extracts the terminology glossary",
    "translate": "1  first translation",
    "review1": "2  review: compares the translation with the Turkish source, reports issues",
    "revise1": "3  applies the review findings",
    "source_check": "4  checks the text against the Turkish source from the start, and corrects it",
    "review2": "5a, 5b  second independent review (in parallel)",
    "reconcile": "6  reconciles the two reviews, produces the final text",
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


def set_stages(text: str, assignment: dict[str, list[str]]) -> str:
    """Replaces the body of [stages]. assignment: {stage: [names]}; names are validated by the caller."""
    start, end = _section_span(text, "stages")
    width = max(len(s) for s in stages.LLM_STAGES)
    lines = []
    for stage in stages.LLM_STAGES:
        names = assignment[stage]
        value = f'"{names[0]}"' if stage not in stages.REVIEW_STAGES and len(names) == 1 else _toml_list(names)
        lines.append(f"{stage.ljust(width)} = {value.ljust(24)} # {STAGE_COMMENTS[stage]}")
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
