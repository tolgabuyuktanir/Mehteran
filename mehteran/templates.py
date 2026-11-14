"""The template library: built-in templates (read-only, mehteran/templates/) and the user's own (<data>/templates/).

Two namespaces, written "builtin:<id>" and "user:<id>". A bare id works when only one namespace has it.
"Customize" copies a template into the user namespace under a new id; that copy is the user's own file, and a
later update of the built-in never touches it. A user template cannot take the id of a built-in one.

A draft is a user template saved with problems (save_draft): it is listed with its problems and cannot run until
it passes the check; it never contains credentials.
"""

from __future__ import annotations

import copy
import os
import re
from pathlib import Path

from . import paths, schema, yamlio
from .i18n import t
from .nodes import ID_RE

BUILTIN, USER = "builtin", "user"
SOURCES = (BUILTIN, USER)


class TemplateError(ValueError):
    def __init__(self, messages: list[str], code: int = 400):
        self.messages, self.code = messages, code
        super().__init__("\n".join(messages))


# Built-in templates that were merged into another one. A run, a favorite or a bookmark that names the old id works
# with the new template.
ALIASES = {
    "multi-document-comparison": "document-comparison",
    "chapter-summaries": "document-summary",
    "multi-length-summary": "document-summary",
    "terms-plain-language": "plain-language-rewrite",
    "proofreading-change-list": "writing-polish",
    "abstract-title-improvement": "writing-polish",
    "sat-math-practice-set": "exam-practice-set",
    "sat-reading-writing-practice": "exam-practice-set",
    "lgs-yks-practice": "exam-practice-set",
    "ap-mcq-from-notes": "ap-question-generator",
    "ap-frq-generator": "ap-question-generator",
}


def canonical_ref(ref: str) -> str:
    """"builtin:old-id" or "old-id" -> the ref of the template that replaced it; any other ref stays as it is."""
    source, _, template_id = ref.rpartition(":")
    if source in ("", BUILTIN) and template_id in ALIASES:
        return f"{BUILTIN}:{ALIASES[template_id]}"
    return ref


def folder(source: str, home: Path) -> Path:
    return paths.BUILTIN_TEMPLATES if source == BUILTIN else home / "templates"


def _path(source: str, template_id: str, home: Path) -> Path:
    if source not in SOURCES or not ID_RE.match(template_id or ""):
        raise TemplateError([t("template_not_found", id=template_id)], 404)
    if source == BUILTIN:
        template_id = ALIASES.get(template_id, template_id)
    return folder(source, home) / f"{template_id}.yaml"


def ids(source: str, home: Path) -> list[str]:
    return sorted(p.stem for p in folder(source, home).glob("*.yaml") if ID_RE.match(p.stem))


def read(source: str, template_id: str, home: Path) -> str:
    path = _path(source, template_id, home)
    if not path.is_file():
        raise TemplateError([t("template_not_found", id=template_id)], 404)
    return path.read_text(encoding="utf-8")


def resolve(ref: str, home: Path) -> tuple[str, str]:
    """"builtin:x", "user:x" or "x" -> (source, id)."""
    source, _, template_id = ref.rpartition(":")
    if source == BUILTIN:
        template_id = ALIASES.get(template_id, template_id)
    if source:
        read(source, template_id, home)
        return source, template_id
    if template_id in ALIASES and not _path(USER, template_id, home).is_file():
        return BUILTIN, ALIASES[template_id]
    found = [s for s in SOURCES if _path(s, template_id, home).is_file()]
    if not found:
        raise TemplateError([t("template_not_found", id=ref)], 404)
    if len(found) > 1:
        raise TemplateError([t("template_ambiguous", id=ref)], 409)
    return found[0], template_id


