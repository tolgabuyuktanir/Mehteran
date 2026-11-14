"""Tools for the people (and agents) who translate the interface.

    python3 -m mehteran.i18n_tools coverage            how many texts each language has
    python3 -m mehteran.i18n_tools missing <lang>      the keys <lang> has no text for, with the English text
    python3 -m mehteran.i18n_tools missing <lang> --json   the same as JSON, ready to translate and merge
    python3 -m mehteran.i18n_tools merge <lang> <file.json>   adds the texts of such a JSON file to the locale files
    python3 -m mehteran.i18n_tools validate [lang]     checks the locale files; exit code 1 when there is a problem
    python3 -m mehteran.i18n_tools absorb              moves the texts written in mehteran/i18n.py into the locale files

Three groups of texts, each with English as the reference:
    ui           mehteran/locales/<lang>.json, "ui"        the web interface (S("key") in mehteran/ui/*.js)
    messages     mehteran/locales/<lang>.json, "messages"  the server and command-line messages (i18n.t("key"))
    translation  pipeline/ui/locales/<lang>.json           the book translation's interface; its Turkish and English
                                                           are in pipeline/ui/app.js (I18N), where its own page needs them
Rules: Turkish and English have every key. Another language may have only some; a missing text is shown in English.
A text keeps the {name} placeholders of the English text, and (in "translation") its HTML tags.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

from . import i18n, languages

GROUPS = ("ui", "messages", "translation")
COMPLETE = ("tr", "en")
TRANSLATION_UI = Path(__file__).resolve().parent.parent / "pipeline" / "ui"
PLACEHOLDER = re.compile(r"(?<!\{)\{([A-Za-z_][A-Za-z_0-9]*)\}(?!\})")
TAG = re.compile(r"</?[a-z][a-z0-9]*\b[^>]*>")
_PAIR = re.compile(r'\b([a-z_][a-z_0-9]*):\s*("(?:[^"\\]|\\.)*")')


def placeholders(text: str) -> set[str]:
    return set(PLACEHOLDER.findall(text))


def translation_builtin() -> dict[str, dict[str, str]]:
    """The Turkish and English texts of the book translation's interface, read from I18N in pipeline/ui/app.js."""
    js = (TRANSLATION_UI / "app.js").read_text(encoding="utf-8")
    block = js[js.index("const I18N = {"):js.index("\n};", js.index("const I18N = {"))]
    out = {}
    for lang, body in re.findall(r"\n  (tr|en): \{\n(.*?)\n  \},", block + "\n  },", re.S):
        out[lang] = {key: json.loads(text) for key, text in _PAIR.findall(body)}
    return out


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def texts(lang: str) -> dict[str, dict[str, str]]:
    """{group: {key: text}} of one language, as stored (no fallback)."""
    own_ui = {key: entry for key, entry in i18n.UI.items() if entry is not i18n.MESSAGES.get(key)}
    out = {"ui": {k: e[lang] for k, e in own_ui.items() if e.get(lang)},
           "messages": {k: e[lang] for k, e in i18n.MESSAGES.items() if e.get(lang)}}
    out["translation"] = translation_builtin()[lang] if lang in COMPLETE else _read(TRANSLATION_UI / "locales" / f"{lang}.json")
    return out


def missing(lang: str) -> dict[str, dict[str, str]]:
    """{group: {key: English text}} for the keys that lang has no text for."""
    reference, own = texts("en"), texts(lang)
    return {group: {key: text for key, text in reference[group].items() if not own[group].get(key)} for group in GROUPS}


def problems(lang: str) -> list[str]:
    out = []
    if lang not in languages.UI_CODES:
        return [f"{lang}: not an interface language (mehteran/languages.json, \"ui\": true)"]
    for path, sections in ((i18n.LOCALES / f"{lang}.json", ("ui", "messages")), (TRANSLATION_UI / "locales" / f"{lang}.json", None)):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError as e:
            out.append(f"{path.name}: not valid JSON ({e})")
            continue
        maps = [data.get(s, {}) for s in sections] if sections else [data]
        if not isinstance(data, dict) or (sections and set(data) - set(sections)) or \
                not all(isinstance(m, dict) and all(isinstance(v, str) for v in m.values()) for m in maps):
            out.append(f"{path}: must be " + ('{"ui": {key: text}, "messages": {key: text}}' if sections else "{key: text}"))
    if out:
        return out
    reference, own = texts("en"), texts(lang)
    for group in GROUPS:
        for key, text in own[group].items():
            if key not in reference[group]:
                out.append(f"{lang} {group}.{key}: no such key in English")
                continue
            if not text.strip():
                out.append(f"{lang} {group}.{key}: empty")
            if placeholders(text) != placeholders(reference[group][key]):
                out.append(f"{lang} {group}.{key}: placeholders {sorted(placeholders(text))}, English has "
                           f"{sorted(placeholders(reference[group][key]))}")
            if group == "translation" and sorted(TAG.findall(text)) != sorted(TAG.findall(reference[group][key])):
                out.append(f"{lang} {group}.{key}: the HTML tags differ from the English text")
        if lang in COMPLETE:
            out += [f"{lang} {group}.{key}: missing" for key in reference[group] if not own[group].get(key)]
    if lang == "en":
        tr = texts("tr")
        out += [f"en {group}.{key}: missing" for group in GROUPS for key in tr[group] if key not in own[group]]
    return out


