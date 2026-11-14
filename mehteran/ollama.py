"""Ollama: local models on this computer, through Ollama's HTTP API on 127.0.0.1 (standard library urllib).

- Finding it: an Ollama that already runs is used as it is; else the system's ollama program (PATH, the macOS app,
  the Windows install), else the one Mehteran installed into <code folder>/.runtime/ollama.
- Starting it: `ollama serve` bound to 127.0.0.1 is started when Mehteran needs it (a run, a model download); it is
  stopped when Mehteran's process ends, and only when Mehteran started it.
- Installing it: only when the user asks (the Setup tab, `mehter install-local ollama`). The official release
  archive of a pinned version is downloaded from GitHub and checked against the SHA-256 sum written below (from the
  release's sha256sum.txt, which matches GitHub's own asset digests); no install script is run.
- Models stay where Ollama keeps them (~/.ollama/models, or OLLAMA_MODELS), shared with any other Ollama use.
- The address is always this computer: MEHTERAN_OLLAMA_URL may change the port (the tests use it), never the host.
"""

from __future__ import annotations

import atexit
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from . import paths, winjob
from .i18n import t
from .localtools import ToolError, dir_size, disk_free, download_verified, memory

VERSION = "0.40.16"
RELEASE = f"https://github.com/ollama/ollama/releases/download/v{VERSION}"
# (system, machine) -> (asset, SHA-256) of release v0.40.16, from its sha256sum.txt (checked against GitHub's digests).
ASSETS = {
    ("darwin", "arm64"): ("ollama-darwin.tgz", "a743717494315da7cd352982b805f6b992d4b4452ca117fd5fbf86c4ee46fca0"),
    ("darwin", "x64"): ("ollama-darwin.tgz", "a743717494315da7cd352982b805f6b992d4b4452ca117fd5fbf86c4ee46fca0"),
    ("linux", "x64"): ("ollama-linux-amd64.tar.zst", "87bfafb2acbc89b2e6a1be0a9043de6aa75fb450696f86bc426e65fc448f788d"),
    ("linux", "arm64"): ("ollama-linux-arm64.tar.zst", "e45b8e6dcb86cb9f3057396351655079c9a4879b4ced2678c9350d375dcbc224"),
    ("windows", "x64"): ("ollama-windows-amd64.zip", "50fcf5ad54277f2fa5d173ebfc93bcb017adbc0c9ef2314daabc96ca9e6aa64e"),
    ("windows", "arm64"): ("ollama-windows-arm64.zip", "86d2b329cae3125684ff29b506623710b68e1393f679594f1c6aa267beac31c2"),
}
DEFAULT_URL = "http://127.0.0.1:11434"
# A model name as Ollama writes it: "qwen2.5:7b", "library/gemma3:4b", "user/model:tag".
MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}(/[A-Za-z0-9][A-Za-z0-9._-]{0,63})?(:[A-Za-z0-9][A-Za-z0-9._-]{0,63})?\Z")
# Ollama's own default context is small and cuts a long document silently. The context (num_ctx) of a call is sized
# from the prompt: at least MIN_CTX, at most the model's maximum and what the computer's memory can hold.
MIN_CTX = 8192
CHARS_PER_TOKEN = 3  # a safe (low) estimate, so that the context is rather too large than too small

