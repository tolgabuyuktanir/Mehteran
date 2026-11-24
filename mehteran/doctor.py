"""mehter doctor: does each installed AI tool still understand what Mehteran asks of it?

Mehteran calls the tools' command-line programs with fixed options (mehteran/providers/) and reads what some of
them report about their usage limits (mehteran/usage.py). An update of a tool can drop an option or change a
report. For each installed tool this checks, without a model call:
- every option of Mehteran's command is in the tool's --help (of its subcommand, as "codex exec");
- Claude Code: its "/usage" report can be read (no model call: it answers from the account);
- Codex: its newest session log has a usage entry that can be read (missing until Codex was used once).
The result is one line per check; the exit code is 1 when a check failed.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from . import paths
from . import providers as adapters
from .common import system, tools
from .i18n import t


def _help(argv: list[str]) -> str:
    """The --help text of the program, or of its subcommand when the command starts with one ("codex exec")."""
    command = argv[:2] if len(argv) > 1 and not argv[1].startswith("-") else argv[:1]
    try:
        proc = subprocess.run(system.resolve([*command, "--help"]), capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=30, stdin=subprocess.DEVNULL, **system.hidden_window())
    except (OSError, subprocess.SubprocessError):
        return ""
    return proc.stdout + proc.stderr


def check_options(adapter) -> tuple[bool, list[str]]:
    """(the tool answered --help, the options of Mehteran's command that its help does not name)."""
    with tempfile.TemporaryDirectory() as tmp:
        argv = adapter.argv("", "", Path(tmp) / "out.txt")
    text = _help(argv)
    if not text.strip():
        return False, []
    return True, [a for a in dict.fromkeys(argv) if a.startswith("--") and a.split("=")[0] not in text]


def checks(home: Path) -> list[tuple[str, bool, str]]:
    """[(tool name, ok, message)] for every installed command-line tool."""
    from . import usage
    tools.extend_path(paths.REPO)
    out = []
    for adapter in adapters.ADAPTERS.values():
        if not getattr(adapter, "cli", True) or not adapter.program or not shutil.which(adapter.program):
            continue
        answered, missing = check_options(adapter)
        if not answered:
            out.append((adapter.name, False, t("doctor_no_help", program=adapter.program)))
        elif missing:
            out.append((adapter.name, False, t("doctor_options_missing", options=", ".join(missing))))
        else:
            out.append((adapter.name, True, t("doctor_options_ok")))
        if adapter.tool == "claude":
            try:
                found = usage.claude_usage(home, adapter.program)
            except (OSError, subprocess.SubprocessError):
                found = None
            out.append((adapter.name, found is not None, t("doctor_usage_ok" if found else "doctor_usage_unreadable")))
        if adapter.tool == "codex":
            found = usage.codex_limits()
            out.append((adapter.name, True, t("doctor_usage_ok" if found else "doctor_codex_no_log")))
    return out
