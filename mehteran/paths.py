"""Where Mehteran keeps the user's data: outside the code folder, in the operating system's data folder.

macOS ~/Library/Application Support/Mehteran, Windows %LOCALAPPDATA%\\Mehteran, Linux $XDG_DATA_HOME/mehteran or
~/.local/share/mehteran. The environment variable MEHTERAN_HOME replaces it (the tests always set it).
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

CODE = Path(__file__).resolve().parent          # the mehteran package
REPO = CODE.parent                              # the folder that also holds the translation app (pipeline/)
BUILTIN_TEMPLATES = CODE / "templates"
SUBFOLDERS = ("templates", "workflows", "executions", "databases")


def default_home() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Mehteran"
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "Mehteran"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "mehteran"


def home() -> Path:
    """The data folder, created with its subfolders on first use."""
    root = Path(os.environ.get("MEHTERAN_HOME") or default_home()).expanduser().resolve()
    for name in SUBFOLDERS:
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def inside(base: Path, *parts: str) -> Path | None:
    """base/parts resolved, or None when the result leaves base (path traversal, an absolute part, a link out)."""
    base = base.resolve()
    try:
        path = base.joinpath(*parts).resolve()
    except (OSError, ValueError):
        return None
    return path if path == base or path.is_relative_to(base) else None


def replace(src: Path, dst: Path) -> None:
    """os.replace that waits a moment when Windows refuses it because another thread or program has dst open
    (a reader of the file that is being replaced). Other systems never wait."""
    for attempt in range(40):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if sys.platform != "win32" or attempt == 39:
                raise
            time.sleep(0.05)


def runtime() -> Path:
    """<code folder>/.runtime, shared with the translation app (pipeline.runtime): the tools installed without
    administrator rights. MEHTERAN_RUNTIME_ROOT replaces the code folder (the tests set it)."""
    if os.environ.get("MEHTERAN_RUNTIME_ROOT"):
        return Path(os.environ["MEHTERAN_RUNTIME_ROOT"]) / ".runtime"
    from pipeline.core import ROOT
    return ROOT / ".runtime"