GB = 1_000_000_000
# Checked in the Ollama registry (the tags exist; size = the model's layers). ram: memory needed to run it, roughly.
RECOMMENDED = [
    {"name": "qwen2.5:0.5b", "size": int(0.40 * GB), "ram": 1 * GB, "languages": ["en", "tr"],
     "notes": {"tr": "Çok küçük; yalnızca denemek için. Türkçesi zayıf.", "en": "Very small; for a quick test only. Weak Turkish."}},
    {"name": "bge-m3:567m", "size": int(1.16 * GB), "ram": 2 * GB, "languages": ["en", "tr"], "kind": "embedding",
     "notes": {"tr": "Gömme (embedding) modeli: metni arama için sayılara çevirir, çok dilli. Sohbet etmez; bir adımda model olarak "
                     "kullanılamaz, ileride belge arama için.",
               "en": "Embedding model: turns text into numbers for search, multilingual. It does not chat; it cannot be a "
                     "step's model, for document search later."}},
    {"name": "llama3.2:3b", "size": int(2.02 * GB), "ram": 4 * GB, "languages": ["en"],
     "notes": {"tr": "Küçük ve hızlı; İngilizce için.", "en": "Small and fast; for English."}},
    {"name": "qwen3:4b", "size": int(2.50 * GB), "ram": 5 * GB, "languages": ["en", "tr"],
     "notes": {"tr": "Küçük, çok dilli, düşünerek cevap verir.", "en": "Small, multilingual, reasons before it answers."}},
    {"name": "gemma3:4b", "size": int(3.35 * GB), "ram": 6 * GB, "languages": ["en", "tr"],
     "notes": {"tr": "Küçük; 140'tan çok dili destekler, Türkçesi iyi.", "en": "Small; supports over 140 languages, good Turkish."}},
    {"name": "qwen2.5:7b", "size": int(4.68 * GB), "ram": 8 * GB, "languages": ["en", "tr"],
     "notes": {"tr": "Orta boy, çok dilli; özet ve sınıflandırma için.", "en": "Medium, multilingual; for summaries and classification."}},
    {"name": "aya-expanse:8b", "size": int(5.06 * GB), "ram": 8 * GB, "languages": ["en", "tr"],
     "notes": {"tr": "Çok dilli olarak eğitildi (Türkçe dahil 23 dil); çeviri ve yazı için.",
               "en": "Trained for 23 languages including Turkish; for translation and writing."}},
    {"name": "qwen3:8b", "size": int(5.23 * GB), "ram": 9 * GB, "languages": ["en", "tr"],
     "notes": {"tr": "Orta boy, çok dilli, düşünerek cevap verir.", "en": "Medium, multilingual, reasons before it answers."}},
    {"name": "qwen2.5vl:7b", "size": int(5.97 * GB), "ram": 10 * GB, "languages": ["en", "tr"], "kind": "vision",
     "notes": {"tr": "Resim de okur (belge fotoğrafı, tablo, grafik). Mehteran'ın adımları henüz modele resim göndermez; şimdilik "
                     "metin modeli olarak çalışır.",
               "en": "Also reads images (document photos, tables, charts). Mehteran's steps do not send images to a model yet; "
                     "for now it works as a text model."}},
    {"name": "gemma3:12b", "size": int(8.16 * GB), "ram": 12 * GB, "languages": ["en", "tr"],
     "notes": {"tr": "Daha büyük ve daha iyi; Türkçe yazısı akıcı.", "en": "Larger and better; fluent Turkish."}},
    {"name": "qwen3:14b", "size": int(9.28 * GB), "ram": 14 * GB, "languages": ["en", "tr"],
     "notes": {"tr": "Büyük; uzun ve zor incelemeler için.", "en": "Large; for long and difficult reviews."}},
    {"name": "gpt-oss:20b", "size": int(13.79 * GB), "ram": 16 * GB, "languages": ["en", "tr"],
     "notes": {"tr": "Büyük, akıl yürütmesi güçlü; en az 16 GB bellek.", "en": "Large, strong reasoning; 16 GB of memory at least."}},
]


class OllamaError(ToolError):
    pass


# --- where -----------------------------------------------------------------------

def base_url() -> str:
    """http://127.0.0.1:<port>; MEHTERAN_OLLAMA_URL may change the port, never the host."""
    url = os.environ.get("MEHTERAN_OLLAMA_URL", "").rstrip("/")
    parsed = urlparse(url)
    if parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost") and parsed.port and not parsed.path:
        return f"http://127.0.0.1:{parsed.port}"
    return DEFAULT_URL


def install_dir() -> Path:
    return paths.runtime() / "ollama"


def models_dir() -> Path:
    return Path(os.environ["OLLAMA_MODELS"]) if os.environ.get("OLLAMA_MODELS") else Path.home() / ".ollama" / "models"


def _own_binary() -> Path | None:
    folder = install_dir()
    name = "ollama.exe" if sys.platform == "win32" else "ollama"
    for candidate in (folder / name, folder / "bin" / name):
        if candidate.is_file():
            return candidate
    return None


def binary() -> tuple[Path | None, str | None]:
    """(the ollama program, "system" or "mehteran"); the system's one first."""
    found = shutil.which("ollama")
    candidates = [Path(found)] if found else []
    if sys.platform == "darwin":
        candidates.append(Path("/Applications/Ollama.app/Contents/Resources/ollama"))
    if sys.platform == "win32" and os.environ.get("LOCALAPPDATA"):
        candidates.append(Path(os.environ["LOCALAPPDATA"]) / "Programs" / "Ollama" / "ollama.exe")
    own = _own_binary()
    for candidate in candidates:
        if candidate.is_file() and (own is None or candidate.resolve() != own.resolve()):
            return candidate, "system"
    return (own, "mehteran") if own else (None, None)


