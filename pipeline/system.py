"""Operating-system specific operations for macOS, Windows and Linux, in one place."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"


# --- commands -----------------------------------------------------------------

def resolve(argv: list[str]) -> list[str]:
    """Finds the full path of the program and returns a command line that runs it.

    On Windows, npm tools are .cmd files, which run through cmd.exe. cmd.exe removes the first and last quote of
    a command line that has more than two, so a path with a space ("C:\\Users\\Ahmet Çelik\\...") would break.
    "/s" with one extra pair of outer quotes keeps every inner quote. The arguments are fixed tool options,
    validated model names and temporary paths; the book text goes through stdin, never through cmd.exe.
    """
    found = shutil.which(argv[0])
    argv = [found, *argv[1:]] if found else argv
    if IS_WINDOWS and argv[0].lower().endswith((".cmd", ".bat")):
        return ["cmd.exe", "/d", "/s", "/c", '"' + subprocess.list2cmdline(argv) + '"']
    return argv


def hidden_window() -> dict:
    """Windows: no console window for a child process (a background run has no console of its own)."""
    return {"creationflags": subprocess.CREATE_NO_WINDOW} if IS_WINDOWS else {}


def new_process_group() -> dict:
    """Popen arguments for a background job: its own process group, so that it can be stopped with its children,
    and on Windows no console, so that closing the interface window does not end a running translation."""
    if IS_WINDOWS:
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW}
    return {"start_new_session": True}


def stop_tree(pid: int) -> None:
    """Stops a process and all processes it started (the pipeline and its claude/codex/gemini calls)."""
    if IS_WINDOWS:
        subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"], capture_output=True)
        return
    try:
        group = os.getpgid(pid)
        if group != os.getpgrp():
            os.killpg(group, signal.SIGTERM)
        else:
            os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass


# --- file lock ----------------------------------------------------------------

def try_lock(handle) -> bool:
    """Non-blocking exclusive lock on an open file. Released when the file is closed or the process ends."""
    if IS_WINDOWS:
        import msvcrt
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            return True
        except OSError:
            return False
    import fcntl
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except BlockingIOError:
        return False


def unlock(handle) -> None:
    if IS_WINDOWS:
        import msvcrt
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl
        fcntl.flock(handle, fcntl.LOCK_UN)


def is_locked(path: Path) -> bool:
    """True when another process holds the lock on this file."""
    if not path.exists():
        return False
    with open(path, "a+") as handle:
        if try_lock(handle):
            unlock(handle)
            return False
        return True


# --- sleep --------------------------------------------------------------------

def keep_awake() -> bool:
    """Prevents the computer from sleeping while this process runs. Returns False when this is not possible."""
    if IS_MAC and shutil.which("caffeinate"):
        try:
            subprocess.Popen(["caffeinate", "-i", "-s", "-w", str(os.getpid())],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            return False
    if IS_WINDOWS:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        return bool(ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED))
    if shutil.which("systemd-inhibit"):
        try:
            subprocess.Popen(["systemd-inhibit", "--what=sleep:idle", "--why=translation",
                              "sh", "-c", f"while kill -0 {os.getpid()} 2>/dev/null; do sleep 30; done"],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError:
            return False
    return False


def can_keep_awake() -> bool:
    return (IS_MAC and bool(shutil.which("caffeinate"))) or IS_WINDOWS or bool(shutil.which("systemd-inhibit"))


# --- terminal -----------------------------------------------------------------

def _linux_terminal() -> list[str] | None:
    for name, flag in (("x-terminal-emulator", "-e"), ("gnome-terminal", "--"), ("konsole", "-e"), ("xterm", "-e")):
        if shutil.which(name):
            return [name, flag]
    return None


def terminal_command(command: str, path_dirs: list[str], note: str = "") -> str:
    """The command line for a new terminal: the given folders are put in front of PATH first, because a new
    terminal does not know the tools that the application installed into its own folder. note: a line shown
    first, telling the user what to do in the window (a fixed message of the application)."""
    if IS_WINDOWS:
        note = re.sub(r'[&|<>^%"]', "", note)  # characters that cmd would read as commands
        line = f"echo {note} && {command}" if note else command
        return f'set "PATH={os.pathsep.join(path_dirs)};%PATH%" && {line}' if path_dirs else line
    line = f"printf '%s\\n\\n' {shlex.quote(note)}; {command}" if note else command
    quoted = ":".join("'" + d.replace("'", "'\\''") + "'" for d in path_dirs)
    return f'export PATH={quoted}:"$PATH"; {line}' if path_dirs else line


def can_open_terminal() -> bool:
    return IS_MAC or IS_WINDOWS or _linux_terminal() is not None


def open_terminal(command: str, path_dirs: list[str] | None = None, note: str = "") -> bool:
    """Runs a fixed command in a new terminal window. Returns False when no terminal can be opened.

    Only fixed commands from tools.TOOLS and the application's own folders arrive here; user input never does.
    """
    command = terminal_command(command, path_dirs or [], note)
    if IS_MAC:
        applescript = command.replace("\\", "\\\\").replace('"', '\\"')
        script = f'tell application "Terminal"\nactivate\ndo script "{applescript}"\nend tell'
        try:
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True, timeout=60)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            return False  # for example: the user did not allow controlling Terminal
        return True
    if IS_WINDOWS:
        subprocess.Popen(["cmd", "/c", "start", "", "cmd", "/k", command])
        return True
    terminal = _linux_terminal()
    if terminal:
        subprocess.Popen([*terminal, "sh", "-c", f"{command}; exec sh"])
        return True
    return False


# --- PDF ----------------------------------------------------------------------

def find_browser() -> str | None:
    """A Chromium browser (Chrome, Edge, Chromium) that can print a page to PDF. Windows always has Edge."""
    if IS_MAC:
        candidates = [f"/Applications/{app}.app/Contents/MacOS/{app}" for app in ("Google Chrome", "Microsoft Edge", "Chromium", "Brave Browser")]
        candidates += [str(Path.home() / c.lstrip("/")) for c in candidates]
    elif IS_WINDOWS:
        roots = [os.environ.get(k, "") for k in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA")]
        candidates = [str(Path(root) / sub) for root in roots if root for sub in (
            r"Google\Chrome\Application\chrome.exe", r"Microsoft\Edge\Application\msedge.exe", r"Chromium\Application\chrome.exe")]
    else:
        candidates = [shutil.which(n) or "" for n in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser", "microsoft-edge")]
    return next((c for c in candidates if c and Path(c).is_file()), None)


def print_pdf(html_path: Path, pdf_path: Path, timeout: int = 120) -> bool:
    """Prints an HTML file to PDF with a headless browser. False when no browser is found or printing fails.

    The browser gets its own empty profile, so that a browser window the user has open is not involved."""
    browser = find_browser()
    if not browser:
        return False
    profile = pdf_path.parent / "browser-profile"
    argv = [browser, "--headless=new", "--disable-gpu", "--no-first-run", "--no-default-browser-check",
            "--no-pdf-header-footer", f"--user-data-dir={profile}", f"--print-to-pdf={pdf_path}", html_path.as_uri()]
    try:
        subprocess.run(argv, capture_output=True, timeout=timeout, **hidden_window())
    except (subprocess.TimeoutExpired, OSError):
        return False
    return pdf_path.is_file() and pdf_path.stat().st_size > 0
