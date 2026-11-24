"""Messages in the interface languages: the command line, the web interface and the workflow checks.

The texts are in mehteran/locales/<code>.json, one file per language: {"ui": {key: text}, "messages": {key: text}}.
Turkish (tr) and English (en) are complete; another language may have only some of the keys, and a missing text is
shown in English. The interface languages are those of the language registry (mehteran/languages.json, "ui": true).
A text added here with MESSAGES.update({...}) or UI.update({key: {"tr": ..., "en": ...}}) still works: it is merged
into the loaded texts; "python3 -m mehteran.i18n_tools absorb" moves such blocks into the locale files.

The language is chosen per web request or engine thread (set_request) or once per process (set_default: the
command line, or MEHTERAN_LANG). Code and identifiers stay in English. Prompts given to the models are not
translated; a workflow passes the output language to them as an input.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from . import languages

LANGUAGES = languages.UI_CODES
FALLBACK = "en"
LOCALES = Path(__file__).resolve().parent / "locales"
_default = os.environ.get("MEHTERAN_LANG") if os.environ.get("MEHTERAN_LANG") in LANGUAGES else "tr"
_local = threading.local()


def set_default(lang: str | None) -> None:
    global _default
    if lang in LANGUAGES:
        _default = lang


def set_request(lang: str | None) -> None:
    _local.lang = lang if lang in LANGUAGES else None


def current() -> str:
    return getattr(_local, "lang", None) or _default


class Catalog(dict):
    """{key: {language: text}}. Setting a key that exists adds its languages to the entry, so a block of
    {"tr": ..., "en": ...} texts in this file does not drop the other languages loaded from the locale files.
    The entry that was there is not changed (a new one takes its place)."""

    def __setitem__(self, key, value):
        if key in self and isinstance(value, dict) and self[key] is not value:
            value = {**self[key], **value}
        super().__setitem__(key, value)

    def update(self, other=(), **more):
        for key, value in {**dict(other), **more}.items():
            self[key] = value


MESSAGES = Catalog()
UI = Catalog()


def text_of(entry: dict, lang: str | None = None) -> str:
    """The text of an entry in a language; English when that language has none."""
    return entry.get(lang or current()) or entry.get(FALLBACK) or next(iter(entry.values()), "")


def load_locales(folder: Path = LOCALES) -> None:
    """Reads <folder>/<code>.json into MESSAGES and UI. English first: its key order is the order of the catalogs."""
    codes = sorted((p.stem for p in folder.glob("*.json") if p.stem in LANGUAGES), key=lambda c: (c != FALLBACK, c != "tr", c))
    for code in codes:
        try:
            data = json.loads((folder / f"{code}.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue  # a broken file of one language: that language falls back to English (i18n_tools validate names it)
        for section, catalog in (("messages", MESSAGES), ("ui", UI)):
            texts = data.get(section) if isinstance(data, dict) else None
            for key, text in (texts.items() if isinstance(texts, dict) else ()):
                if isinstance(text, str) and text:
                    catalog.setdefault(key, {})[code] = text


def ui_strings(lang: str | None = None) -> dict:
    """The interface texts for the page: {key: {<lang>: text, "en": text}} (the page falls back to "en")."""
    lang = lang or current()
    return {key: {code: entry[code] for code in {lang, FALLBACK} if entry.get(code)} for key, entry in UI.items()}


class Msg(str):
    """A message rendered in the current language that remembers its key and values, so that a stored message (an
    event, a node error) can be shown again in another language (render)."""
    key: str = ""
    params: dict = {}


def _param(value):
    """A message value as JSON: a nested message (or an exception carrying one) keeps its key and values."""
    if isinstance(value, BaseException) and value.args and isinstance(value.args[0], Msg):
        value = value.args[0]
    if isinstance(value, Msg) and value.key:
        return {"$key": value.key, "params": value.params}
    if isinstance(value, dict) and "$key" in value:  # already stored that way
        return value
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if _pairs(value):  # [[label, message], ...]: shown as "label: message; ..."
        return [[str(a), _param(b)] for a, b in value]
    return str(value)


def _pairs(value) -> bool:
    return isinstance(value, list) and bool(value) and all(isinstance(v, (list, tuple)) and len(v) == 2 for v in value)


def t(key: str, **values) -> str:
    entry = MESSAGES.get(key)
    if entry is None:
        return key
    shown = {k: "; ".join(f"{a}: {_shown(b)}" for a, b in v) if _pairs(v) else _shown(v) for k, v in values.items()}
    out = Msg(text_of(entry).format(**shown))  # always formatted: literal braces are written doubled
    out.key, out.params = key, {k: _param(v) for k, v in values.items()}
    return out


def _shown(value):
    return render(value["$key"], value.get("params"), "") if isinstance(value, dict) and "$key" in value else value


def message_of(error: BaseException | str) -> str:
    """The message of an exception, keeping its key when it is one of ours (str(error) would lose it)."""
    if isinstance(error, BaseException):
        return error.args[0] if error.args and isinstance(error.args[0], Msg) else str(error)
    return error


def render(key: str | None, params: dict | None, fallback: str = "") -> str:
    """A stored message (key and values) in the current language; the stored text when it has no key."""
    if not key or key not in MESSAGES:
        return fallback

    try:
        return str(t(key, **(params or {})))
    except (KeyError, IndexError, ValueError):
        return fallback


def localized(value, lang: str | None = None) -> str:
    """A workflow text: a plain string, or a {tr, en} map (English for another language; else the one there is)."""
    if isinstance(value, dict):
        return str(text_of(value, lang))
    return "" if value is None else str(value)


load_locales()

# Messages that the page shows too (one text, in both catalogs).
SHARED = ("quota_waiting",)
UI.update({key: value for key, value in MESSAGES.items() if key.startswith("status_") or key in SHARED})

# Texts may still be added below as MESSAGES.update({...}) / UI.update({key: {"tr": ..., "en": ...}}); they are merged
# into the texts loaded above. "python3 -m mehteran.i18n_tools absorb" moves them into mehteran/locales/.