# --- the HTTP API --------------------------------------------------------------------

def _open(path: str, body: dict | None = None, method: str | None = None, timeout: float = 5):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(base_url() + path, data=data, method=method or ("POST" if data else "GET"),
                                     headers={"Content-Type": "application/json"})
    return urllib.request.urlopen(request, timeout=timeout)  # noqa: S310 - always http://127.0.0.1


def _error_text(e: urllib.error.HTTPError) -> str:
    try:
        return str(json.loads(e.read()).get("error") or e)
    except (ValueError, OSError, AttributeError):
        return str(e)
    finally:
        e.close()


def version() -> str | None:
    """The version of the running Ollama, or None when none answers."""
    try:
        with _open("/api/version", timeout=1.5) as res:
            return str(json.loads(res.read()).get("version") or "")
    except (OSError, ValueError):
        return None


def running() -> bool:
    return version() is not None


def installed_models() -> list[dict]:
    """[{name, size, modified}] of the running Ollama; empty when it does not run."""
    try:
        with _open("/api/tags", timeout=3) as res:
            models = json.loads(res.read()).get("models") or []
    except (OSError, ValueError):
        return []
    return [{"name": m.get("name") or m.get("model"), "size": m.get("size"), "modified": m.get("modified_at")}
            for m in models if isinstance(m, dict) and (m.get("name") or m.get("model"))]


# --- starting and stopping ---------------------------------------------------------------

_server: subprocess.Popen | None = None
_server_job: int | None = None  # Windows job handle of _server (see winjob)
_server_lock = threading.Lock()


def ensure_running(timeout: float = 30) -> None:
    """Starts `ollama serve` on 127.0.0.1 when no Ollama answers. Raises OllamaError when there is none."""
    global _server, _server_job
    if running():
        return
    with _server_lock:
        if running():
            return
        program, _ = binary()
        if program is None:
            raise OllamaError(t("ollama_missing"))
        if _server is None or _server.poll() is not None:
            from pipeline import system
            log = paths.home() / "jobs" / "ollama-serve.log"
            log.parent.mkdir(parents=True, exist_ok=True)
            env = {**os.environ, "OLLAMA_HOST": base_url().removeprefix("http://")}
            with open(log, "ab") as out:
                _server = subprocess.Popen([str(program), "serve"], env=env, stdin=subprocess.DEVNULL, stdout=out,
                                           stderr=subprocess.STDOUT, **system.new_process_group())
                _server_job = winjob.attach(_server.pid)  # Windows: ends with Mehteran even when atexit does not run
        end = time.time() + timeout
        while time.time() < end:
            if running():
                return
            if _server.poll() is not None:
                break
            time.sleep(0.2)
    raise OllamaError(t("ollama_not_started"))


def started_here() -> bool:
    return _server is not None and _server.poll() is None


@atexit.register
def stop_started() -> None:
    """Stops the Ollama server that this process started (never one that was already running)."""
    global _server, _server_job
    if started_here():
        from pipeline import system
        system.stop_tree(_server.pid)
        try:
            _server.wait(10)
        except subprocess.TimeoutExpired:
            _server.kill()
    winjob.close(_server_job)
    _server, _server_job = None, None


# --- answers ----------------------------------------------------------------------------

def model_context(model: str) -> int | None:
    """The largest context (tokens) that the model supports, from /api/show; None when Ollama does not tell."""
    try:
        with _open("/api/show", {"model": model, "name": model}, timeout=10) as res:
            info = json.loads(res.read()).get("model_info") or {}
    except (OSError, ValueError, AttributeError):
        return None
    values = [v for k, v in info.items() if k.endswith(".context_length") and isinstance(v, int) and v > 0]
    return values[0] if values else None


def memory_context() -> int:
    """The context that the computer's memory can hold safely: 1024 tokens per GB of memory, from 4096 to 131072
    (the key-value cache of a 7B model needs about 0.5 MB per token)."""
    ram = memory()
    return 8192 if ram is None else max(4096, min(131072, int(ram / GB) * 1024))


