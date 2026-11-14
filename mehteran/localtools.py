"""Helpers for the tools that Mehteran installs into the shared <code folder>/.runtime folder (Ollama, Tesseract OCR,
Typst, Pandoc, whisper.cpp with ffmpeg, qpdf):
checked downloads, sizes, the computer's memory and free disk, and a subprocess that a cancel or a timeout stops.

Every download has a pinned version and a SHA-256 sum written in this code; a file whose sum differs is deleted and
never used. The download itself is the translation app's (pipeline.runtime._download: progress on stdout, which the
install job's log shows).
"""

from __future__ import annotations

import ctypes
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

from .i18n import t


class ToolError(RuntimeError):
    """A local tool is missing or failed; the message is shown to the user."""


def download_verified(url: str, dest: Path, sha256: str) -> None:
    """Downloads url to dest and checks its SHA-256 sum; a wrong file is deleted and refused."""
    from pipeline import runtime
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    runtime._download(url, part)
    digest = hashlib.sha256()
    with open(part, "rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != sha256.lower():
        part.unlink(missing_ok=True)
        raise ToolError(t("download_checksum", name=dest.name))
    os.replace(part, dest)


def dir_size(path: Path) -> int | None:
    if not path.exists():
        return None
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file() and not p.is_symlink())


def disk_free(path: Path) -> int | None:
    """Free bytes on the disk that holds path (or its nearest existing parent)."""
    path = Path(path)
    while not path.exists() and path != path.parent:
        path = path.parent
    try:
        return shutil.disk_usage(path).free
    except OSError:
        return None


def memory() -> int | None:
    """The computer's memory in bytes, or None when it cannot be read."""
    try:
        if sys.platform == "darwin":
            out = subprocess.run(["sysctl", "-n", "hw.memsize"], capture_output=True, text=True, timeout=5).stdout
            return int(out.strip())
        if sys.platform == "win32":
            class Status(ctypes.Structure):
                _fields_ = [("length", ctypes.c_ulong), ("load", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                            ("avail", ctypes.c_ulonglong), ("pt", ctypes.c_ulonglong), ("pa", ctypes.c_ulonglong),
                            ("vt", ctypes.c_ulonglong), ("va", ctypes.c_ulonglong), ("ve", ctypes.c_ulonglong)]
            status = Status()
            status.length = ctypes.sizeof(Status)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))  # type: ignore[attr-defined]
            return int(status.total)
        text = Path("/proc/meminfo").read_text()
        return int(re.search(r"MemTotal:\s+(\d+) kB", text).group(1)) * 1024
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        return None


def run(argv: list[str], abort: threading.Event | None, timeout: float, cwd: Path | None = None,
        env: dict | None = None) -> tuple[int, str]:
    """Runs a command; stops it with its children on abort or after timeout. Returns (exit code, the end of its
    error output). Raises ToolError on a timeout and InterruptedError on an abort."""
    from pipeline import system
    proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.PIPE, **system.new_process_group())  # also: no console window
    errors: list[bytes] = []
    reader = threading.Thread(target=lambda: errors.append(proc.stderr.read()), daemon=True)
    reader.start()
    end = time.time() + timeout
    try:
        while proc.poll() is None:
            if abort is not None and abort.wait(0.1):
                system.stop_tree(proc.pid)
                proc.wait(10)
                raise InterruptedError()
            if abort is None:
                time.sleep(0.1)
            if time.time() > end:
                system.stop_tree(proc.pid)
                proc.wait(10)
                raise ToolError(t("tool_timeout", name=Path(argv[0]).name, seconds=int(timeout)))
        reader.join(5)
    finally:
        reader.join(1)
        proc.stderr.close()
    return proc.returncode, b"".join(errors).decode("utf-8", "replace")[-1000:]


# --- shared by the converters and the speech tools (typst.py, pandoc.py, speech.py, qpdf.py) ---------------

def exe(name: str) -> str:
    return name + ".exe" if sys.platform == "win32" else name


