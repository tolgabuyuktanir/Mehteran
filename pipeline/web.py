"""Local web interface. Reachable only from this computer (127.0.0.1); runs the work in the background as CLI processes."""

from __future__ import annotations

import hmac
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
import zipfile
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

from . import configfile, export, i18n, stages, system, tools
from .core import PipelineError, Project, read_json, say, split_name, write_json, write_text
from .documents import SUPPORTED
from .i18n import t
from .providers import QuotaError, run as run_llm

CODE_DIR = Path(__file__).resolve().parent
STATIC = CODE_DIR / "ui"
STATIC_TYPES = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css"}
UPLOAD_LIMIT = 300 * 1024 * 1024
JSON_LIMIT = 2 * 1024 * 1024
BOOK_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$")
LANG_RE = re.compile(r"^[a-z]{2,3}(-[a-z0-9]{2,8})?$")
PROMPTS = ["rules", "translate", "review", "revise", "source_check", "custom_report", "custom_rewrite", "gate",
           "glossary", "align"]  # display order
TR_ASCII = str.maketrans("çğıİöşüâîûÇĞÖŞÜÂÎÛ", "cgiiosuaiucgosuaiu")


class HTTPError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code


# --- background jobs --------------------------------------------------------

class Jobs:
    """Install jobs and book runs started by this server. Book runs are also tracked through the book's lock
    file, so a run is still visible after the server restarts."""

    def __init__(self):
        self.lock = threading.Lock()
        self.items: dict[str, dict] = {}

    def start(self, key: str, argv: list[str], log: Path, env: dict | None = None, cwd: Path | None = None) -> None:
        with self.lock:
            job = self.items.get(key)
            if job and job["proc"].poll() is None:
                raise HTTPError(409, t("job_running"))
            log.parent.mkdir(parents=True, exist_ok=True)
            handle = open(log, "w", encoding="utf-8")
            handle.write(f"$ {' '.join(argv)}\n\n")
            handle.flush()
            proc = subprocess.Popen(system.resolve(argv), stdout=handle, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, cwd=cwd, env=env, **system.new_process_group())
            job = self.items[key] = {"proc": proc, "log": log, "closed": False}
        done, failed = t("job_done"), t("job_failed")  # in the language of the request that started the job

        def wait():
            code = proc.wait()
            handle.write(f"\n[{done if code == 0 else failed.format(code=code)}]\n")
            handle.close()
            job["closed"] = True  # only now is the log complete

        threading.Thread(target=wait, daemon=True).start()

    def info(self, key: str) -> dict | None:
        job = self.items.get(key)
        if not job:
            return None
        code = job["proc"].poll()
        return {"running": not job["closed"], "code": code, "log": _tail(job["log"])}


def _tail(path: Path, size: int = 20000) -> str:
    if not path.exists():
        return ""
    with open(path, "rb") as f:
        f.seek(max(0, path.stat().st_size - size))
        return f.read().decode("utf-8", "replace")


def _book_pid(book_dir: Path) -> int | None:
    """The id of the process that runs the book, if it is running now (-1 when it runs but the id is unknown)."""
    if not system.is_locked(book_dir / "work" / ".lock"):
        return None
    pid_file = book_dir / "work" / "run.pid"
    text = pid_file.read_text(encoding="utf-8").strip() if pid_file.exists() else ""
    return int(text) if text.isdigit() else -1


def _forget_reference(book_dir: Path, lang: str) -> None:
    """A new or deleted reference file makes its prepared text and alignment invalid."""
    meta_path = book_dir / "work" / "prep.json"
    meta = read_json(meta_path, {})
    if lang in meta.get("references", {}):
        del meta["references"][lang]
        write_json(meta_path, meta)
    (book_dir / "work" / "references" / f"{lang}.md").unlink(missing_ok=True)
    (book_dir / "work" / "alignment" / f"{lang}.json").unlink(missing_ok=True)


# --- application ------------------------------------------------------------

