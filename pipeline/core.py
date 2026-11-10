"""Configuration, paths and file helpers."""

from __future__ import annotations

import json
import os
import re
import threading
import time
import tomllib
from dataclasses import dataclass
from pathlib import Path

from .i18n import t

# TP_ROOT: the folder that holds books, prompts and the configuration (default: the code folder).
ROOT = Path(os.environ.get("TP_ROOT") or Path(__file__).resolve().parent.parent).resolve()
_print_lock = threading.Lock()


class PipelineError(Exception):
    """An error whose message is shown to the user as plain text."""


def say(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


def write_text(path: Path, text: str) -> None:
    """Writes to a temporary file first, so that a half-written file never counts as finished."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    for attempt in range(20):
        try:
            os.replace(tmp, path)
            return
        except PermissionError:  # Windows: another process has the file open for a moment
            if attempt == 19:
                raise
            time.sleep(0.05)


EFFORTS = ("low", "medium", "high", "xhigh", "max")


def split_name(name: str) -> tuple[str, str]:
    """A stage assignment is "provider" or "provider/model", optionally with "@effort" (the thinking level, for
    example "claude/opus@high"). Returns (provider, model or "")."""
    provider, _, model = name.partition("@")[0].partition("/")
    return provider, model


def effort_of(name: str) -> str:
    """The thinking level of an assignment ("" = the tool's default)."""
    return name.partition("@")[2]


def slug(name: str) -> str:
    """A file-name-safe form of an assignment name (Windows does not allow "/" or ":" in file names)."""
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=1) + "\n")


_PREPARED: set[Path] = set()


@dataclass
class Project:
    root: Path
    cfg: dict

    @classmethod
    def load(cls, root: Path = ROOT) -> "Project":
        if root not in _PREPARED:  # once per process: the user's files from the defaults (see userfiles.py)
            from . import userfiles  # imported here: userfiles needs configfile, which needs this module
            userfiles.ensure(root)
            _PREPARED.add(root)
        path = root / "config.toml"
        if not path.exists():
            raise PipelineError(t("config_missing", path=path))
        try:
            with path.open("rb") as f:
                cfg = tomllib.load(f)
        except tomllib.TOMLDecodeError as e:
            raise PipelineError(t("config_invalid", error=e)) from e
        return cls(root, cfg)

    def book_dir(self, book: str) -> Path:
        return self.root / "books" / book

    def language_name(self, code: str) -> str:
        name = self.cfg.get("languages", {}).get(code)
        if not name:
            raise PipelineError(t("unknown_language", code=code))
        return name

    def providers_for(self, stage: str) -> list[str]:
        value = self.cfg["stages"][stage]
        return [value] if isinstance(value, str) else list(value)

    def rules(self) -> str:
        """The publishing rules of prompts/rules.md: given to the models in every step that has {{rules}}."""
        path = self.root / "prompts" / "rules.md"
        text = path.read_text(encoding="utf-8").strip() if path.exists() else ""
        return text or "(none)"

    def prompt(self, name: str, **values: str) -> str:
        template = (self.root / "prompts" / f"{name}.md").read_text(encoding="utf-8")
        if "{{rules}}" in template:
            values.setdefault("rules", self.rules())
        # Single pass: inserted book text is not scanned again for placeholders.
        return re.sub(r"\{\{(\w+)\}\}", lambda m: values[m.group(1)], template)