def conda_bin(prefix: Path) -> Path:
    """The program folder of a conda-forge prefix."""
    return prefix / "Library" / "bin" if sys.platform == "win32" else prefix / "bin"


def find_program(name: str, own: list[Path]) -> tuple[Path | None, str | None]:
    """(program, "mehteran" or "system"): Mehteran's own copy first (the first existing path of own), then PATH."""
    for candidate in own:
        if candidate.is_file():
            return candidate, "mehteran"
    found = shutil.which(name)
    return (Path(found), "system") if found else (None, None)


def program_version(program: Path | None, *args: str) -> str | None:
    """The first version number that `program args` prints, or None."""
    if not program:
        return None
    try:
        out = subprocess.run([str(program), *(args or ("--version",))], capture_output=True, text=True, timeout=20,
                             stdin=subprocess.DEVNULL)
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"(\d+\.\d+(\.\d+)?)", out.stdout + out.stderr)
    return m.group(1) if m else None


def platform_key() -> tuple[str, str]:
    """("darwin" | "linux" | "windows", "arm64" | "x64" | the machine's own name)."""
    import platform
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64" if machine in ("x86_64", "amd64") else machine
    return {"darwin": "darwin", "win32": "windows"}.get(sys.platform, "linux"), arch


def install_archive(url: str, sha256: str, target: Path) -> None:
    """Downloads a release archive (zip, tar.gz, tar.xz), checks its SHA-256 sum and unpacks it into target, which it
    replaces. An archive with a single top folder gives that folder's content."""
    from pipeline import runtime
    from . import paths
    base = paths.runtime()
    base.mkdir(parents=True, exist_ok=True)
    name = url.rsplit("/", 1)[-1]
    with tempfile.TemporaryDirectory(dir=base) as tmp:
        archive = Path(tmp) / name
        download_verified(url, archive, sha256)
        print(t("download_verified", name=name), flush=True)
        unpacked = Path(tmp) / "unpacked"
        unpacked.mkdir()
        runtime._safe_extract(archive, "zip" if name.endswith(".zip") else "tar", unpacked)
        entries = list(unpacked.iterdir())
        top = entries[0] if len(entries) == 1 and entries[0].is_dir() else unpacked
        if target.exists():
            shutil.rmtree(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(top, target)


def micromamba_missing() -> bool:
    """True when a conda-forge install must first bring micromamba (with Poppler, the translation app's installer)."""
    from . import paths
    return not (paths.runtime() / "micromamba" / exe("micromamba")).exists()


def conda_install(prefix: Path, specs: list[str]) -> None:
    """Installs pinned conda-forge packages into prefix with micromamba (which checks every package against the
    channel's SHA-256 sums). micromamba comes with the translation app's Poppler installer when it is missing.
    Output goes to stdout (the job log); raises ToolError when a step fails."""
    from pipeline import runtime
    from . import paths
    base = paths.runtime()
    micromamba = base / "micromamba" / exe("micromamba")
    if not micromamba.exists():
        print(t("ocr_installing_poppler"), flush=True)
        runtime.install_poppler(base.parent)  # <root>/.runtime/poppler and <root>/.runtime/micromamba
    env = {**os.environ, "MAMBA_ROOT_PREFIX": str(base / "mamba"), "CONDA_PKGS_DIRS": str(base / "mamba" / "pkgs")}
    root_prefix = ["--root-prefix", str(base / "mamba")]
    print(t("conda_installing", specs=" ".join(specs)), flush=True)
    for argv in ([str(micromamba), "create", *root_prefix, "--yes", "--prefix", str(prefix), "--channel", "conda-forge",
                  "--override-channels", *specs],
                 [str(micromamba), "clean", "--all", "--yes"]):
        print("> " + subprocess.list2cmdline(argv), flush=True)
        if subprocess.run(argv, env=env, stdin=subprocess.DEVNULL).returncode != 0:
            raise ToolError(t("conda_install_failed", specs=" ".join(specs)))