def coverage() -> list[tuple[str, dict[str, tuple[int, int]]]]:
    reference = texts("en")
    return [(lang, {group: (sum(1 for k in reference[group] if texts_of.get(group, {}).get(k)), len(reference[group]))
                    for group in GROUPS})
            for lang in languages.UI_CODES for texts_of in [texts(lang)]]


def write_locale(lang: str, ui: dict[str, str], messages: dict[str, str]) -> None:
    i18n.LOCALES.mkdir(exist_ok=True)
    order = {"ui": [k for k, e in i18n.UI.items() if e is not i18n.MESSAGES.get(k)], "messages": list(i18n.MESSAGES)}
    data = {name: {k: part[k] for k in [*order[name], *sorted(set(part) - set(order[name]))] if part.get(k)}
            for name, part in (("ui", ui), ("messages", messages))}
    (i18n.LOCALES / f"{lang}.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def merge(lang: str, new: dict) -> int:
    """Adds {group: {key: text}} (the form "missing --json" prints) to the files of lang. Returns the number of texts."""
    reference, own = texts("en"), texts(lang)
    count = 0
    for group in GROUPS:
        for key, text in (new.get(group) or {}).items():
            if key in reference[group] and isinstance(text, str) and text.strip():
                own[group][key] = text
                count += 1
    write_locale(lang, own["ui"], own["messages"])
    if lang not in COMPLETE and own["translation"]:
        folder = TRANSLATION_UI / "locales"
        folder.mkdir(exist_ok=True)
        ordered = {k: own["translation"][k] for k in reference["translation"] if own["translation"].get(k)}
        (folder / f"{lang}.json").write_text(json.dumps(ordered, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return count


def absorb() -> int:
    """Writes every text that mehteran/i18n.py holds into the locale files, then removes those blocks from i18n.py
    (MESSAGES.update({...}) and UI.update({...}) with a literal map, and the comment lines right above them)."""
    for lang in languages.UI_CODES:
        own = texts(lang)
        if own["ui"] or own["messages"]:
            write_locale(lang, own["ui"], own["messages"])
    path = Path(i18n.__file__)
    source = path.read_text(encoding="utf-8")
    lines = source.split("\n")
    removed = 0
    for node in reversed(ast.parse(source).body):
        call = node.value if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call) else None
        if not (call and isinstance(call.func, ast.Attribute) and call.func.attr == "update" and isinstance(call.func.value, ast.Name)
                and call.func.value.id in ("MESSAGES", "UI") and len(call.args) == 1 and isinstance(call.args[0], ast.Dict)):
            continue
        start = node.lineno - 1
        while start > 0 and lines[start - 1].lstrip().startswith("#"):
            start -= 1
        while start > 0 and not lines[start - 1].strip() and node.end_lineno < len(lines) and not lines[node.end_lineno].strip():
            start -= 1
        del lines[start:node.end_lineno]
        removed += 1
    if removed:
        path.write_text("\n".join(lines), encoding="utf-8")
    return removed


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in args
    args = [a for a in args if a != "--json"]
    command = args[0] if args else ""
    if command == "coverage":
        for lang, groups in coverage():
            done, total = sum(d for d, _ in groups.values()), sum(n for _, n in groups.values())
            print(f"{lang:3} {100 * done // total:3d}%  " + "  ".join(f"{g} {d}/{n}" for g, (d, n) in groups.items()))
        return 0
    if command == "missing" and len(args) == 2:
        if args[1] not in languages.UI_CODES:
            print(problems(args[1])[0], file=sys.stderr)
            return 1
        found = missing(args[1])
        if as_json:
            print(json.dumps(found, ensure_ascii=False, indent=1))
        else:
            for group in GROUPS:
                for key, text in found[group].items():
                    print(f"{group}.{key}\t{text}")
            print(f"{args[1]}: {sum(map(len, found.values()))} missing", file=sys.stderr)
        return 0
    if command == "merge" and len(args) == 3:
        if args[1] not in languages.UI_CODES:
            print(problems(args[1])[0], file=sys.stderr)
            return 1
        print(f"{args[1]}: {merge(args[1], json.loads(Path(args[2]).read_text(encoding='utf-8')))} texts merged")
        return 0
    if command == "validate" and len(args) <= 2:
        found = [p for lang in ([args[1]] if len(args) == 2 else languages.UI_CODES) for p in problems(lang)]
        print("\n".join(found) if found else "ok")
        return 1 if found else 0
    if command == "absorb" and len(args) == 1:
        print(f"{absorb()} blocks moved from mehteran/i18n.py into {i18n.LOCALES}")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
