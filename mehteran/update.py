"""Brings a git copy of Mehteran up to date ("mehter update", run by the launcher before "ui"), and keeps the book
translation app on the computers that used it.

Update: fetch, then a fast-forward merge of the branch's upstream. An update that cannot be applied cleanly (no
network, no sign-in, code changed on this computer) is skipped with a message; Mehteran then starts as it is. A copy
without git (a zip file, the npm package) is not updated here.

The book translation app (pipeline/, ./translate) was part of this repository; it is no longer part of Mehteran.
On a computer that used it (books/ holds a book, or its config.toml exists), Mehteran puts its code back
from the git history into the same place, once, when the code is missing: "./translate ui", the books, the settings
and the instructions keep working as before. The restored paths are in .gitignore, so later updates leave them
alone; the translation app itself gets no more updates.
"""

from __future__ import annotations

import io
import os
import shutil
import subprocess
import tarfile
from pathlib import Path

from .common.system import hidden_window
from .i18n import t

# The files the translation app needs, as they were in the repository. The user's own files (books/, config.toml,
# prompts/*.md, prompts/custom/, glossary/) were never in git: an update never touched them.
TRANSLATION_PATHS = ("pipeline", "translate", "translate.cmd", "scripts/start.sh", "scripts/start.cmd",
                     "Open Interface.command", "Open Interface.bat", "config.default.toml", "prompts/defaults",
                     "docs/guide.md", "docs/guide.tr.md")
MARKER = "pipeline/core.py"  # present while the translation app's code is there


def _git(root: Path, *args: str, timeout: int = 60, text: bool = True) -> subprocess.CompletedProcess:
    # Never wait for a user name or password: a repository without a stored sign-in is just skipped.
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never", "GIT_ASKPASS": "", "SSH_ASKPASS": ""}
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=text, timeout=timeout, env=env,
                          stdin=subprocess.DEVNULL, **({"encoding": "utf-8", "errors": "replace"} if text else {}),
                          **hidden_window())


def _say(message: str) -> None:
    print(message, flush=True)


def update(root: Path) -> int:
    """Returns 0 also when the update is skipped: starting Mehteran matters more than updating it."""
    if not (root / ".git").exists() or not shutil.which("git"):
        return 0
    try:
        if _git(root, "fetch", "--quiet").returncode != 0:
            _say(t("update_skipped_offline"))
            return 0
        behind = _git(root, "rev-list", "--count", "HEAD..@{upstream}")
        if behind.returncode != 0 or behind.stdout.strip() in ("", "0"):
            return 0  # up to date, or a branch without an upstream
        result = _git(root, "merge", "--ff-only", "--quiet", "@{upstream}", timeout=120)
        if result.returncode != 0:
            lines = (result.stderr or result.stdout).strip().splitlines()
            _say(t("update_skipped_local", reason=lines[-1] if lines else ""))
            return 0
        _say(t("update_done", count=behind.stdout.strip()))
    except (OSError, subprocess.TimeoutExpired):
        _say(t("update_skipped_offline"))
    finally:
        keep_translation(root)
    return 0


def used_translation(root: Path) -> bool:
    """The book translation app was used here: a book in books/, or its settings file."""
    books = root / "books"
    return (root / "config.toml").is_file() or (books.is_dir() and any(p.is_dir() for p in books.iterdir()))


def keep_translation(root: Path) -> bool:
    """Puts the translation app's code back from the git history when this computer used it and the code is gone.
    True when it did. Never raises: a copy without git history simply stays as it is."""
    if (root / MARKER).is_file() or not used_translation(root) or not (root / ".git").exists() or not shutil.which("git"):
        return False
    try:
        last = _git(root, "rev-list", "-1", "HEAD", "--", MARKER).stdout.strip()  # the last commit that changed it
        if not last:
            return False
        # Usually the commit that removed it: its parent has the code. If the file is still in that commit (it was
        # removed on this computer, not in git), that commit itself has the newest code.
        source = last if _git(root, "cat-file", "-e", f"{last}:{MARKER}").returncode == 0 else f"{last}^"
        listed = _git(root, "ls-tree", "--name-only", source, "--", *TRANSLATION_PATHS)
        present = [p for p in listed.stdout.splitlines() if p] if listed.returncode == 0 else []
        if MARKER.split("/")[0] not in present:
            return False
        archive = _git(root, "archive", "--format=tar", source, "--", *present, timeout=120, text=False)
        if archive.returncode != 0:
            return False
        with tarfile.open(fileobj=io.BytesIO(archive.stdout)) as tar:
            tar.extractall(root, filter="data")  # "data": no absolute paths, no links out of root
    except (OSError, subprocess.SubprocessError, tarfile.TarError):
        return False
    _say(t("translation_kept"))
    return True
