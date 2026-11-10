"""Brings a git copy of the application up to date when it starts ("./translate update", run by the launcher).

The user's own files (config.toml, the instructions in prompts/, the custom-step instructions) are kept exactly as
they are: they are copied aside first and written back after the update, whatever the update contains. An update
that cannot be applied cleanly (no network, no sign-in for a private repository, code changed on this computer)
is skipped with a message; the application then starts as it is.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from . import system
from .core import say
from .i18n import t


def user_files(root: Path) -> list[Path]:
    """The files that belong to the user and that an update must never change."""
    files = [root / "config.toml", root / "prompts" / ".defaults.json"]
    files += sorted((root / "prompts").glob("*.md"))
    files += sorted((root / "prompts" / "custom").glob("*.md"))
    return [f for f in files if f.is_file()]


def _git(root: Path, *args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    # Never wait for a user name or password: a private repository without a stored sign-in is just skipped.
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GIT_ASKPASS": "", "SSH_ASKPASS": ""}
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8",
                          errors="replace", timeout=timeout, env=env, stdin=subprocess.DEVNULL, **system.hidden_window())


def _book_running(root: Path) -> bool:
    return any(system.is_locked(lock) for lock in (root / "books").glob("*/work/.lock"))


def update(root: Path) -> int:
    """Returns 0 also when the update is skipped: starting the application matters more than updating it."""
    if not (root / ".git").exists() or not shutil.which("git"):
        return 0  # a copy from a zip file: updated by downloading it again
    if _book_running(root):
        say(t("update_skipped_running"))  # the running translation must not get new code in the middle
        return 0
    try:
        if _git(root, "fetch", "--quiet").returncode != 0:
            say(t("update_skipped_offline"))
            return 0
        behind = _git(root, "rev-list", "--count", "HEAD..@{upstream}")
        if behind.returncode != 0 or behind.stdout.strip() in ("", "0"):
            return 0  # up to date, or a branch without an upstream
        saved = {path: path.read_bytes() for path in user_files(root)}
        # An older copy still has some user files in git: their changes are put back after the update.
        tracked = [str(p.relative_to(root)) for p in saved if _git(root, "ls-files", "--error-unmatch", str(p)).returncode == 0]
        if tracked:
            _git(root, "checkout", "--", *tracked)
        result = _git(root, "merge", "--ff-only", "--quiet", "@{upstream}", timeout=120)
        for path, data in saved.items():  # written back whatever happened
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if result.returncode != 0:
            lines = (result.stderr or result.stdout).strip().splitlines()
            say(t("update_skipped_local", reason=lines[-1] if lines else ""))
            return 0
        say(t("update_done", count=behind.stdout.strip()))
    except (OSError, subprocess.TimeoutExpired):
        say(t("update_skipped_offline"))
    return 0
