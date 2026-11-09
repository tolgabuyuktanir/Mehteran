"""Installs the command-line tools for a user who has nothing installed.

Codex and Gemini are npm packages. When no suitable Node.js is on the computer, a portable Node.js (latest LTS)
is downloaded from nodejs.org into <root>/.runtime/node and checked against the published SHA-256 sums.
Each npm package is installed into its own folder, <root>/.runtime/tools/<tool>: no administrator rights are
needed, the system's npm permissions do not matter, and installing one tool cannot change another (npm
rebuilds the whole tree of a shared folder and can drop another package's platform binary).
Claude Code uses its official installer.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.request
import zipfile
from pathlib import Path

from . import system
from .core import PipelineError, say
from .i18n import t

NODE_DIST = "https://nodejs.org/dist"
MIN_NODE = 20  # Gemini CLI needs Node.js 20 or later
NPM_PACKAGES = {"codex": "@openai/codex", "gemini": "@google/gemini-cli"}
CLAUDE_INSTALL = {
    "posix": ["bash", "-c", "curl -fsSL https://claude.ai/install.sh | bash"],
    "windows": ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", "irm https://claude.ai/install.ps1 | iex"],
}


def runtime_dir(root: Path) -> Path:
    return root / ".runtime"


def node_bin_dir(root: Path) -> Path:
    home = runtime_dir(root) / "node"
    return home if system.IS_WINDOWS else home / "bin"


def tool_prefix(root: Path, tool: str) -> Path:
    return runtime_dir(root) / "tools" / tool


def tool_bin_dir(root: Path, tool: str) -> Path:
    prefix = tool_prefix(root, tool)
    return prefix if system.IS_WINDOWS else prefix / "bin"


def bin_dirs(root: Path) -> list[Path]:
    """Folders with the tools that this module installed; they go to the front of PATH."""
    return [tool_bin_dir(root, tool) for tool in NPM_PACKAGES] + [node_bin_dir(root)]


# --- Node.js ------------------------------------------------------------------

def _node_major(node: str) -> int:
    try:
        out = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=20, **system.hidden_window()).stdout
        return int(re.match(r"v(\d+)", out.strip()).group(1))
    except (OSError, subprocess.TimeoutExpired, AttributeError, ValueError):
        return 0


def _download(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "translation-pipeline"})
    with urllib.request.urlopen(request, timeout=60) as response, open(dest, "wb") as f:
        total = int(response.headers.get("Content-Length") or 0)
        done, shown = 0, -1
        while chunk := response.read(1024 * 1024):
            f.write(chunk)
            done += len(chunk)
            percent = done * 100 // total if total else -1
            if percent >= 0 and percent // 10 != shown:
                shown = percent // 10
                say(t("download_progress", percent=percent, mb=done // (1024 * 1024)))


def _node_file(version: str) -> tuple[str, str]:
    """(file name, archive kind) of the Node.js build for this computer."""
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64" if machine in ("x86_64", "amd64") else None
    if not arch:
        raise PipelineError(t("node_unsupported", machine=machine))
    if system.IS_WINDOWS:
        return f"node-{version}-win-{arch}.zip", "zip"
    if system.IS_MAC:
        return f"node-{version}-darwin-{arch}.tar.gz", "tar"
    return f"node-{version}-linux-{arch}.tar.xz", "tar"


def _safe_extract(archive: Path, kind: str, dest: Path) -> None:
    """Extracts without letting any entry escape the destination folder."""
    dest = dest.resolve()
    if kind == "zip":
        with zipfile.ZipFile(archive) as z:
            for name in z.namelist():
                if not (dest / name).resolve().is_relative_to(dest):
                    raise PipelineError(t("archive_unsafe"))
            z.extractall(dest)
        return
    with tarfile.open(archive) as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(dest, filter="data")
        else:  # Python 3.11 before 3.11.4
            for member in tar.getmembers():
                if not (dest / member.name).resolve().is_relative_to(dest) or member.isdev():
                    raise PipelineError(t("archive_unsafe"))
            tar.extractall(dest)


def install_node(root: Path) -> None:
    """Downloads the latest Node.js LTS into <root>/.runtime/node and verifies its SHA-256 sum."""
    with urllib.request.urlopen(urllib.request.Request(f"{NODE_DIST}/index.json", headers={"User-Agent": "translation-pipeline"}),
                                timeout=60) as response:
        releases = json.load(response)
    version = next(r["version"] for r in releases if r.get("lts"))
    name, kind = _node_file(version)
    say(t("node_downloading", version=version))
    with urllib.request.urlopen(urllib.request.Request(f"{NODE_DIST}/{version}/SHASUMS256.txt",
                                                       headers={"User-Agent": "translation-pipeline"}), timeout=60) as response:
        sums = response.read().decode("utf-8")
    expected = next((line.split()[0] for line in sums.splitlines() if line.endswith("  " + name)), None)
    if not expected:
        raise PipelineError(t("node_no_checksum", name=name))

    runtime = runtime_dir(root)
    runtime.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=runtime) as tmp:
        archive = Path(tmp) / name
        _download(f"{NODE_DIST}/{version}/{name}", archive)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        if digest != expected:
            raise PipelineError(t("node_checksum_mismatch"))
        unpacked = Path(tmp) / "unpacked"
        _safe_extract(archive, kind, unpacked)
        top = next(unpacked.iterdir())
        target = runtime / "node"
        if target.exists():
            shutil.rmtree(target)
        os.replace(top, target)
    say(t("node_installed", version=version))


def find_npm(root: Path) -> tuple[str, dict]:
    """Returns (npm command, environment). Uses the system Node.js when it is recent enough, else the portable one."""
    env = os.environ.copy()
    own = node_bin_dir(root)
    candidates = [own] + ([] if not shutil.which("node") else [None])
    for folder in candidates:
        node = shutil.which("node", path=str(folder)) if folder else shutil.which("node")
        npm = shutil.which("npm", path=str(folder)) if folder else shutil.which("npm")
        if node and npm and _node_major(node) >= MIN_NODE:
            env["PATH"] = str(Path(node).parent) + os.pathsep + env.get("PATH", "")
            return npm, env
    install_node(root)
    npm = shutil.which("npm", path=str(own))
    if not npm:
        raise PipelineError(t("node_install_failed"))
    env["PATH"] = str(own) + os.pathsep + env.get("PATH", "")
    return npm, env


# --- tools --------------------------------------------------------------------

def _run_streaming(argv: list[str], env: dict | None = None) -> None:
    proc = subprocess.run(system.resolve(argv), env=env, cwd=Path.home(), stdin=subprocess.DEVNULL, **system.hidden_window())
    if proc.returncode != 0:
        raise PipelineError(t("install_step_failed", code=proc.returncode))


def install_tool(tool: str, root: Path) -> None:
    """Installs one tool. Output goes to stdout (the web interface shows it as the install log)."""
    if tool == "claude":
        argv = CLAUDE_INSTALL["windows" if system.IS_WINDOWS else "posix"]
        if not system.IS_WINDOWS and not shutil.which("curl"):
            raise PipelineError(t("need_curl"))
        _run_streaming(argv)
        return
    if tool not in NPM_PACKAGES:
        raise PipelineError(t("not_found"))
    lock_path = runtime_dir(root) / ".install.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "a+") as lock:
        while not system.try_lock(lock):  # two installs at once must not download Node.js twice
            time.sleep(1)
        npm, env = find_npm(root)
        _run_streaming([npm, "install", "--global", "--prefix", str(tool_prefix(root, tool)), "--no-fund", "--no-audit",
                        NPM_PACKAGES[tool] + "@latest"], env)