def context_size(prompt: str, system_prompt: str, model: str) -> int:
    """num_ctx for this call: the prompt and room for the reply, at least MIN_CTX, at most the model's maximum and
    the memory-safe context. Rounded up to 1024."""
    needed = (len(prompt) + len(system_prompt)) // CHARS_PER_TOKEN + 1
    wanted = needed + max(2048, needed // 2)  # a reply may be as long as a rewritten document
    size = -(-max(wanted, MIN_CTX) // 1024) * 1024
    return min(size, model_context(model) or size, memory_context())


def chat(model: str, prompt: str, system_prompt: str, timeout: float, options: dict | None = None,
         on_text=None) -> str:
    """One answer of model to prompt (streamed, so that a long answer does not hit a read timeout). on_text gets each
    piece of the answer as it arrives (the live log)."""
    if not MODEL_RE.match(model or ""):
        raise OllamaError(t("ollama_bad_model", name=model))
    options = {"num_ctx": context_size(prompt, system_prompt, model), **(options or {})}  # a set num_ctx wins
    body = {"model": model, "stream": True, "options": options,
            "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}]}
    end = time.time() + timeout
    parts: list[str] = []
    try:
        with _open("/api/chat", body, timeout=min(timeout, 300)) as res:
            for line in res:
                if time.time() > end:
                    raise OllamaError(t("ollama_timeout", seconds=int(timeout)))
                if not line.strip():
                    continue
                event = json.loads(line)
                if event.get("error"):
                    raise OllamaError(t("ollama_failed", error=event["error"]))
                piece = (event.get("message") or {}).get("content") or ""
                parts.append(piece)
                if on_text and piece:
                    on_text(piece)
                if event.get("done"):
                    # The prompt filled the whole context: Ollama cut its beginning (a document, the instruction).
                    if (event.get("prompt_eval_count") or 0) >= options["num_ctx"]:
                        raise OllamaError(t("ollama_too_long", tokens=options["num_ctx"]))
                    break
    except urllib.error.HTTPError as e:
        message = _error_text(e)
        raise OllamaError(t("ollama_no_model", name=model) if e.code == 404 else t("ollama_failed", error=message)) from None
    except (OSError, ValueError) as e:
        raise OllamaError(t("ollama_failed", error=e)) from None
    answer = re.sub(r"<think>.*?</think>", "", "".join(parts), flags=re.S).strip()  # a reasoning model's notes
    if not answer:
        raise OllamaError(t("ollama_empty", name=model))
    return answer


# --- downloading and deleting models ------------------------------------------------------------

def pull_warnings(name: str) -> tuple[list[str], bool]:
    """Warnings before a model is downloaded, and whether the download must not start (the disk is too full)."""
    known = next((m for m in RECOMMENDED if m["name"] == name), None)
    warnings, blocked = [], False
    if known is None:
        warnings.append(t("ollama_size_unknown"))
        return warnings, blocked
    free = disk_free(models_dir())
    if free is not None and free < known["size"] * 1.1 + GB:
        warnings.append(t("ollama_disk_low", need=_gb(known["size"]), free=_gb(free)))
        blocked = True
    ram = memory()
    if ram is not None and ram < known["ram"]:
        warnings.append(t("ollama_ram_low", need=_gb(known["ram"]), ram=_gb(ram)))
    return warnings, blocked


def _gb(n: int) -> str:
    return f"{n / GB:.1f}"


class Pull:
    """One model download at a time, in a thread of this process, with its progress."""

    def __init__(self):
        self.lock = threading.Lock()
        self.state: dict = {}
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self, name: str) -> None:
        with self.lock:
            if self.thread and self.thread.is_alive():
                raise OllamaError(t("ollama_pull_running", name=self.state.get("name")))
            self.stop = threading.Event()
            self.state = {"name": name, "status": "starting", "completed": 0, "total": 0, "percent": 0,
                          "done": False, "error": None, "cancelled": False, "started": time.time()}
            self.thread = threading.Thread(target=self._run, args=(name, self.stop), daemon=True)
            self.thread.start()

    def _run(self, name: str, stop: threading.Event) -> None:
        state = self.state
        layers: dict[str, tuple[int, int]] = {}
        try:
            ensure_running()
            with _open("/api/pull", {"model": name, "name": name, "stream": True}, timeout=120) as res:
                for line in res:
                    if stop.is_set():
                        state.update(status="cancelled", cancelled=True)
                        return  # closing the connection ends the download in Ollama
                    if not line.strip():
                        continue
                    event = json.loads(line)
                    if event.get("error"):
                        raise OllamaError(t("ollama_failed", error=event["error"]))
                    if event.get("total"):  # one entry per layer: the progress is over all layers seen so far
                        layers[event.get("digest") or event.get("status")] = (event.get("completed") or 0, event["total"])
                    total, completed = sum(t for _, t in layers.values()), sum(c for c, _ in layers.values())
                    state.update(status=str(event.get("status") or ""), total=total, completed=completed,
                                 percent=int(completed * 100 / total) if total else state["percent"])
                    if event.get("status") == "success":
                        state.update(percent=100)
                        break
        except urllib.error.HTTPError as e:
            state["error"] = t("ollama_failed", error=_error_text(e))
        except (OSError, ValueError, ToolError) as e:
            state["error"] = str(e)
        finally:
            state["done"] = True

    def cancel(self) -> bool:
        if self.thread and self.thread.is_alive():
            self.stop.set()
            return True
        return False

    def info(self) -> dict:
        return dict(self.state)


def delete(name: str) -> None:
    if not MODEL_RE.match(name or ""):
        raise OllamaError(t("ollama_bad_model", name=name))
    try:
        with _open("/api/delete", {"model": name, "name": name}, method="DELETE", timeout=30):
            pass
    except urllib.error.HTTPError as e:
        raise OllamaError(t("ollama_failed", error=_error_text(e))) from None
    except OSError as e:
        raise OllamaError(t("ollama_failed", error=e)) from None


# --- installing Ollama ----------------------------------------------------------------------

def asset() -> tuple[str, str]:
    machine = platform.machine().lower()
    arch = "arm64" if machine in ("arm64", "aarch64") else "x64" if machine in ("x86_64", "amd64") else machine
    system_name = {"darwin": "darwin", "win32": "windows"}.get(sys.platform, "linux")
    if (system_name, arch) not in ASSETS:
        raise OllamaError(t("ollama_unsupported", machine=f"{system_name}-{arch}"))
    return ASSETS[(system_name, arch)]


def _untar_zst(archive: Path, dest: Path) -> None:
    """A .tar.zst archive: Python 3.14 reads it itself; earlier versions need the zstd program."""
    from pipeline import runtime
    try:
        import compression.zstd  # noqa: F401  (Python 3.14 and later)
        with tarfile.open(archive, "r:zst") as tar:
            tar.extractall(dest, filter="data")
        return
    except ImportError:
        pass
    zstd = shutil.which("zstd")
    if not zstd:
        raise OllamaError(t("ollama_need_zstd"))
    plain = archive.with_suffix("")  # .tar
    subprocess.run([zstd, "-d", "-q", "-f", "-o", str(plain), str(archive)], check=True)
    runtime._safe_extract(plain, "tar", dest)


def install() -> Path:
    """Downloads Ollama VERSION into <code folder>/.runtime/ollama and checks it. Output goes to stdout (the job log)."""
    from pipeline import runtime
    name, sha256 = asset()
    print(t("ollama_downloading", version=VERSION, name=name), flush=True)
    base = paths.runtime()
    base.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=base) as tmp:
        archive = Path(tmp) / name
        download_verified(f"{RELEASE}/{name}", archive, sha256)
        print(t("download_verified", name=name), flush=True)
        unpacked = Path(tmp) / "unpacked"
        unpacked.mkdir()
        if name.endswith(".tar.zst"):
            _untar_zst(archive, unpacked)
        else:
            runtime._safe_extract(archive, "zip" if name.endswith(".zip") else "tar", unpacked)
        target = install_dir()
        if target.exists():
            shutil.rmtree(target)
        os.replace(unpacked, target)
    program = _own_binary()
    if program is None:
        raise OllamaError(t("ollama_install_failed"))
    program.chmod(0o755)
    print(t("ollama_installed", version=VERSION, path=program), flush=True)
    return program


def _program_version(program: Path) -> str | None:
    try:
        from pipeline import system
        out = subprocess.run([str(program), "--version"], capture_output=True, text=True, timeout=10,
                             encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL, **system.hidden_window())
    except (OSError, subprocess.SubprocessError):
        return None
    m = re.search(r"(\d+\.\d+\.\d+)", out.stdout + out.stderr)
    return m.group(1) if m else None


def status() -> dict:
    """What the Setup tab shows about Ollama."""
    program, source = binary()
    serving = version()
    own = install_dir()
    return {"id": "ollama", "name": "Ollama", "installed": program is not None or serving is not None,
            "source": source, "path": str(program) if program else None,
            "version": serving or (_program_version(program) if program else None), "running": serving is not None,
            "started_by_mehteran": started_here(), "url": base_url(), "pinned_version": VERSION,
            "size": dir_size(own), "install_dir": str(own), "models_dir": str(models_dir()),
            "disk_free": disk_free(models_dir()), "memory": memory()}