def summary(source: str, template_id: str, home: Path) -> dict:
    text = read(source, template_id, home)
    out = {"source": source, "id": template_id, "ref": f"{source}:{template_id}", "valid": True, "problems": [],
           "draft": False}
    try:
        wf = schema.parse(text)
    except schema.WorkflowError as e:
        out.update(valid=False, problems=e.messages(), name=template_id, draft=source == USER)
        try:
            data = yamlio.load(text)
        except yamlio.YAMLError:
            data = None
        if isinstance(data, dict):  # a draft keeps its name and description in the list
            out.update({key: data[key] for key in ("name", "description", "category") if key in data})
        return out
    out.update({key: wf.data.get(key) for key in ("name", "description", "version", "category", "tier", "based_on")})
    out["nodes"] = len(wf.nodes)
    out["inputs"] = len(wf.inputs)
    # What a run needs, for the library cards: required files, model calls (an upper bound when a condition picks a
    # branch), loops (a model call per part).
    out["docs"] = sum(1 for s in wf.inputs.values() if s["type"] == "file" and s.get("required", True))
    out["calls"] = sum(1 for n in wf.nodes.values() if n["type"] == "ai.cli")
    out["loops"] = sum(1 for n in wf.nodes.values() if n["type"] == "ai.map")
    out["branches"] = any(n["type"] == "condition" for n in wf.nodes.values())
    if source == BUILTIN:
        out["aliases"] = sorted(old for old, new in ALIASES.items() if new == template_id)
    return out


def listing(home: Path) -> list[dict]:
    return [summary(source, template_id, home) for source in SOURCES for template_id in ids(source, home)]


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    paths.replace(tmp, path)


def _check_new_id(new_id: str, home: Path) -> None:
    if not ID_RE.match(new_id or ""):
        raise TemplateError([t("bad_id", value=new_id)])
    if any(_path(source, new_id, home).exists() for source in SOURCES):
        raise TemplateError([t("template_exists", id=new_id)], 409)


def with_id(text: str, new_id: str, based_on: str | None = None) -> str:
    """The same YAML text with another top-level id (and based_on), keeping the comments and the layout."""
    text, count = re.subn(r"^id:[^\n]*$", f"id: {new_id}", text, count=1, flags=re.M)
    if not count:
        text = f"id: {new_id}\n" + text
    if based_on is not None:
        text = re.sub(r"^based_on:[^\n]*\n?", "", text, flags=re.M)
        line = "based_on: " + " ".join(based_on.split())  # one line, and not read as a replacement pattern
        text = re.sub(r"^(id: [^\n]*)$", lambda m: f"{m.group(1)}\n{line}", text, count=1, flags=re.M)
    return text


def customize(source: str, template_id: str, new_id: str, home: Path) -> str:
    """Copies a template into the user namespace under new_id. Returns the new id."""
    text = read(source, template_id, home)
    _check_new_id(new_id, home)
    try:
        version = schema.parse(text).data.get("version")
    except schema.WorkflowError:
        version = None
    based_on = f"{source}:{template_id}" + (f"@{version}" if version is not None else "")
    new_text = with_id(text, new_id, based_on)
    try:
        schema.parse(new_text)
    except schema.WorkflowError as e:
        raise TemplateError(e.messages()) from None
    _write(_path(USER, new_id, home), new_text)
    return new_id


def save(template_id: str, text: str, home: Path) -> None:
    """Saves an edited user template. The text must pass the full check; its id must stay the same."""
    path = _path(USER, template_id, home)
    if _path(BUILTIN, template_id, home).exists() and not path.exists():
        raise TemplateError([t("template_builtin_readonly")], 403)
    if not path.exists():
        raise TemplateError([t("template_not_found", id=template_id)], 404)
    try:
        wf = schema.parse(text)
    except schema.WorkflowError as e:
        raise TemplateError(e.messages()) from None
    if wf.id != template_id:
        raise TemplateError([t("template_id_mismatch", found=wf.id, id=template_id)])
    _write(path, text)


