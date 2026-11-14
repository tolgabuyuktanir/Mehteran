"""The language registry: one list for the interface languages, the flag picker and the output language of a workflow.

The data is mehteran/languages.json: one entry per language with its code, its own name ("native"), its English
name, the country code of its flag (mehteran/ui/flags/<flag>.svg) and its direction ("ltr" or "rtl"). An entry with
"ui": true is an interface language: it has a file mehteran/locales/<code>.json. Every language of the translation
app's default list (config.default.toml, [languages]) is here too.
"""

from __future__ import annotations

import json
from pathlib import Path

LANGUAGES: list[dict] = json.loads((Path(__file__).resolve().parent / "languages.json").read_text(encoding="utf-8"))
BY_CODE = {item["code"]: item for item in LANGUAGES}
CODES = tuple(BY_CODE)
UI_CODES = tuple(item["code"] for item in LANGUAGES if item.get("ui"))


def english_name(code: str) -> str:
    """The English name of a language code, for an instruction to a model; the code itself when it is not known."""
    return BY_CODE[code]["english"] if code in BY_CODE else code
