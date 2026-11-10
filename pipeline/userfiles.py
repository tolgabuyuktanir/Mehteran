"""The user's own files: config.toml (workflow, models, settings) and the instructions in prompts/.

The repository holds only their defaults (config.default.toml, prompts/defaults/). The user's copies are not in git,
so an update ("git pull") never changes them:
- config.toml is made from config.default.toml once. Later defaults add only what config.toml lacks (a new tool, a
  new setting); an existing value is never changed, and the workflow ([stages], [nodes]) is never touched.
- An instruction is copied from its default once. When the default changes, the copy follows only if the user never
  edited it; prompts/.defaults.json records the default that each copy came from.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tomllib
from pathlib import Path

from . import configfile

WORKFLOW_SECTIONS = {"stages", "nodes"}  # never changed by an update


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ensure(root: Path) -> None:
    ensure_config(root)
    ensure_prompts(root)


def ensure_config(root: Path) -> None:
    default, config = root / "config.default.toml", root / "config.toml"
    if not default.exists():
        return  # a test project or an older copy: config.toml is all there is
    if not config.exists():
        shutil.copyfile(default, config)
        return
    text = config.read_text(encoding="utf-8")
    merged = merge_defaults(text, default.read_text(encoding="utf-8"))
    if merged != text:
        config.write_text(merged, encoding="utf-8")


def _sections(cfg: dict, prefix: str = "") -> dict[str, dict]:
    """{"general": {...}, "providers.claude": {...}}: the tables that hold values (nested tables are flattened)."""
    out = {}
    for key, value in cfg.items():
        if isinstance(value, dict):
            name = prefix + key
            plain = {k: v for k, v in value.items() if not isinstance(v, dict)}
            if plain or not any(isinstance(v, dict) for v in value.values()):
                out[name] = plain
            out.update(_sections(value, name + "."))
    return out


def _block(text: str, section: str) -> str:
    """The text of a section in the default file: its comment lines, its header and its body."""
    m = re.search(rf"^\[{re.escape(section)}\][ \t]*\n", text, re.M)
    start = configfile._comment_block_start(text, m.start())
    _, end = configfile._section_span(text, section)
    end = configfile._comment_block_start(text, end)
    return text[start:end].strip("\n") + "\n"


def merge_defaults(text: str, default_text: str) -> str:
    """config.toml with what the defaults have and it lacks. Nothing that it has is changed."""
    try:
        have, defaults = _sections(tomllib.loads(text)), _sections(tomllib.loads(default_text))
    except tomllib.TOMLDecodeError:
        return text  # a broken file is the user's to fix; the application reports it when it loads
    for section, values in defaults.items():
        if section in WORKFLOW_SECTIONS:
            continue
        if section not in have:
            # A new section goes before [languages], which stays the last section (new languages are appended).
            m = re.search(r"^\[languages\][ \t]*$", text, re.M)
            at = configfile._comment_block_start(text, m.start()) if m else len(text)
            text = text[:at].rstrip("\n") + "\n\n" + _block(default_text, section) + "\n" + text[at:].lstrip("\n")
            continue
        for key, value in values.items():
            if key not in have[section]:
                text = configfile.set_key(text, section, key, json.dumps(value, ensure_ascii=False))
    return text


def ensure_prompts(root: Path) -> None:
    defaults = root / "prompts" / "defaults"
    if not defaults.is_dir():
        return
    record_path = root / "prompts" / ".defaults.json"
    try:
        record = json.loads(record_path.read_text(encoding="utf-8")) if record_path.exists() else {}
    except ValueError:
        record = {}
    before = dict(record)
    for default in sorted(defaults.glob("*.md")):
        local = root / "prompts" / default.name
        new = _sha(default)
        if not local.exists():
            shutil.copyfile(default, local)
            record[default.name] = new
            continue
        mine = _sha(local)
        if mine == new:
            record[default.name] = new  # the same as the default (also after "Restore default")
        elif record.get(default.name) == mine:
            shutil.copyfile(default, local)  # never edited: it follows the new default
            record[default.name] = new
        # else: the user edited it; it stays as it is
    if record != before:
        record_path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8")