def save_model(template_id: str, data, home: Path, drop_comments: bool = False, draft: bool = False) -> dict:
    """Saves a workflow edited in the visual editor (a mapping). The same rule as save(): only a workflow that
    passes the full check is saved, unless draft is set (save_draft). The comments of the stored file are put back
    next to their key or list entry (yamlio.keep_comments); when some cannot be placed (their node or key is gone)
    and drop_comments is false, nothing is saved and {"saved": False, "comments": n} tells the editor to ask the
    user first."""
    if not _path(USER, template_id, home).exists():
        save(template_id, "", home)  # raises the reason: a built-in template, or no such template
    old = read(USER, template_id, home)
    text, lost = yamlio.keep_comments(old, schema.dump(data))
    if lost and not drop_comments:
        return {"saved": False, "comments": lost}
    if draft:
        return {**save_draft(template_id, text, home), "saved": True, "comments": lost}
    save(template_id, text, home)
    return {"saved": True, "comments": lost}


def create_model(data, home: Path, draft: bool = False) -> str:
    """Adds a new workflow from the visual editor under the id written in it (as a draft: also with problems).
    Returns that id."""
    if draft:
        new_id = data.get("id") if isinstance(data, dict) else None
        save_draft(new_id, schema.dump(data), home, create=True)
        return new_id
    return import_text(schema.dump(data), home)


def save_draft(template_id: str, text: str, home: Path, create: bool = False) -> dict:
    """Saves a user template even when it has problems (a draft); create: a new one under template_id. The text
    must be at most 1 MB, must not contain credentials, and when it is a mapping its id must be template_id.
    Returns the template's summary (valid, problems, draft)."""
    path = _path(USER, template_id, home)
    if create:
        _check_new_id(template_id, home)
    elif _path(BUILTIN, template_id, home).exists() and not path.exists():
        raise TemplateError([t("template_builtin_readonly")], 403)
    elif not path.exists():
        raise TemplateError([t("template_not_found", id=template_id)], 404)
    if len(text) > 1_000_000:
        raise TemplateError([t("yaml_too_large")])
    try:
        data = yamlio.load(text)
    except yamlio.YAMLError:
        data = None
    problems: list[schema.Problem] = []
    if isinstance(data, dict):
        if data.get("id") != template_id:
            raise TemplateError([t("draft_wrong_id", found=data.get("id"), id=template_id)])
        try:
            schema.check(copy.deepcopy(data))
        except schema.WorkflowError as e:
            problems = e.problems
    else:  # text that is not (yet) a YAML mapping: look for credential keys and values line by line
        for n, line in enumerate(text.splitlines(), 1):
            key = re.match(r"\s*(?:-\s*)?[\"']?([^:#\"'\s]+)[\"']?\s*:", line)
            if key and schema.CREDENTIAL_KEY.search(key.group(1)):
                problems.append(schema.Problem(f"line {n}", "credential_key"))
            if schema.CREDENTIAL_VALUE.search(line):
                problems.append(schema.Problem(f"line {n}", "credential_value"))
    credentials = [p.message() for p in problems if p.key.startswith("credential")]
    if credentials:
        raise TemplateError([t("draft_credentials", problems="; ".join(credentials))])
    _write(path, text)
    return summary(USER, template_id, home)


def import_text(text: str, home: Path) -> str:
    """Adds a workflow file to the user's templates under the id written in it. Returns that id."""
    try:
        wf = schema.parse(text)
    except schema.WorkflowError as e:
        raise TemplateError(e.messages()) from None
    _check_new_id(wf.id, home)
    _write(_path(USER, wf.id, home), text)
    return wf.id


def delete(source: str, template_id: str, home: Path) -> None:
    if source != USER:
        raise TemplateError([t("template_builtin_readonly")], 403)
    path = _path(USER, template_id, home)
    if not path.exists():
        raise TemplateError([t("template_not_found", id=template_id)], 404)
    path.unlink()
