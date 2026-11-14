"""Sharing a workflow as a file, and the preview shown before a shared file is imported.

The shared file is the workflow's own YAML with two top-level fields that the schema allows: based_on (the
built-in template it is, or the one it was made from) and author (an optional name). The preview shows everything
that the file would do here before it is added: its steps and their prompts, its inputs, the models and local tools it
needs, and its problems. The workflow check (schema.check) refuses credentials in any field, as for every import.
"""

from __future__ import annotations

import json
import re

from . import estimate, i18n, schema, templates, yamlio
from .nodes import REGISTRY

AUTHOR_LIMIT = 80
AUDIO = {"mp3", "wav", "m4a", "ogg", "opus", "flac", "aac", "mp4", "webm", "mov", "mkv"}
IMAGES = {"png", "jpg", "jpeg", "tif", "tiff"}


def _set_line(text: str, key: str, value: str) -> str:
    """The YAML text with one top-level "key: value" line (replaced, or added after the id line)."""
    text = re.sub(rf"^{key}:[^\n]*\n?", "", text, flags=re.M)
    line = f"{key}: {json.dumps(value, ensure_ascii=False)}"  # a JSON string is a YAML double-quoted scalar
    out, count = re.subn(r"^(id: [^\n]*)$", lambda m: f"{m.group(1)}\n{line}", text, count=1, flags=re.M)
    return out if count else f"{line}\n{text}"


def share_text(source: str, template_id: str, home, author: str = "") -> tuple[str, str]:
    """(file name, text) of the shared file "<id>.mehteran.yaml"."""
    text = templates.read(source, template_id, home)
    try:
        wf = schema.parse(text)
    except schema.WorkflowError as e:
        raise templates.TemplateError(e.messages()) from None
    if source == "builtin":
        version = wf.data.get("version")
        text = _set_line(text, "based_on", f"builtin:{template_id}" + (f"@{version}" if version is not None else ""))
    author = " ".join(str(author or "").split())[:AUTHOR_LIMIT]
    if author:
        text = _set_line(text, "author", author)
    try:
        schema.parse(text)
    except schema.WorkflowError as e:  # an author that looks like a credential, for example
        raise templates.TemplateError(e.messages()) from None
    return f"{template_id}.mehteran.yaml", text


def _prompts(wf: schema.Workflow) -> list[dict]:
    """Every instruction-like text of the steps: the multi-line fields and the texts for a person."""
    out = []
    for node_id in wf.order:
        node = wf.nodes[node_id]
        node_type = REGISTRY[node["type"]]
        for key, spec in node_type.config.items():
            value = (node.get("config") or {}).get(key)
            if spec.widget != "area" and spec.kind != "localized" and key != "question":
                continue
            text = i18n.localized(value) if isinstance(value, dict) else value
            if isinstance(text, str) and text.strip():
                out.append({"node": node_id, "label": node.get("label"), "type": node["type"], "field": key,
                            "field_label": spec.label, "text": text})
    return out


def _local_tools(wf: schema.Workflow) -> list[str]:
    """The local tools of the Setup tab that this workflow can need: typst, pandoc, ocr, speech."""
    need = []
    formats = set()
    for spec in wf.inputs.values():
        if spec["type"] == "file":
            formats |= set(spec.get("formats", schema.FILE_FORMATS))
    for node in wf.nodes.values():
        config = node.get("config") or {}
        if node["type"] == "document.export":
            chosen = set(config.get("formats") or ["md"])
            if "pdf" in chosen:
                need.append("typst")
            if "epub" in chosen or ("docx" in chosen and config.get("converter") == "pandoc"):
                need.append("pandoc")
        if node["type"] == "document.extract" and config.get("ocr") == "always":
            need.append("ocr")
    if formats & IMAGES:
        need.append("ocr")
    if formats & AUDIO:
        need.append("speech")
    return list(dict.fromkeys(need))


def preview(text: str, home, cfg: dict) -> dict:
    """What the import would add, for the preview drawer. Problems do not raise: they are part of the answer."""
    try:
        data = yamlio.load(text) if len(text) <= 1_000_000 else None
    except yamlio.YAMLError:
        data = None
    data = data if isinstance(data, dict) else {}
    out = {"id": data.get("id") if isinstance(data.get("id"), str) else "", "name": data.get("name"),
           "description": data.get("description"), "author": data.get("author"), "based_on": data.get("based_on"),
           "version": data.get("version"), "valid": False, "problems": []}
    try:
        wf = schema.parse(text)
    except schema.WorkflowError as e:
        out["problems"] = e.messages()
        return out
    found = estimate.estimate(wf, {}, cfg)
    out.update({"valid": True, "graph": wf.graph(), "input_specs": list(wf.inputs.values()),
                "outputs": wf.data.get("outputs") or [], "prompts": _prompts(wf), "local_tools": _local_tools(wf),
                "models": found["models"], "reads_web": any(s["type"] == "url" for s in wf.inputs.values()),
                "exists": any(templates._path(source, wf.id, home).exists() for source in templates.SOURCES)})
    return out
