"""{{inputs.x}} and {{nodes.<id>.<output>}} placeholders; {{item.<field>}} inside the prompt of a loop (ai.map).

Substitution is a single pass: text that a placeholder inserts (a document, a model's answer) is never scanned
again, so a document that contains "{{inputs.x}}" cannot pull other values into a prompt.
"""

from __future__ import annotations

import re
from typing import Callable

TOKEN = re.compile(r"\{\{(.*?)\}\}", re.S)
REF = re.compile(r"^(?:inputs\.([a-z][a-z0-9_-]{0,63})|nodes\.([a-z][a-z0-9_-]{0,63})\.([a-z][a-z0-9_-]{0,63})|"
                 r"item\.(text|title|index|count))$")
ITEM_FIELDS = ("text", "title", "index", "count")  # one part of a loop: its text, its title, its number, how many


def references(template: str) -> list[str]:
    """Every placeholder of the template, as written between the braces (stripped)."""
    return [m.group(1).strip() for m in TOKEN.finditer(template)]


def parse(ref: str) -> tuple[str, str, str] | None:
    """("inputs", id, ""), ("nodes", id, output) or ("item", field, ""); None for anything else."""
    m = REF.match(ref)
    if not m:
        return None
    if m.group(4):
        return ("item", m.group(4), "")
    return ("inputs", m.group(1), "") if m.group(1) else ("nodes", m.group(2), m.group(3))


def render(template: str, value: Callable[[str], str]) -> str:
    """Replaces each placeholder with value(ref) in one pass. value raises KeyError for an unknown reference."""
    return TOKEN.sub(lambda m: value(m.group(1).strip()), template)


def only_reference(template: str) -> str | None:
    """The reference when the whole template is exactly one placeholder ("{{inputs.paper}}"), else None."""
    m = TOKEN.fullmatch(template.strip())
    return m.group(1).strip() if m else None
