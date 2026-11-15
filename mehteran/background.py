"""Mehteran in the background: the web server starts when the person signs in to the computer, without a terminal
window and without opening the browser, so that scheduled runs (schedules.py) start on time.

- macOS: a LaunchAgent (~/Library/LaunchAgents/<LABEL>.plist), loaded with launchctl.
- Linux: a systemd user service (~/.config/systemd/user/mehteran.service).
- Windows: a script in the Startup folder that starts pythonw without a window (not tested on Windows).

The service runs `python -m mehteran ui --no-browser` with the Python of this Mehteran, in the code folder, with
MEHTERAN_BACKGROUND=1 and the PATH of the moment it was turned on (the AI tools are found through it; a login service
gets a short PATH). No other variable of the environment is copied: API keys stay out of the service file.
A background server whose port is in use (Mehteran open in a terminal) waits until the port is free (web.serve).
Its output goes to <data>/logs/background.log; its process id to <data>/background.pid.
"""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
import threading
from pathlib import Path

from . import paths

LABEL = "com.mehteran.ui"
ENV_FLAG = "MEHTERAN_BACKGROUND"
PASSED = ("MEHTERAN_HOME", "TP_LANG")  # Mehteran's own settings, when set (never a key)


def is_background() -> bool:
    return os.environ.get(ENV_FLAG) == "1"


def supported() -> bool:
    return sys.platform in ("darwin", "win32") or sys.platform.startswith("linux")


def service_file() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Mehteran.vbs"
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / "systemd" / "user" / "mehteran.service"


def log_file(home: Path) -> Path:
    return Path(home) / "logs" / "background.log"


def pid_file(home: Path) -> Path:
    return Path(home) / "background.pid"


def _python() -> str:
    exe = Path(sys.executable)
    if sys.platform == "win32" and (exe.parent / "pythonw.exe").is_file():
        return str(exe.parent / "pythonw.exe")  # no console window
    return str(exe)


def _environment() -> dict:
    env = {ENV_FLAG: "1", "PATH": os.environ.get("PATH", "")}
    env.update({k: os.environ[k] for k in PASSED if os.environ.get(k)})
    return env


def _argv() -> list[str]:
    return [_python(), "-m", "mehteran", "ui", "--no-browser"]


def _alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if sys.platform == "win32":
        out = subprocess.run(["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True)
        return str(pid) in out.stdout
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def running_pid(home: Path) -> int | None:
    try:
        pid = int(pid_file(home).read_text().strip())
    except (OSError, ValueError):
        return None
    return pid if _alive(pid) else None


def status(home: Path) -> dict:
    pid = running_pid(home)
    return {"supported": supported(), "enabled": service_file().is_file(), "running": pid is not None,
            "this_server": is_background(), "service_file": str(service_file()), "log": str(log_file(home)),
            "platform": sys.platform}


def mark_running(home: Path) -> None:
    """Called by the background server once it listens."""
    pid_file(home).write_text(str(os.getpid()), encoding="utf-8")


# --- turning it on and off -----------------------------------------------------------------------------------

def _launchctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["launchctl", *args], capture_output=True, text=True, timeout=30)


def _systemctl(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", "--user", *args], capture_output=True, text=True, timeout=30)


def service_text(home: Path) -> bytes:
    """The service file's content for this system."""
    log = str(log_file(home))
    if sys.platform == "darwin":
        return plistlib.dumps({"Label": LABEL, "ProgramArguments": _argv(), "WorkingDirectory": str(paths.REPO),
                               "EnvironmentVariables": _environment(), "RunAtLoad": True,
                               "KeepAlive": {"SuccessfulExit": False}, "ThrottleInterval": 30,
                               "StandardOutPath": log, "StandardErrorPath": log, "ProcessType": "Background"})
    if sys.platform == "win32":
        def vbs(text: str) -> str:
            return '"' + text.replace('"', '""') + '"'
        command = " ".join('""' + part.replace('"', "") + '""' for part in _argv())
        lines = ['Set shell = CreateObject("WScript.Shell")', 'Set env = shell.Environment("Process")']
        lines += [f"env({vbs(k)}) = {vbs(v)}" for k, v in _environment().items()]
        lines += [f"shell.CurrentDirectory = {vbs(str(paths.REPO))}", f'shell.Run "{command}", 0, False']
        return ("\r\n".join(lines) + "\r\n").encode("utf-16")

    def quoted(text: str) -> str:
        return '"' + text.replace("\\", "\\\\").replace('"', '\\"').replace("%", "%%") + '"'
    env = "\n".join(f"Environment={quoted(f'{k}={v}')}" for k, v in _environment().items())
    return (f"[Unit]\nDescription=Mehteran (local AI workflows)\n\n[Service]\n"
            f"ExecStart={' '.join(quoted(a) for a in _argv())}\nWorkingDirectory={quoted(str(paths.REPO))}\n{env}\n"
            f"Restart=on-failure\nRestartSec=30\nStandardOutput=append:{log}\nStandardError=append:{log}\n\n"
            f"[Install]\nWantedBy=default.target\n").encode("utf-8")


def turn_on(home: Path) -> None:
    """Writes the service file and starts the service now (it waits while this server holds the port)."""
    if not supported():
        raise OSError("not supported")
    log_file(home).parent.mkdir(parents=True, exist_ok=True)
    target = service_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(service_text(home))
    if sys.platform == "darwin":
        domain = f"gui/{os.getuid()}"
        _launchctl("bootout", f"{domain}/{LABEL}")
        done = _launchctl("bootstrap", domain, str(target))
        if done.returncode != 0:
            raise OSError(done.stderr.strip() or "launchctl bootstrap")
    elif sys.platform == "win32":
        if running_pid(home) is None:
            subprocess.Popen(["wscript.exe", str(target)], close_fds=True)
    else:
        _systemctl("daemon-reload")
        done = _systemctl("enable", "--now", "mehteran.service")
        if done.returncode != 0:
            raise OSError(done.stderr.strip() or "systemctl enable")


def turn_off(home: Path) -> None:
    """Removes the service file and stops the background server. When this process is that server, it stops a
    moment later, after the reply to the request has gone out."""
    pid = running_pid(home)
    if sys.platform.startswith("linux"):
        _systemctl("disable", "mehteran.service")  # while its file is still there
    service_file().unlink(missing_ok=True)

    def stop():
        if sys.platform == "darwin":
            _launchctl("bootout", f"gui/{os.getuid()}/{LABEL}")
        elif sys.platform.startswith("linux"):
            _systemctl("stop", "mehteran.service")
            _systemctl("daemon-reload")
        elif pid and pid != os.getpid():
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
        elif pid:
            os._exit(0)
    if is_background():
        threading.Timer(0.5, stop).start()
    else:
        stop()