class App:
    def __init__(self, proj: Project):
        self.proj = proj
        self.root = proj.root
        self.jobs = Jobs()
        self.model_lists: dict[str, tuple[float, list[str]]] = {}
        self.token = secrets.token_urlsafe(32)
        self.run_lock = threading.Lock()

    # helpers
    def reload(self) -> Project:
        self.proj = Project.load(self.root)
        return self.proj

    def book_dir(self, book: str) -> Path:
        if not BOOK_RE.match(book):
            raise HTTPError(404, t("book_missing"))
        path = self.proj.book_dir(book)
        if not path.is_dir():
            raise HTTPError(404, t("book_missing"))
        return path

    def lang(self, code: str) -> str:
        if not LANG_RE.match(code or "") or code not in self.proj.cfg.get("languages", {}):
            raise HTTPError(400, t("unknown_language", code=code))
        return code

    def ensure_idle(self, book_dir: Path) -> None:
        if _book_pid(book_dir):
            raise HTTPError(409, t("book_running"))

    # tools
    def tools(self) -> dict:
        proj = self.reload()
        tools.extend_path(self.root)  # a tool installed a moment ago may have created a new folder on PATH
        used: dict[str, list[str]] = {}
        for stage in stages.llm_stages(proj):
            for name in proj.providers_for(stage):
                used.setdefault(split_name(name)[0], []).append(stage)
        lang = i18n.current()

        def status(tool):
            i18n.set_request(lang)  # pool threads do not inherit the request language
            return tools.status(tool)

        with ThreadPoolExecutor(max_workers=3) as pool:
            items = list(pool.map(status, tools.TOOLS))
        quota = read_json(self.root / ".jobs" / "quota.json", {})
        for item in items:
            item["stages"] = used.get(item["provider"], [])
            item["job"] = self.jobs.info(f"install:{item['id']}")
            item["requirements"] = t(f"requirements_{item['id']}")
            item["sign_in_help"] = t(f"sign_in_help_{item['id']}")
            item["quota"] = quota.get(item["provider"])
        books = [p for p in (self.root / "books").glob("*") if p.is_dir()]
        return {"tools": items, "terminal": system.can_open_terminal(), "all_job": self.jobs.info("install:all"),
                "books": len(books)}

    def tool(self, tool: str) -> dict:
        if tool not in tools.TOOLS:
            raise HTTPError(404, t("not_found"))
        return tools.TOOLS[tool]

    def install(self, names: list[str], key: str) -> dict:
        """Installs tools in the background (one after the other). key: the job name shown in the interface."""
        env = os.environ.copy()
        env.update({"TP_ROOT": str(self.root), "TP_LANG": i18n.current(), "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1",
                    "PYTHONPATH": str(CODE_DIR.parent) + os.pathsep + env.get("PYTHONPATH", "")})
        self.jobs.start(f"install:{key}", tools.install_command(names), self.root / ".jobs" / f"install-{key}.log",
                        env=env, cwd=CODE_DIR.parent)
        return {"message": t("install_started")}

    def install_one(self, tool: str) -> dict:
        self.tool(tool)
        return self.install([tool], tool)

    def install_missing(self) -> dict:
        tools.extend_path(self.root)
        missing = [tool for tool, spec in tools.TOOLS.items() if not shutil.which(spec["command"])]
        if not missing:
            return {"message": t("nothing_to_install")}
        return self.install(missing, "all")

    def models(self, tool: str) -> dict:
        """The model list of a tool. Reading it can start the tool, so the answer is kept for ten minutes."""
        self.tool(tool)
        tools.extend_path(self.root)
        known = self.model_lists.get(tool)
        if not known or time.time() - known[0] > 600 or not known[1]:
            known = self.model_lists[tool] = (time.time(), tools.list_models(tool))
        return {"models": known[1]}

    def login(self, tool: str, body: dict) -> dict:
        self.tool(tool)
        return {"message": tools.login(tool, str(body.get("method", "")), str(body.get("key", "")))}

    def test_tool(self, tool: str) -> dict:
        return self.test_model({"name": self.tool(tool)["provider"]})

    def test_model(self, body: dict) -> dict:
        name = str(body.get("name", ""))
        if not configfile.NAME_RE.match(name) or split_name(name)[0] not in self.proj.cfg["providers"]:
            raise HTTPError(400, t("model_invalid", name=name))
        started = time.time()
        try:
            answer = run_llm(self.reload(), name, "Reply with exactly this word and nothing else: OK",
                             wait_for_quota=False, attempts=1, timeout=180)
        except QuotaError as e:
            path = self.root / ".jobs" / "quota.json"
            known = read_json(path, {})
            known[split_name(name)[0]] = {"until": e.until, "since": time.time(), "message": str(e)}
            write_json(path, known)
            raise
        return {"message": t("test_answer", seconds=f"{time.time() - started:.0f}", answer=answer[:60])}

    # languages and settings
    def add_language(self, body: dict) -> dict:
        code = str(body.get("code", "")).strip().lower()
        name = " ".join(str(body.get("name", "")).split())
        if not LANG_RE.match(code):
            raise HTTPError(400, t("language_code_invalid"))
        if not re.fullmatch(r"[A-Za-z][A-Za-z ()\-]{1,60}", name):
            raise HTTPError(400, t("language_name_invalid"))
        if code in self.proj.cfg.get("languages", {}):
            raise HTTPError(409, t("language_exists"))
        path = self.root / "config.toml"
        text = path.read_text(encoding="utf-8")
        sections = re.findall(r"^\[([^\]]+)\]", text, re.M)
        if not sections or sections[-1] != "languages":
            raise HTTPError(500, t("languages_not_last"))
        write_text(path, text.rstrip("\n") + f'\n{code} = "{name}"\n')
        self.reload()
        return {"message": t("language_added", name=name, code=code)}

    def settings(self) -> dict:
        proj = self.reload()
        tool_of = {spec["provider"]: tool for tool, spec in tools.TOOLS.items()}
        return {
            "stages": {stage: proj.providers_for(stage) for stage in stages.llm_stages(proj)},
            "flow": (flow := stages.flow(proj)),
            "nodes": {node: stages.node_options(proj.cfg, node) for node in flow
                      if stages.kind(node) in ("custom", "gate")},
            "instructions": {node: stages.instructions(proj, node) for node in flow if stages.kind(node) == "custom"},
            "default_flow": stages.DEFAULT_FLOW,
            "max_flow_steps": stages.MAX_FLOW_STEPS,
            "max_loops": stages.MAX_LOOPS,
            "max_reporters": stages.MAX_REPORTERS,
            "languages": proj.cfg.get("languages", {}),
            "stage_order": stages.all_stages(proj),
            "providers": {
                name: {"default_model": spec.get("model", ""), "models": list(spec.get("models", [])),
                       "tool": tool_of.get(name)}
                for name, spec in proj.cfg["providers"].items()
            },
            "keep_awake": proj.cfg["general"].get("keep_awake", True) and system.can_keep_awake(),
        }

    def save_stages(self, body: dict) -> dict:
        """Saves the workflow canvas: the nodes in order, their options, which provider/model does each stage,
        the instructions of custom nodes and each provider's model list."""
        proj = self.reload()
        flow = body.get("flow")
        nodes = self._node_options(flow, body.get("nodes"))
        error = stages.flow_error(flow, {"nodes": nodes})
        if error:
            raise HTTPError(400, error)
        cfg = {"nodes": nodes}
        assignment = body.get("stages")
        order = stages.PREP_STAGES + ["translate"] + flow
        if not isinstance(assignment, dict) or set(assignment) != set(order):
            raise HTTPError(400, t("bad_request"))
        for stage, names in assignment.items():
            if not isinstance(names, list) or not names or len(set(names)) != len(names):
                raise HTTPError(400, t("stage_needs_model", stage=stage))
            reporting = stage in flow and stages.role(cfg, stage) == "report"
            if not reporting and len(names) != 1:
                raise HTTPError(400, t("stage_one_model", stage=stage))
            if len(names) > stages.MAX_REPORTERS:
                raise HTTPError(400, t("stage_too_many", stage=stage))
            for name in names:
                if not isinstance(name, str) or not configfile.NAME_RE.match(name) or split_name(name)[0] not in proj.cfg["providers"]:
                    raise HTTPError(400, t("model_invalid", name=name))
        texts = body.get("instructions") or {}
        if not isinstance(texts, dict):
            raise HTTPError(400, t("bad_request"))
        for node in flow:
            if stages.kind(node) == "custom":
                text = str(texts.get(node, "")).replace("\r\n", "\n").strip()
                if len(text) > stages.INSTRUCTIONS_LIMIT:
                    raise HTTPError(400, t("instructions_too_long"))
                write_text(stages.instructions_path(self.root, node), text + "\n")
        path = self.root / "config.toml"
        text = configfile.set_stages(path.read_text(encoding="utf-8"), assignment, flow, nodes)
        for provider, models in (body.get("models") or {}).items():
            if provider in proj.cfg["providers"] and isinstance(models, list):
                clean = [m for m in dict.fromkeys(str(m) for m in models) if configfile.MODEL_RE.match(m)][:30]
                text = configfile.set_models(text, provider, clean)
        write_text(path, text)
        self.reload()
        return {"message": t("stages_saved")}

    @staticmethod
    def _node_options(flow, given) -> dict:
        """The options of the custom nodes and checkpoints of a flow, keeping only known keys of the right type."""
        if not isinstance(flow, list) or not isinstance(given or {}, dict):
            raise HTTPError(400, t("bad_request"))
        out = {}
        for node in flow:
            options = (given or {}).get(node) if isinstance(node, str) else None
            options = options if isinstance(options, dict) else {}
            if stages.kind(str(node)) == "custom":
                out[node] = {"title": str(options.get("title", ""))[:stages.TITLE_LIMIT], "mode": options.get("mode")}
            elif stages.kind(str(node)) == "gate":
                loops = options.get("max")
                out[node] = {"back_to": options.get("back_to"),
                             "max": loops if isinstance(loops, int) and not isinstance(loops, bool) else None}
        return out

    # books
    def books(self) -> list[dict]:
        proj = self.reload()
        out = []
        for book_dir in sorted(p for p in (self.root / "books").glob("*") if p.is_dir() and BOOK_RE.match(p.name)):
            sources = [f.name for f in sorted((book_dir / "source").glob("*")) if f.suffix.lower() in SUPPORTED]
            refs = [{"lang": f.stem, "file": f.name} for f in sorted((book_dir / "references").glob("*"))
                    if f.suffix.lower() in SUPPORTED]
            meta = read_json(book_dir / "work" / "prep.json", {})
            outputs = sorted(f.stem for f in (book_dir / "output").glob("*.md") if not f.stem.endswith(".report"))
            running = bool(_book_pid(book_dir))
            out.append({
                "name": book_dir.name, "source": sources, "references": refs, "prepared": "source" in meta,
                "status": stages.book_status(proj, book_dir.name), "running": running,
                "outputs": outputs, "run": self.run_info(proj, book_dir, running),
            })
        return out

    def run_info(self, proj: Project, book_dir: Path, running: bool) -> dict | None:
        """The live status of the last run, with the remaining calls and the estimated remaining time."""
        info = read_json(book_dir / "work" / "run.json")
        if not info:
            return None
        if not running and info.get("state") in ("running", "waiting_quota"):
            info["state"] = "interrupted"  # the process ended without recording why (stopped, crashed, computer off)
            info["quota"] = {}
        info["now"] = time.time()
        if running:
            try:
                info["remaining"] = stages.estimate(proj, book_dir.name, info["target"], info.get("refs", []),
                                                    info.get("segments", ""), info.get("durations"))
            except (PipelineError, OSError, KeyError, ValueError):
                info["remaining"] = None
        return info

    def estimate(self, book: str, body: dict) -> dict:
        book_dir = self.book_dir(book)
        target = self.lang(str(body.get("lang", "")))
        refs = [self.lang(str(r)) for r in body.get("references") or []]
        segments = str(body.get("segments") or "").replace(" ", "")
        if segments and not re.fullmatch(r"\d+(-\d+)?(,\d+(-\d+)?)*", segments):
            raise HTTPError(400, t("segments_format"))
        proj = self.reload()
        plan = stages.estimate(proj, book_dir.name, target, refs, segments)
        plan["stale"] = stages.stale_for(proj, book_dir.name, target, refs, segments)
        return plan

    def create_book(self, body: dict) -> dict:
        name = str(body.get("name", "")).strip().translate(TR_ASCII).lower()
        name = re.sub(r"[^a-z0-9_-]+", "-", name).strip("-")[:64]
        if not BOOK_RE.match(name):
            raise HTTPError(400, t("book_name_invalid"))
        book_dir = self.proj.book_dir(name)
        if book_dir.exists():
            raise HTTPError(409, t("book_exists", name=name))
        for sub in ("source", "references"):
            (book_dir / sub).mkdir(parents=True)
        return {"name": name, "message": t("book_added", name=name)}

    def upload(self, book: str, kind: str, lang: str | None, filename: str, length: int, stream) -> dict:
        try:
            book_dir = self.book_dir(book)
            self.ensure_idle(book_dir)
            ext = Path(filename).suffix.lower()
            if ext not in SUPPORTED:
                raise HTTPError(400, t("upload_type", supported=", ".join(SUPPORTED)))
            if not 0 < length <= UPLOAD_LIMIT:
                raise HTTPError(413, t("upload_size", limit=UPLOAD_LIMIT // 1024 // 1024))
            if ext == ".pdf" and not shutil.which("pdftotext"):
                raise HTTPError(400, t("pdf_tool_missing_windows" if system.IS_WINDOWS else "pdf_tool_missing"))
            if kind == "source":
                if "source" in read_json(book_dir / "work" / "prep.json", {}):
                    raise HTTPError(409, t("source_locked"))
                folder, stem = book_dir / "source", "tr"
            else:
                lang = self.lang(lang or "")
                folder, stem = book_dir / "references", lang
        except HTTPError:
            # Read the body before answering; otherwise the browser sees a broken connection instead of the reason.
            if 0 < length <= UPLOAD_LIMIT:
                while length > 0 and (chunk := stream.read(min(1024 * 1024, length))):
                    length -= len(chunk)
            raise

        tmp = folder / f".uploading{ext}"
        received = 0
        with open(tmp, "wb") as f:
            while received < length:
                chunk = stream.read(min(1024 * 1024, length - received))
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)
        try:
            if received != length:
                raise HTTPError(400, t("upload_incomplete"))
            _check_file(tmp, ext)
            for old in folder.glob("*" if kind == "source" else f"{stem}.*"):
                if old.suffix.lower() in SUPPORTED and old != tmp:
                    old.unlink()
            os.replace(tmp, folder / f"{stem}{ext}")
        finally:
            tmp.unlink(missing_ok=True)
        if kind == "references":
            _forget_reference(book_dir, lang)
        return {"message": t("uploaded", name=filename)}

    def delete_reference(self, book: str, lang: str) -> dict:
        book_dir = self.book_dir(book)
        self.ensure_idle(book_dir)
        lang = self.lang(lang)
        for f in (book_dir / "references").glob(f"{lang}.*"):
            if f.suffix.lower() in SUPPORTED:
                f.unlink()
        _forget_reference(book_dir, lang)
        return {"message": t("reference_deleted")}

    def reset_book(self, book: str) -> dict:
        book_dir = self.book_dir(book)
        self.ensure_idle(book_dir)
        shutil.rmtree(book_dir / "work", ignore_errors=True)
        return {"message": t("book_reset")}

    def preview(self, book: str) -> dict:
        """The source as the pipeline reads it, split into segments. Prepares the source first if needed (no model calls)."""
        book_dir = self.book_dir(book)
        work = book_dir / "work"
        if "source" not in read_json(work / "prep.json", {}):
            self.ensure_idle(book_dir)
            stages.prepare(self.reload(), book_dir.name, [])
        files = sorted((work / "segments").glob("*.md"))
        parts = [f"──────── {t('report_segment', id=int(f.stem))} ────────\n\n{f.read_text(encoding='utf-8').strip()}" for f in files]
        return {"segments": len(files), "text": "\n\n".join(parts)}

    def run_book(self, book: str, body: dict) -> dict:
        book_dir = self.book_dir(book)
        target = self.lang(str(body.get("lang", "")))
        if target == "tr":
            raise HTTPError(400, t("target_not_turkish"))
        refs = [self.lang(str(r)) for r in body.get("references") or []]
        argv = [sys.executable, "-m", "pipeline", "run", book, target, "--refs", ",".join(refs) or ","]
        segments = str(body.get("segments") or "").replace(" ", "")
        if segments:
            if not re.fullmatch(r"\d+(-\d+)?(,\d+(-\d+)?)*", segments):
                raise HTTPError(400, t("segments_format"))
            argv += ["--segments", segments]
        if body.get("until"):
            if body["until"] not in stages.all_stages(self.reload()):
                raise HTTPError(400, t("stage_invalid"))
            argv += ["--until", body["until"]]
        if body.get("redo"):
            if body["redo"] not in stages.llm_stages(self.reload()):
                raise HTTPError(400, t("stage_invalid"))
            argv += ["--redo", body["redo"]]

        with self.run_lock:
            self.ensure_idle(book_dir)
            env = os.environ.copy()
            # PYTHONUTF8: on Windows a redirected stdout would otherwise use the local code page and fail on "ı".
            env.update({"TP_ROOT": str(self.root), "TP_LANG": i18n.current(), "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1",
                        "PYTHONPATH": str(CODE_DIR.parent) + os.pathsep + env.get("PYTHONPATH", "")})
            log = book_dir / "logs" / f"{time.strftime('%Y%m%d-%H%M%S')}-{target}.log"
            self.jobs.start(f"book:{book}", argv, log, env=env, cwd=CODE_DIR.parent)
            # Wait briefly until the run holds the lock, so that the interface shows it as running at once.
            for _ in range(50):
                if _book_pid(book_dir) or self.jobs.info(f"book:{book}")["code"] is not None:
                    break
                time.sleep(0.1)
            job = self.jobs.info(f"book:{book}")
            if job["code"] not in (None, 0):
                # The run ended at once (for example a missing tool): show the reason instead of "started".
                for _ in range(20):
                    if not self.jobs.info(f"book:{book}")["running"]:
                        break
                    time.sleep(0.05)
                lines = [line for line in self.jobs.info(f"book:{book}")["log"].splitlines() if line.strip()]
                reason = next((line for line in reversed(lines) if line.startswith(t("error"))), lines[-2] if len(lines) > 1 else "")
                raise HTTPError(400, t("run_failed_at_start", reason=reason))
        return {"message": t("run_started")}

    def stop_book(self, book: str) -> dict:
        book_dir = self.book_dir(book)
        pid = _book_pid(book_dir)
        if not pid or pid < 0:
            raise HTTPError(409, t("nothing_running"))
        system.stop_tree(pid)  # the pipeline and the claude/codex/gemini processes it started
        if system.IS_WINDOWS:
            for _ in range(50):  # wait until the process is gone, so that its last status write cannot win
                if not _book_pid(book_dir):
                    break
                time.sleep(0.1)
            # Windows ends the process at once, so the pipeline cannot record the stop itself.
            status_path = book_dir / "work" / "run.json"
            info = read_json(status_path, {})
            if info:
                info.update(state="stopped", finished=time.time(), quota={})
                write_json(status_path, info)
        return {"message": t("run_stopped")}

    def log(self, book: str) -> dict:
        book_dir = self.book_dir(book)
        logs = sorted((book_dir / "logs").glob("*.log"))
        job = self.jobs.info(f"book:{book}")
        return {"log": _tail(logs[-1]) if logs else "", "file": logs[-1].name if logs else "",
                "running": bool(_book_pid(book_dir)) or bool(job and job["running"])}

    def export(self, book: str, lang: str, kind: str, fmt: str) -> tuple[bytes, str, str]:
        """Returns (content, content type, download file name) of an output in the requested format."""
        path = self.output_path(book, lang, kind)
        text = path.read_text(encoding="utf-8")
        title = f"{book} · {self.proj.language_name(lang)}" + (f" · {t('report_word')}" if kind == "report" else "")
        # The report is written in the interface language; the translation in the target language.
        doc_lang = i18n.current() if kind == "report" else lang
        name = f"{book}-{lang}" + ("-report" if kind == "report" else "")
        if fmt == "md":
            return text.encode("utf-8"), "text/markdown", f"{name}.md"
        if fmt == "docx":
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            return export.to_docx(text, title, doc_lang, lists=kind == "report"), mime, f"{name}.docx"
        if fmt == "pdf":
            # A real PDF from the browser installed on the computer (Chrome or Edge, without its window). Without
            # one, the page opens with the print dialog, where "Save as PDF" makes the file.
            page = export.to_html(text, title, doc_lang, lists=kind == "report")
            with tempfile.TemporaryDirectory() as tmp:
                source, pdf = Path(tmp) / f"{name}.html", Path(tmp) / f"{name}.pdf"
                source.write_text(page, encoding="utf-8")
                if system.print_pdf(source, pdf):
                    return pdf.read_bytes(), "application/pdf", f"{name}.pdf"
            page = export.to_html(text, title, doc_lang, print_on_load=True, lists=kind == "report")
            return page.encode("utf-8"), "text/html", f"{name}.html"
        if fmt == "html":
            page = export.to_html(text, title, doc_lang, lists=kind == "report")
            return page.encode("utf-8"), "text/html", f"{name}.html"
        raise HTTPError(404, t("not_found"))

    def output_path(self, book: str, lang: str, kind: str) -> Path:
        book_dir = self.book_dir(book)
        lang = self.lang(lang)
        path = book_dir / "output" / (f"{lang}.md" if kind == "translation" else f"{lang}.report.md")
        if kind not in ("translation", "report") or not path.exists():
            raise HTTPError(404, t("output_missing"))
        return path

    # prompts
    def _required(self, name: str) -> set[str]:
        default = self.root / "prompts" / "defaults" / f"{name}.md"
        reference = default if default.exists() else self.root / "prompts" / f"{name}.md"
        return set(re.findall(r"\{\{(\w+)\}\}", reference.read_text(encoding="utf-8")))

    def prompts(self) -> list[dict]:
        proj = self.reload()
        order = stages.llm_stages(proj)
        # The steps that use each instruction file; "rules" goes to every step that has {{rules}}.
        named = {s: stages.template(proj.cfg, s) if s in stages.flow(proj) or s == "translate" else s for s in order}
        users = {name: [s for s in order if named[s] == name] for name in PROMPTS}
        users["rules"] = [s for s in order if s != "align"]
        out = []
        for name in PROMPTS:
            text = (self.root / "prompts" / f"{name}.md").read_text(encoding="utf-8")
            default = self.root / "prompts" / "defaults" / f"{name}.md"
            out.append({"name": name, "description": t(f"prompt_{name}"), "text": text, "steps": users[name],
                        "required": sorted(self._required(name)), "has_default": default.exists(),
                        "changed": default.exists() and text != default.read_text(encoding="utf-8")})
        return out

    def save_prompt(self, name: str, body: dict) -> dict:
        if name not in PROMPTS:
            raise HTTPError(404, t("not_found"))
        text = str(body.get("text", "")).replace("\r\n", "\n")
        required = self._required(name)
        found = set(re.findall(r"\{\{(\w+)\}\}", text))
        problems = []
        if required - found:
            problems.append(t("placeholders_missing", names=", ".join("{{%s}}" % p for p in sorted(required - found))))
        if found - required:
            problems.append(t("placeholders_unknown", names=", ".join("{{%s}}" % p for p in sorted(found - required))))
        if problems:
            raise HTTPError(400, t("prompt_not_saved", problems="; ".join(problems)))
        write_text(self.root / "prompts" / f"{name}.md", text if text.endswith("\n") else text + "\n")
        return {"message": t("prompt_saved")}

    def restore_prompt(self, name: str) -> dict:
        default = self.root / "prompts" / "defaults" / f"{name}.md"
        if name not in PROMPTS or not default.exists():
            raise HTTPError(404, t("not_found"))
        write_text(self.root / "prompts" / f"{name}.md", default.read_text(encoding="utf-8"))
        return {"message": t("prompt_restored")}


def _check_file(path: Path, ext: str) -> None:
    """Checks the content of the file, not its extension."""
    with open(path, "rb") as f:
        head = f.read(8)
    if ext in (".docx", ".epub"):
        needed = "word/document.xml" if ext == ".docx" else "META-INF/container.xml"
        ok = head.startswith(b"PK\x03\x04") and zipfile.is_zipfile(path)
        if ok:
            with zipfile.ZipFile(path) as z:
                ok = needed in z.namelist()
        if not ok:
            raise HTTPError(400, t("upload_not_valid", ext=ext))
    elif ext == ".pdf":
        if not head.startswith(b"%PDF-"):
            raise HTTPError(400, t("upload_not_valid", ext=ext))
    else:
        try:
            path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise HTTPError(400, t("upload_not_utf8")) from None


# --- HTTP -------------------------------------------------------------------

ROUTES = [
    ("GET", r"/api/tools", lambda a, m, b: a.tools()),
    ("POST", r"/api/tools/install-missing", lambda a, m, b: a.install_missing()),
    ("POST", r"/api/tools/(\w+)/install", lambda a, m, b: a.install_one(m[1])),
    ("POST", r"/api/tools/(\w+)/login", lambda a, m, b: a.login(m[1], b)),
    ("POST", r"/api/tools/(\w+)/test", lambda a, m, b: a.test_tool(m[1])),
    ("GET", r"/api/settings", lambda a, m, b: a.settings()),
    ("PUT", r"/api/stages", lambda a, m, b: a.save_stages(b)),
    ("POST", r"/api/models/test", lambda a, m, b: a.test_model(b)),
    ("GET", r"/api/tools/(\w+)/models", lambda a, m, b: a.models(m[1])),
    ("POST", r"/api/languages", lambda a, m, b: a.add_language(b)),
    ("GET", r"/api/books", lambda a, m, b: a.books()),
    ("POST", r"/api/books", lambda a, m, b: a.create_book(b)),
    ("DELETE", r"/api/books/([\w-]+)/references/([\w-]+)", lambda a, m, b: a.delete_reference(m[1], m[2])),
    ("POST", r"/api/books/([\w-]+)/reset", lambda a, m, b: a.reset_book(m[1])),
    ("POST", r"/api/books/([\w-]+)/preview", lambda a, m, b: a.preview(m[1])),
    ("POST", r"/api/books/([\w-]+)/run", lambda a, m, b: a.run_book(m[1], b)),
    ("POST", r"/api/books/([\w-]+)/estimate", lambda a, m, b: a.estimate(m[1], b)),
    ("POST", r"/api/books/([\w-]+)/stop", lambda a, m, b: a.stop_book(m[1])),
    ("GET", r"/api/books/([\w-]+)/log", lambda a, m, b: a.log(m[1])),
    ("GET", r"/api/prompts", lambda a, m, b: a.prompts()),
    ("PUT", r"/api/prompts/([\w-]+)", lambda a, m, b: a.save_prompt(m[1], b)),
    ("POST", r"/api/prompts/([\w-]+)/restore", lambda a, m, b: a.restore_prompt(m[1])),
]
UPLOAD_RE = re.compile(r"/api/books/([\w-]+)/(source|references)(?:/([\w-]+))?")
OUTPUT_RE = re.compile(r"/api/books/([\w-]+)/output/([\w-]+)/(translation|report)")
EXPORT_RE = re.compile(r"/api/books/([\w-]+)/export/([\w-]+)/(translation|report)/(md|docx|html|pdf)")


def make_handler(app: App, port: int):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        server_version = "TranslationPipeline"

        def log_message(self, fmt, *args):  # request bodies and keys are never logged
            pass

        def send(self, code: int, body: bytes, content_type: str, extra: dict | None = None):
            self.send_response(code)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            for key, value in (extra or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, code: int, data):
            self.send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json")

        def handle_any(self, method: str):
            url = urlparse(self.path)
            path, query = unquote(url.path), parse_qs(url.query)
            i18n.set_request(self.headers.get("X-Lang") or query.get("lang", [None])[0])
            try:
                # Against DNS rebinding: only requests addressed to a local name.
                if self.headers.get("Host") not in allowed_hosts:
                    raise HTTPError(403, t("bad_host"))
                if not path.startswith("/api/"):
                    return self.static(method, path)
                # Prevents other web sites from sending requests to this server.
                token = self.headers.get("X-Token") or query.get("token", [""])[0]
                if not hmac.compare_digest(token, app.token):
                    raise HTTPError(403, t("bad_token"))
                length = int(self.headers.get("Content-Length") or 0)

                m = UPLOAD_RE.fullmatch(path)
                if method == "PUT" and m:
                    filename = Path(query.get("file", [""])[0]).name
                    return self.send_json(200, app.upload(m[1], m[2], m[3], filename, length, self.rfile))
                m = OUTPUT_RE.fullmatch(path)
                if method == "GET" and m:
                    out = app.output_path(m[1], m[2], m[3])
                    extra = {}
                    if query.get("download"):
                        extra["Content-Disposition"] = f'attachment; filename="{m[1]}-{out.name}"'
                    return self.send(200, out.read_bytes(), "text/markdown", extra)

                m = EXPORT_RE.fullmatch(path)
                if method == "GET" and m:
                    data, mime, filename = app.export(m[1], m[2], m[3], m[4])
                    # A PDF opens in a new tab (the browser's PDF viewer has a save button); the others download.
                    extra = {"Content-Disposition": f'{"inline" if m[4] == "pdf" else "attachment"}; filename="{filename}"'}
                    return self.send(200, data, mime, extra)

                route = next(((fn, m) for route_method, pattern, fn in ROUTES
                              if route_method == method and (m := re.fullmatch(pattern, path))), None)
                if not route:
                    raise HTTPError(404, t("not_found"))
                body = {}
                if length:
                    if length > JSON_LIMIT:
                        raise HTTPError(413, t("request_too_large"))
                    try:
                        body = json.loads(self.rfile.read(length))
                    except (json.JSONDecodeError, UnicodeDecodeError):
                        raise HTTPError(400, t("bad_request")) from None
                    if not isinstance(body, dict):
                        raise HTTPError(400, t("bad_request"))
                fn, m = route
                return self.send_json(200, fn(app, m, body))
            except HTTPError as e:
                self.send_json(e.code, {"error": str(e)})
            except PipelineError as e:
                self.send_json(400, {"error": str(e)})
            except Exception as e:  # keep the server alive; details only in the terminal
                say(f"[ui] unexpected error: {type(e).__name__}: {e}")
                self.send_json(500, {"error": t("unexpected_error")})
            finally:
                i18n.set_request(None)

        def static(self, method: str, path: str):
            if method != "GET":
                raise HTTPError(405, t("not_allowed"))
            name = "index.html" if path == "/" else path.lstrip("/")
            if name not in STATIC_TYPES:
                raise HTTPError(404, t("not_found"))
            body = (STATIC / name).read_bytes()
            if name == "index.html":
                body = body.replace(b"__TOKEN__", app.token.encode())
            self.send(200, body, STATIC_TYPES[name])

        def do_GET(self):
            self.handle_any("GET")

        def do_POST(self):
            self.handle_any("POST")

        def do_PUT(self):
            self.handle_any("PUT")

        def do_DELETE(self):
            self.handle_any("DELETE")

    return Handler


def serve(proj: Project, port: int = 8765, open_browser: bool = True) -> None:
    tools.extend_path(proj.root)
    (proj.root / "books").mkdir(exist_ok=True)
    app = App(proj)
    url = f"http://127.0.0.1:{port}/"
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app, port))
    except OSError:
        # Usually the interface is already open (the launcher was started twice): show that one.
        say(t("ui_port_busy", url=url, port=port))
        if open_browser:
            webbrowser.open(url)
        return
    say(t("ui_running", url=url))
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=[url]).start()
    try:
        server.serve_forever()
    finally:
        server.server_close()
