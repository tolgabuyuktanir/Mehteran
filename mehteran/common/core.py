"""Paths and file helpers shared by the modules of mehteran.common."""

from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path

from .. import paths

ROOT = paths.REPO  # the code folder: the tools that Mehteran installs go into <ROOT>/.runtime
_print_lock = threading.Lock()


class UserError(Exception):
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


def split_name(name: str) -> tuple[str, str]:
    """A model is "provider" or "provider/model", optionally with "@effort" (the thinking level, for example
    "claude/opus@high"). Returns (provider, model or "")."""
    provider, _, model = name.partition("@")[0].partition("/")
    return provider, model


def read_json(path: Path, default=None):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))
