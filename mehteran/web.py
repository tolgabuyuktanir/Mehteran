"""Web interface: python -m mehteran ui  ->  http://127.0.0.1:8766/

The standard library HTTP server, reachable only from this computer. The same protections as the translation
app's interface (pipeline/web.py):
- requests must be addressed to 127.0.0.1:<port> or localhost:<port> (against DNS rebinding),
- every /api/ request carries the session key made at start (compared in constant time),
- JSON bodies and uploads have size limits; uploaded file names are reduced to a safe base name,
- every file is resolved inside the data folder; a path that leaves it is refused,
- answers are not cached and not content-sniffed; the page has a strict Content-Security-Policy.

The Setup tab works like the translation app's one, on the same code (pipeline.tools and pipeline.runtime, used
read-only): the tools go into the same <code folder>/.runtime, so both programs share one installation. Mehteran
never writes the translation app's config.toml: the model lists it reads from the tools are kept in
<data>/configurations/models.json and offered next to the models of config.toml.
"""

from __future__ import annotations

import copy
import hashlib
import hmac
import json
import math
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse

from pipeline import i18n as pipeline_i18n
from pipeline import runtime, system, tools
from pipeline.core import ROOT, PipelineError, Project

from . import __version__, i18n, languages, paths, schema, settings, templates, translation, yamlio
from . import providers as adapters
from .engine import FILES_SIZE_LIMIT, Engine, RunError, resume_on_start, safe_filename
from .i18n import UI, t
from .nodes import FORMATS, ID_RE, PROVIDER_RE, REGISTRY
from .placeholders import ITEM_FIELDS

UPLOAD_LIMIT = 300 * 1024 * 1024
TRANSLATION_FAVORITE = "app:translation"  # the book translation, a favorite like a template (library.json)
# The choices of the first-start panel, in its order. Each leads to one built-in template (its run window), to a
# category of the library, to a few named templates, or to the book translation.
WELCOME_CHOICES = (
    ("document", {"template": "document-explainer"}),
    ("writing", {"templates": ("email-reply-draft", "official-letter-writer", "cv-and-cover-letter", "social-media-posts",
                               "plain-language-rewrite", "writing-polish")}),
    ("data", {"category": "data"}),
    ("education", {"category": "education"}),
    ("research", {"category": "research"}),
    ("translation", {}),
)
JSON_LIMIT = 2 * 1024 * 1024
STATIC = Path(__file__).resolve().parent / "ui"
STATIC_TYPES = {"index.html": "text/html", "app.js": "text/javascript", "style.css": "text/css",
                "canvas.js": "text/javascript", "editor.js": "text/javascript", "live.js": "text/javascript",
                "icon.svg": "image/svg+xml", "langpicker.js": "text/javascript", "markdown.js": "text/javascript",
                "history.js": "text/javascript"}
FLAG_RE = re.compile(r"/flags/([a-z]{2}(?:-[a-z]{2})?)\.svg\Z")  # the flags of the language picker (ui/flags)
TR_LOCALE_RE = re.compile(r"/tr/locales/([a-z]{2})\.json\Z")  # the book translation's texts in other languages
UPLOAD_RE = re.compile(r"[0-9a-f]{32}\Z")
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
       "font-src 'self'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
TEXT_FILES = {".md", ".txt", ".yaml", ".json"}
EDIT_LIMIT = 1024 * 1024  # bytes of an edited result (UTF-8); the JSON request around it stays under JSON_LIMIT
EDITABLE_RE = re.compile(r"nodes/([a-z][a-z0-9_-]{0,63})/([A-Za-z0-9][A-Za-z0-9_-]{0,99})\.md")  # a step's Markdown output


class HTTPError(Exception):
    def __init__(self, code: int, message: str, problems: list[str] | None = None):
        super().__init__(message)
        self.code, self.problems = code, problems or []


def code_stamp() -> str:
    """A short fingerprint of the code on disk (names, sizes, modification times of mehteran/*.py and ui/*, and of
    the translation app's pipeline/*.py and pipeline/ui/*, which this server runs and serves too). The server keeps
    the one it started with; when the files change, the page can say the server is out of date: it would serve the
    new page with the old Python code and texts."""
    digest = hashlib.sha256()
    files = [*paths.CODE.glob("*.py"), *STATIC.glob("*"), *(paths.REPO / "pipeline").glob("*.py"), *translation.STATIC.glob("*"),
             paths.CODE / "languages.json", *i18n.LOCALES.glob("*.json"), *(translation.STATIC / "locales").glob("*.json")]
    for path in sorted(files):
        if path.is_file():
            stat = path.stat()
            digest.update(f"{path.relative_to(paths.REPO).as_posix()}:{stat.st_size}:{stat.st_mtime_ns}\n".encode())
    return digest.hexdigest()[:16]


def running_stale(port: int) -> bool | None:
    """Asks the program on 127.0.0.1:port whether it is a Mehteran older than the code on disk. None: not Mehteran,
    or no answer."""
    import urllib.error
    import urllib.request
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/version", timeout=3) as res:
            return bool(json.loads(res.read()).get("stale")) if res.headers.get("Server", "").startswith("Mehteran") else None
    except urllib.error.HTTPError as e:
        # A Mehteran from before this check has no such address: it is older than the code on disk.
        return True if e.code == 404 and e.headers.get("Server", "").startswith("Mehteran") else None
    except (OSError, ValueError):
        return None


class Jobs:
    """Install jobs started by this server: a process each, its output in a log file (as in the translation app)."""

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
        done, failed = t("job_done"), t("job_failed")

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
        log = job["log"].read_bytes()[-20000:].decode("utf-8", "replace") if job["log"].exists() else ""
        return {"running": not job["closed"], "code": job["proc"].poll(), "log": log}


def _jsonable(value):
    """A YAML value as JSON: dates, sets and other YAML types become text, so the editor can show them."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if value is None or isinstance(value, (str, bool, int)) or (isinstance(value, float) and math.isfinite(value)):
        return value
    return str(value)


def _ports(model) -> dict:
    """The output ports of each node of a model ({node: {port: kind}}), also when the model has problems."""
    out = {}
    for node in (model.get("nodes") if isinstance(model, dict) and isinstance(model.get("nodes"), list) else []):
        if isinstance(node, dict) and isinstance(node.get("id"), str) and isinstance(node.get("type"), str) \
                and node["type"] in REGISTRY:
            out[node["id"]] = REGISTRY[node["type"]].outputs(node["config"] if isinstance(node.get("config"), dict) else {})
    return out


def _check(model) -> dict:
    """The full check of an editor model: valid, the problems with their place, the ports of each node."""
    try:
        wf = schema.check(copy.deepcopy(model))
    except schema.WorkflowError as e:
        return {"valid": False, "problems": e.items(), "warnings": [], "ports": _ports(model)}
    # warnings (schema.warnings): a valid workflow that probably does not do what its author wants
    return {"valid": True, "problems": [], "warnings": [w.item() for w in schema.warnings(wf)], "ports": _ports(model)}


def _model(body) -> dict:
    model = body.get("model")
    if not isinstance(model, dict):
        raise HTTPError(400, t("bad_request"))
    return model


class App:
    def __init__(self, engine: Engine):
        self.engine = engine
        self.home = engine.home
        self.token = secrets.token_urlsafe(32)
        self.jobs = Jobs()
        self.configurations = self.home / "configurations"
        self.conf_lock = threading.Lock()  # two model lists read at once must not lose one of them
        self.stamp = code_stamp()
        self.uploads = self.home / "executions" / ".uploads"
        self.uploads.mkdir(parents=True, exist_ok=True)
        self._clean_uploads()
        self.translation = None  # the translation app (mehteran.translation.Translation), set by serve()
        from . import history
        self.automation = history.Automation(engine)  # batch starts and saves to a folder (history.py)
        self.automation.kick()  # work left from before a restart: queued batch runs, saves not done yet

    def _clean_uploads(self) -> None:
        """Uploads that never became a run are removed after a day."""
        for folder in self.uploads.iterdir():
            if folder.is_dir() and time.time() - folder.stat().st_mtime > 86400:
                shutil.rmtree(folder, ignore_errors=True)

    # --- information ---
    def info(self, m, body) -> dict:
        cfg = self.engine.provider_cfg
        loaded = self._read_conf("models.json")
        providers = settings.provider_choices(cfg)
        for item in providers:  # the models read from the tool first, then those of config.toml
            item["models"] = list(dict.fromkeys([*(loaded.get(item["name"]) or []), *item["models"]]))
            item["tool"] = next((tool for tool, spec in tools.TOOLS.items()
                                 if adapters.canonical(spec["provider"] or "") == item["name"]), None)
            item.update(_provider_facts(item["name"], cfg["providers"][item["name"]]))
        node_types = {name: {
            "label": nt.label, "description": nt.description, "outputs": nt.outputs({}),
            "takes_retries": nt.takes_retries, "default_retries": nt.default_retries, "default_timeout": nt.default_timeout,
            "config": {key: {"kind": f.kind, "required": f.required, "default": f.default, "label": f.label,
                             "widget": f.widget} for key, f in nt.config.items()}} for name, nt in REGISTRY.items()}
        return {"version": __version__, "home": str(self.home), "providers": providers, "stale": code_stamp() != self.stamp,
                "config_source": cfg.get("source", ""), "node_types": node_types,
                "translation": {**(self.translation.info() if self.translation else {"running": False, "error": "translation_not_started",
                                                                                     "detail": ""}),
                                "favorite": TRANSLATION_FAVORITE in self._favorites()},
                # the limits of a run's files, shown by the run window (engine.FILES_SIZE_LIMIT, schema.MAX_FILES)
                "max_files": schema.MAX_FILES, "files_limit_mb": FILES_SIZE_LIMIT // 1024 // 1024,
                "upload_limit_mb": UPLOAD_LIMIT // 1024 // 1024,
                "formats": list(FORMATS), "file_formats": list(schema.FILE_FORMATS), "input_types": list(schema.INPUT_TYPES)}

    # --- settings that Mehteran keeps itself (<data>/configurations) ---
    def _read_conf(self, name: str) -> dict:
        try:
            data = json.loads((self.configurations / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    def _update_conf(self, name: str, key: str, value) -> None:
        with self.conf_lock:
            data = self._read_conf(name)
            data[key] = value
            self._write_conf(name, data)

    def _write_conf(self, name: str, data: dict) -> None:
        self.configurations.mkdir(parents=True, exist_ok=True)
        tmp = self.configurations / f"{name}.{secrets.token_hex(4)}.tmp"
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        paths.replace(tmp, self.configurations / name)

    # --- setup: the same tools, installs and sign-ins as the translation app ---
    def _used(self) -> dict[str, list[str]]:
        """provider -> the names of the templates that use it (a model input's default or a fixed model)."""
        used: dict[str, list[str]] = {}
        autos: dict[str, str] = {}
        for item in templates.listing(self.home):
            if not item["valid"]:
                continue
            wf = schema.parse(templates.read(item["source"], item["id"], self.home))
            names = [spec["default"] for spec in wf.inputs.values() if spec["type"] == "provider" and spec.get("default")]
            names += [n["config"]["provider"] for n in wf.nodes.values() if isinstance(n["config"].get("provider"), str)
                      and PROVIDER_RE.match(n["config"]["provider"].strip())]
            for name in names:
                if name.strip() in adapters.AUTO:  # `auto`: the tool it uses now; with none usable, the first adapter
                    if name not in autos:  # once per kind: each answer asks every tool for its state (not setdefault,
                        autos[name] = (self._auto_now(name.strip())  # which would ask again for every template)
                                       or ("ollama" if name.strip() == "auto:local" else next(iter(adapters.ADAPTERS))))
                    name = autos[name]
                provider = adapters.canonical(name.partition("@")[0].partition("/")[0])
                if i18n.localized(wf.data["name"]) not in used.setdefault(provider, []):
                    used[provider].append(i18n.localized(wf.data["name"]))
        return used

    def _translation_used(self) -> set[str]:
        """The providers that the translation workflow uses (its config.toml stages), as its Setup tab counts them.
        Empty when the translation app is not loaded."""
        if not (self.translation and self.translation.app):
            return set()
        from pipeline import stages
        from pipeline.core import split_name
        try:
            proj = self.translation.app.reload()
            return {split_name(name)[0] for stage in stages.llm_stages(proj) for name in proj.providers_for(stage)}
        except (PipelineError, OSError, KeyError, ValueError):
            return set()

    def tools(self, m, body) -> dict:
        tools.extend_path(ROOT)  # a tool installed a moment ago may have created a new folder on PATH
        lang = i18n.current()
        jobs = {tool: self.jobs.info(f"install:{tool}") for tool in tools.TOOLS}  # before the status (as translate)
        all_job = self.jobs.info("install:all")

        def status(tool):
            pipeline_i18n.set_request(i18n.pipeline_lang(lang))  # pool threads do not inherit the request language
            return tools.status(tool)

        with ThreadPoolExecutor(max_workers=3) as pool:
            items = list(pool.map(status, tools.TOOLS))
        used = self._used()
        translation_used = self._translation_used()
        configured = self.engine.provider_cfg["providers"]
        quota = {**_read_json(ROOT / ".jobs" / "quota.json"), **self._read_conf("quota.json")}
        states = self._tool_states()  # billing and calls at once (stream P)
        user = adapters.read_settings(self.home)
        for item in items:
            mine = adapters.canonical(item["provider"]) if item["provider"] else None  # "chatgpt" is codex here
            item["templates"] = used.get(mine, []) if mine in configured else []
            item["translation"] = item["provider"] in translation_used
            item["configured"] = item["provider"] is None or mine in configured
            if mine in adapters.ADAPTERS:
                item.update(_provider_facts(mine, configured.get(mine) or {}), **_provider_state(mine, states[mine], user))
            item["required"] = bool(item["templates"]) or item["translation"] or item["provider"] is None
            if item["provider"] is None:
                item["name"] = pipeline_i18n.t(f"tool_name_{item['id']}")
            item["job"] = jobs[item["id"]]
            item["requirements"] = pipeline_i18n.t(f"requirements_{item['id']}")
            item["sign_in_help"] = pipeline_i18n.t(f"sign_in_help_{item['id']}")
            item["quota"] = quota.get(item["provider"])
        return {"tools": items, "terminal": system.can_open_terminal(), "all_job": all_job,
                "runs": len(self.engine.list())}

    def _tool(self, tool: str, model: bool = False) -> dict:
        if tool not in tools.TOOLS or (model and tools.TOOLS[tool]["provider"] is None):
            raise HTTPError(404, t("not_found"))
        return tools.TOOLS[tool]

    def _install(self, names: list[str], key: str) -> dict:
        env = os.environ.copy()
        env.update({"TP_LANG": i18n.pipeline_lang(), "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1",
                    "PYTHONPATH": str(paths.REPO) + os.pathsep + env.get("PYTHONPATH", "")})
        self.jobs.start(f"install:{key}", [sys.executable, "-m", "mehteran", "install", *names],
                        self.home / "jobs" / f"install-{key}.log", env=env, cwd=paths.REPO)
        return {"message": t("install_started")}

    def install_one(self, m, body) -> dict:
        self._tool(m[1])
        return self._install([m[1]], m[1])

    def install_missing(self, m, body) -> dict:
        """Installs the tools that the templates and the translation workflow use, and the PDF reader; the others
        have their own button."""
        tools.extend_path(ROOT)
        used = {**self._used(), **{p: ["translation"] for p in self._translation_used()}}
        missing = [tool for tool, spec in tools.TOOLS.items()
                   if (spec["provider"] is None or spec["provider"] in used) and not shutil.which(spec["command"])]
        if not missing:
            return {"message": t("nothing_to_install")}
        return self._install(missing, "all")

    def models(self, m, body) -> dict:
        """The model list of a tool, read from the tool itself and kept in <data>/configurations/models.json."""
        spec = self._tool(m[1], model=True)
        tools.extend_path(ROOT)
        names = tools.list_models(m[1])
        if names:
            self._update_conf("models.json", spec["provider"], names)
        else:
            names = self._read_conf("models.json").get(spec["provider"]) or []
        return {"models": names}

    def login(self, m, body) -> dict:
        self._tool(m[1], model=True)
        return {"message": tools.login(m[1], str(body.get("method", "")), str(body.get("key", "")))}

    def test_tool(self, m, body) -> dict:
        return self.test_model(m, {"name": self._tool(m[1], model=True)["provider"]})

    def test_model(self, m, body) -> dict:
        """One short call to the model, the way a workflow calls it (an adapter, or pipeline.providers.run for a
        provider of config.toml)."""
        from pipeline.providers import QuotaError, run as run_llm
        cfg = self.engine.provider_cfg
        name = str(body.get("name", "")).strip()
        name = self.engine.resolve_model(name) or name  # `auto`: the model a run would use now
        provider = name.partition("@")[0].partition("/")[0]
        if not PROVIDER_RE.match(name) or provider not in cfg["providers"]:
            raise HTTPError(400, t("bad_provider", value=name))
        tools.extend_path(ROOT)
        started = time.time()
        if cfg["providers"][provider].get("api") == "ollama":  # a local model: Mehteran calls Ollama itself
            from . import ollama
            model = name.partition("@")[0].partition("/")[2] or cfg["providers"][provider].get("model") or ""
            try:
                ollama.ensure_running()
                answer = ollama.chat(model, "Reply with exactly this word and nothing else: OK", settings.SYSTEM_PROMPT, 180,
                                     cfg["providers"][provider].get("options"))
            except ollama.OllamaError as e:
                raise HTTPError(400, str(e)) from None
            return {"message": t("test_answer", seconds=f"{time.time() - started:.0f}", answer=answer.strip()[:60])}
        spec = cfg["providers"][provider]
        if spec.get("adapter") == "openai-local":  # the local server (Setup: "Test")
            from .providers import base
            try:
                answer = adapters.ADAPTERS["openai-local"].chat(spec.get("url", ""), adapters.split(name)[1] or spec.get("model", ""),
                                                                "Reply with exactly this word and nothing else: OK",
                                                                base.SYSTEM_PROMPT, 180)
            except base.CallError as e:
                raise HTTPError(400, str(e)) from None
            return {"message": t("test_answer", seconds=f"{time.time() - started:.0f}", answer=answer.strip()[:60])}
        if spec.get("adapter") in adapters.ADAPTERS:  # with the billing guard, as a run calls it
            from .providers import base
            _, model, effort = adapters.split(name)
            try:
                answer, _ = base.run(adapters.ADAPTERS[spec["adapter"]], spec, model, effort,
                                     "Reply with exactly this word and nothing else: OK", 180)
            except base.UsageLimit as e:
                self._update_conf("quota.json", provider, {"until": e.until, "since": time.time(), "message": str(e)})
                raise HTTPError(400, t("quota_known", name=provider, time=time.strftime("%H:%M", time.localtime(e.until)))) from None
            except base.CallError as e:
                raise HTTPError(400, str(e)) from None
            return {"message": t("test_answer", seconds=f"{time.time() - started:.0f}", answer=answer.strip()[:60])}
        try:
            answer = run_llm(Project(ROOT, {"providers": cfg["providers"], "general": cfg["general"]}), name,
                             "Reply with exactly this word and nothing else: OK", wait_for_quota=False, attempts=1, timeout=180)
        except QuotaError as e:
            self._update_conf("quota.json", provider, {"until": e.until, "since": time.time(), "message": str(e)})
            raise
        return {"message": t("test_answer", seconds=f"{time.time() - started:.0f}", answer=answer.strip()[:60])}

    # --- stream P: the AI tools of the workflows (mehteran/providers/): billing, the model order, `auto` ---
    def _tool_states(self) -> dict:
        return (self.engine.tool_states or adapters.statuses)()  # the tests give the engine fake states

    def _auto_now(self, kind: str) -> str:
        """The model that `kind` would use if a run started now ("" when none can)."""
        cfg = self.engine.provider_cfg
        found = [c for c in adapters.candidates(kind, self._tool_states(), adapters.read_settings(self.home))
                 if adapters.split(c)[0] in cfg["providers"]]
        blocked = self.engine.known_limits()
        return sorted(found, key=lambda c: adapters.split(c)[0] in blocked)[0] if found else ""

    def providers_get(self, m, body) -> dict:
        """Each adapter with its state, billing and calls at once; the model order; what each `auto` kind uses now."""
        cfg = self.engine.provider_cfg
        user = adapters.read_settings(self.home)
        states = self._tool_states()
        blocked = self.engine.known_limits()
        busy = adapters.busy()
        items = []
        for name in adapters.ADAPTERS:
            if name not in cfg["providers"]:
                continue
            st = states[name]
            items.append({"name": name, "installed": st.get("installed", False), "signed_in": st.get("signed_in", False),
                          **_provider_facts(name, cfg["providers"][name]), **_provider_state(name, st, user),
                          "blocked_until": blocked.get(name), "in_use": busy.get(name, {}).get("in_use", 0),
                          "models": st.get("models") or [], "url": user["providers"].get(name, {}).get("url", ""),
                          "model": user["providers"].get(name, {}).get("model", "")})
        auto = {}
        for kind in adapters.AUTO:
            chosen = self._auto_now(kind)
            provider, model, _ = adapters.split(chosen)
            auto[kind] = {"name": chosen, **adapters.destination(provider, model, cfg["providers"].get(provider))} if chosen else None
        return {"providers": items, "order": adapters.order(states, user), "order_is_default": not user["order"],
                "auto": auto}

    def providers_put(self, m, body) -> dict:
        """Saves the model order ({"order": [model]}) and per tool "API key (billed)" and calls at once
        ({"providers": {name: {api_key, concurrency}}}) in <data>/configurations/providers.toml."""
        user = adapters.read_settings(self.home)
        if "order" in body:
            order = body["order"]
            if not isinstance(order, list) or len(order) > 20 or not all(
                    isinstance(e, str) and adapters.ENTRY_RE.match(e) and adapters.split(e)[0] in adapters.ADAPTERS
                    for e in order):
                raise HTTPError(400, t("bad_request"))
            user["order"] = list(dict.fromkeys(order))
        for name, change in (body.get("providers") or {}).items() if isinstance(body.get("providers"), dict) else []:
            if name not in adapters.ADAPTERS or not isinstance(change, dict):
                raise HTTPError(400, t("bad_request"))
            mine = user["providers"].setdefault(name, {})
            if isinstance(change.get("api_key"), bool):
                mine["api_key"] = change["api_key"]
            if isinstance(change.get("concurrency"), int) and not isinstance(change["concurrency"], bool):
                mine["concurrency"] = min(max(change["concurrency"], 1), adapters.MAX_CONCURRENCY)
            if name == "openai-local" and "url" in change:  # only an address on this computer
                url = adapters.loopback_url(change["url"]) if change["url"] else ""
                if url is None:
                    raise HTTPError(400, t("local_server_url_bad"))
                mine["url"] = url
            if name in adapters.NEEDS_MODEL and isinstance(change.get("model"), str):
                mine["model"] = change["model"].strip()[:120]
        with self.conf_lock:
            adapters.write_settings(self.home, user)
        adapters.forget_status()
        self.engine.reload_providers()
        return self.providers_get(m, {})

    # --- the visual editor ---
    def editor_check(self, m, body) -> dict:
        return _check(_model(body))

    def editor_yaml(self, m, body) -> dict:
        return {"yaml": schema.dump(_model(body))}

    def editor_parse(self, m, body) -> dict:
        """YAML text -> the editor's model. Text that is not a YAML mapping is refused with its problems, so the
        editor stays on the YAML tab and keeps the text."""
        text = str(body.get("yaml", ""))
        try:
            if len(text) > 1_000_000:
                raise schema.WorkflowError([schema.Problem("", "yaml_too_large")])
            try:
                data = yamlio.load(text)
            except yamlio.YAMLError as e:
                raise schema.WorkflowError([schema.Problem("", "yaml_invalid", {"error": e})]) from None
            if not isinstance(data, dict):
                raise schema.WorkflowError([schema.Problem("", "not_a_mapping")])
        except schema.WorkflowError as e:
            raise HTTPError(400, e.messages()[0], e.messages()) from None
        model = _jsonable(data)
        return {"model": model, **_check(model)}

    def editor_rename(self, m, body) -> dict:
        try:
            return {"model": schema.rename(_model(body), str(body.get("kind", "")), str(body.get("old", "")),
                                           str(body.get("new", "")))}
        except schema.WorkflowError as e:
            raise HTTPError(400, e.items()[0]["message"], e.messages()) from None

    # --- the editor's model calls (mehteran/drafting.py): "Describe it" and "Test this step", as jobs ---
    @property
    def editor_jobs(self):
        if "_editor_jobs" not in self.__dict__:
            from .drafting import Jobs
            self.__dict__["_editor_jobs"] = Jobs(self.home)
        return self.__dict__["_editor_jobs"]

    def _editor_job(self, start) -> dict:
        from .drafting import DraftError
        try:
            return start()
        except DraftError as e:
            raise HTTPError(400, str(e)) from None

    def editor_draft(self, m, body) -> dict:
        """A model writes a first draft of a workflow for {"description", "provider"}: starts the job. One model call
        (two when the first answer does not pass the check). Nothing is saved and nothing runs."""
        from . import drafting
        taken = {item["id"] for item in templates.listing(self.home)}
        return self._editor_job(lambda: {"id": drafting.start_draft(
            self.editor_jobs, self.engine, str(body.get("description", "")), str(body.get("provider", "")), taken)})

    def editor_try_source(self, m, body) -> dict:
        from . import drafting
        refs = body.get("templates") if isinstance(body.get("templates"), list) else []
        return self._editor_job(lambda: drafting.try_source(self.engine, _model(body), str(body.get("node", "")), refs[:4]))

    def editor_try(self, m, body) -> dict:
        """Runs one step of the editor's workflow alone: {"model", "node", "provider", "run": id} with the outputs of
        that run, or {"sample": text} instead of "run"."""
        from . import drafting
        sample = body.get("sample")
        if sample is not None and not isinstance(sample, str):
            raise HTTPError(400, t("bad_request"))
        return self._editor_job(lambda: {"id": drafting.start_try(
            self.editor_jobs, self.engine, _model(body), str(body.get("node", "")), str(body.get("provider", "")),
            str(body.get("run", "")), sample)})

    def editor_job_state(self, m, body) -> dict:
        offset = body.get("offset", 0)
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise HTTPError(400, t("bad_request"))
        return self._editor_job(lambda: self.editor_jobs.state(m[1], offset))

    def editor_job_cancel(self, m, body) -> dict:
        return self._editor_job(lambda: {"cancelled": self.editor_jobs.cancel(m[1])})

    def template_save_model(self, m, body) -> dict:
        return templates.save_model(m[2], _model(body), self.home, drop_comments=body.get("drop_comments") is True,
                                    draft=body.get("draft") is True)

    def template_create(self, m, body) -> dict:
        model = _model(body)
        if not isinstance(model.get("id"), str) or not ID_RE.fullmatch(model["id"]):
            raise HTTPError(400, t("bad_id", value=model.get("id")))
        new_id = templates.create_model(model, self.home, draft=body.get("draft") is True)
        return {"id": new_id, "ref": f"user:{new_id}", **templates.summary("user", new_id, self.home)}

    # --- drafts and node types (limits work) ---
    def template_save_draft(self, m, body) -> dict:
        """A user template saved with problems: {"yaml": text}, or {"model": mapping, "drop_comments"} from the
        visual editor. Answers the template's summary: valid, problems, draft."""
        if "model" in body:
            return templates.save_model(m[2], _model(body), self.home, drop_comments=body.get("drop_comments") is True,
                                        draft=True)
        return {**templates.save_draft(m[2], str(body.get("yaml", "")), self.home), "saved": True}

    def node_types(self, m, body) -> list:
        """Every node type with what a form needs to edit it: labels, ports and config fields."""
        out = []
        for name, nt in REGISTRY.items():
            fields = [{"name": key, "kind": f.kind, "widget": f.widget, "required": f.required, "default": f.default,
                       "label": f.label, "help": f.help, "basic": f.basic,
                       "options": [{"value": value, "label": label} for value, label in f.options],
                       **({"min": f.low, "max": f.high} if f.kind == "int" else {}),
                       **({"item_fields": [f"item.{x}" for x in ITEM_FIELDS]} if f.item else {})}
                      for key, f in nt.config.items()]
            out.append({"type": name, "label": nt.label, "description": nt.description,
                        "outputs": [{"name": port, "kind": kind} for port, kind in nt.outputs({}).items()],
                        "outputs_from": "formats" if name == "document.export" else None,
                        "joins": nt.joins, "branches": name == "condition",
                        "takes_retries": nt.takes_retries, "default_retries": nt.default_retries,
                        "default_timeout": nt.default_timeout, "timeout_per_call": nt.timeout_per_call,
                        "initial_config": nt.initial, "config": fields})
        return out

    # --- local tools: Ollama, Tesseract OCR, Typst, Pandoc, whisper.cpp, qpdf (installed only when the user asks) ---
    def local_tools(self, m, body) -> dict:
        """The state of each local tool, with its install job (as /api/tools has it for the AI tools)."""
        from . import ocr, ollama, pandoc, qpdf, speech, typst
        items = [ollama.status(), ocr.status(), typst.status(), pandoc.status(), speech.status(), qpdf.status()]
        for item in items:
            item["job"] = self.jobs.info(f"local:{item['id']}")
        items[1]["languages_job"] = self.jobs.info("local:ocr-languages")
        items[4]["models_job"] = self.jobs.info("local:speech-models")
        return {"tools": items, "pull": self.pulls.info()}

    def _local_job(self, key: str, args: list[str]) -> dict:
        env = os.environ.copy()
        env.update({"TP_LANG": i18n.pipeline_lang(), "PYTHONUNBUFFERED": "1", "PYTHONUTF8": "1",
                    "PYTHONPATH": str(paths.REPO) + os.pathsep + env.get("PYTHONPATH", "")})
        self.jobs.start(f"local:{key}", [sys.executable, "-m", "mehteran", "--lang", i18n.current(), "install-local", *args],
                        self.home / "jobs" / f"install-{key}.log", env=env, cwd=paths.REPO)
        return {"message": t("install_started")}

    def local_install(self, m, body) -> dict:
        from . import ocr, speech
        if m[1] == "speech-models":
            names = body.get("models") or []
            if not isinstance(names, list) or not names or any(n not in speech.MODELS for n in names):
                raise HTTPError(400, t("speech_unknown_model", name=", ".join(map(str, names)) if isinstance(names, list)
                                       else "", known=", ".join(speech.MODELS)))
            return self._local_job("speech-models", ["speech-models", *names])
        if m[1] == "ocr-languages":
            codes = body.get("languages") or []
            if not isinstance(codes, list) or not codes or any(c not in ocr.LANGUAGES for c in codes):
                raise HTTPError(400, t("ocr_unknown_language", code=", ".join(map(str, codes)) if isinstance(codes, list)
                                       else "", known=", ".join(ocr.LANGUAGES)))
            return self._local_job("ocr-languages", ["ocr-languages", *codes])
        return self._local_job(m[1], [m[1]])

    def local_cancel(self, m, body) -> dict:
        job = self.jobs.items.get(f"local:{m[1]}")
        if not job or job["proc"].poll() is not None:
            return {"cancelled": False}
        system.stop_tree(job["proc"].pid)
        return {"cancelled": True}

    def ollama_models(self, m, body) -> dict:
        """Installed models (Ollama is started for this when it is installed) and the recommended ones."""
        from . import localtools, ollama
        program, _ = ollama.binary()
        if program is not None or ollama.running():
            try:
                ollama.ensure_running()
            except ollama.OllamaError:
                pass
        installed = ollama.installed_models()
        names = {item["name"] for item in installed}
        return {"running": ollama.running(), "installed": installed, "memory": localtools.memory(),
                "disk_free": localtools.disk_free(ollama.models_dir()),
                "recommended": [{**item, "installed": item["name"] in names} for item in ollama.RECOMMENDED]}

    def ollama_pull(self, m, body) -> dict:
        from . import ollama
        name = str(body.get("name", "")).strip()
        if not ollama.MODEL_RE.match(name):
            raise HTTPError(400, t("ollama_bad_model", name=name))
        warnings, blocked = ollama.pull_warnings(name)
        if blocked and body.get("force") is not True:
            raise HTTPError(409, t("ollama_disk_blocked"), warnings)
        try:
            self.pulls.start(name)
        except ollama.OllamaError as e:
            raise HTTPError(409, str(e)) from None
        return {"started": True, "warnings": warnings}

    def ollama_pull_state(self, m, body) -> dict:
        return self.pulls.info()

    def ollama_pull_cancel(self, m, body) -> dict:
        return {"cancelled": self.pulls.cancel()}

    def ollama_delete(self, m, body) -> dict:
        from . import ollama
        try:
            ollama.ensure_running()
            ollama.delete(str(body.get("name", "")).strip())
        except ollama.OllamaError as e:
            raise HTTPError(400, str(e)) from None
        return {"ok": True}

    @property
    def pulls(self):
        if "_pulls" not in self.__dict__:
            from .ollama import Pull
            self.__dict__["_pulls"] = Pull()
        return self.__dict__["_pulls"]

    # --- usage, model switch, live logs, activity ---
    def usage(self, m, body) -> dict:
        from . import usage
        return usage.summary(self.engine.store, self.home, self.engine.provider_cfg, ROOT)

    def usage_probe(self, m, body) -> dict:
        """Claude Code's own limits: one very short call with its smallest model (only when the user asks)."""
        from . import usage
        spec = self.engine.provider_cfg["providers"].get(m[1]) or {}
        if usage.tool_of(spec) != "claude":
            raise HTTPError(400, t("usage_probe_failed", error=m[1]))
        tools.extend_path(ROOT)
        try:
            found = usage.probe_claude(self.home, str(spec["command"][0]))
        except (OSError, subprocess.SubprocessError) as e:
            raise HTTPError(400, t("usage_probe_failed", error=e)) from None
        if found is None:
            raise HTTPError(400, t("usage_probe_failed", error="no rate_limit_event"))
        return found

    def node_switch(self, m, body) -> dict:
        self.engine.switch(m[1], m[2], str(body.get("provider", "")))
        return {"ok": True}

    def run_log(self, m, body, query: dict | None = None) -> dict:
        query = query or {}
        node = (query.get("node") or [""])[0]
        try:
            offset = int((query.get("offset") or ["0"])[0])
        except ValueError:
            raise HTTPError(400, t("bad_request")) from None
        if not ID_RE.fullmatch(node):
            raise HTTPError(400, t("bad_request"))
        return self.engine.node_log(m[1], node, offset)

    def activity(self, m, body) -> dict:
        from . import usage
        return {"runs": self.engine.activity(), "translation": usage.translation_activity(ROOT), "time": time.time()}

    def translation_runs(self, m, body) -> list:
        """The last run of each book (the Runs tab lists them with the workflow runs)."""
        from . import usage
        return usage.translation_runs(ROOT)

    def docs(self, m, body) -> dict:
        """The user guide (docs/mehteran.md; its Turkish copy for Turkish), shown by the footer's "Guide" link."""
        name = "mehteran.tr.md" if i18n.current() == "tr" else "mehteran.md"
        path = paths.REPO / "docs" / name
        if not path.is_file():
            raise HTTPError(404, t("not_found"))
        return {"name": name, "text": path.read_text(encoding="utf-8")}

    def strings(self, m, body) -> dict:
        return i18n.ui_strings()  # in the request's language, and in English for a text that language lacks

    def languages(self, m, body) -> dict:
        """The language registry: every language (the output language of a workflow) and the interface languages."""
        return {"languages": languages.LANGUAGES, "ui": list(languages.UI_CODES)}

    # --- templates ---
    def template_list(self, m, body) -> list:
        favorites = set(self._favorites())
        return [{**item, "favorite": f"{item['source']}:{item['id']}" in favorites} for item in templates.listing(self.home)]

    # --- favorites: <data>/configurations/library.json {"favorites": ["builtin:<id>", "user:<id>", ...]} ---
    def _favorites(self) -> list[str]:
        value = self._read_conf("library.json").get("favorites")
        if not isinstance(value, list):
            return []
        return list(dict.fromkeys(templates.canonical_ref(x) for x in value if isinstance(x, str)))  # merged ids -> new

    def _favorite_refs(self) -> set[str]:
        """What can be a favorite: every template of the library, and the book translation ("app:translation")."""
        return {f"{item['source']}:{item['id']}" for item in templates.listing(self.home)} | {TRANSLATION_FAVORITE}

    def template_favorite(self, m, body) -> dict:
        """Marks a template (or the book translation) as a favorite or not. An id that is not in the library is refused."""
        ref = templates.canonical_ref(f"{m[1]}:{m[2]}")
        if ref not in self._favorite_refs():
            raise HTTPError(404, t("not_found"))
        with self.conf_lock:
            data = self._read_conf("library.json")
            known = self._favorite_refs()
            favorites = [x for x in self._favorites() if x != ref and x in known]  # ids deleted since are dropped
            if body.get("on") is True:
                favorites.append(ref)
            data["favorites"] = favorites
            self._write_conf("library.json", data)
        return {"favorite": body.get("on") is True}

    # --- the pre-run estimate (mehteran/estimate.py) and the first-start welcome ---
    def template_estimate(self, m, body) -> dict:
        """The model calls of a run of this template with the form's values ({"values": {input: text}}); each model
        with its tool. Nothing is read or called for it."""
        from . import estimate
        values = body.get("values") or {}
        if not isinstance(values, dict):
            raise HTTPError(400, t("bad_request"))
        out = estimate.estimate(schema.parse(templates.read(m[1], m[2], self.home)), values, self.engine.provider_cfg,
                                resolve=self._auto_now, privacy="local" if body.get("privacy") == "local" else "")
        by_provider = {name: (tool, spec["name"]) for tool, spec in tools.TOOLS.items() if spec["provider"]
                       for name in {spec["provider"], adapters.canonical(spec["provider"])}}  # "chatgpt" and "codex"
        for item in out["models"]:
            item["tool"], item["tool_name"] = by_provider.get(item["provider"], (None, None))
        return out

    def _default_providers(self, template_id: str) -> list[str]:
        """The providers a built-in template calls with its default models."""
        from . import estimate
        try:
            wf = schema.parse(templates.read("builtin", template_id, self.home))
        except (templates.TemplateError, schema.WorkflowError):
            return []
        found = estimate.estimate(wf, {}, self.engine.provider_cfg, resolve=self._auto_now)["models"]
        return list(dict.fromkeys(item["provider"] for item in found if item["provider"] and item["configured"]))

    def welcome(self, m, body) -> dict:
        """The first-start panel of the library: shown until the user runs something or closes it. That is kept in
        <data>/configurations/library.json ("welcome_closed": "dismissed" or "used"), so it holds for every browser
        and port. Each choice names the providers it needs; the page adds their state from GET /api/tools."""
        from . import usage
        closed = self._read_conf("library.json").get("welcome_closed") in ("dismissed", "used")
        if not closed and (self.engine.store.runs() or usage.translation_runs(ROOT)):
            self._update_conf("library.json", "welcome_closed", "used")  # stays closed when the runs are removed later
            closed = True
        if closed:
            return {"show": False}
        builtin = {item["id"]: item.get("category") for item in templates.listing(self.home)
                   if item["source"] == "builtin" and item["valid"]}
        choices = []
        for name, target in WELCOME_CHOICES:
            if not target:  # the book translation: the providers of its own workflow
                choices.append({"id": name, "action": "translation", "templates": [],
                                "providers": sorted(self._translation_used())})
                continue
            wanted = (target["template"],) if "template" in target else target.get("templates")
            ids = [x for x in wanted if x in builtin] if wanted else [x for x, c in builtin.items() if c == target["category"]]
            if not ids:
                continue  # a choice whose templates are not in this library is left out
            choices.append({"id": name, "action": "run" if "template" in target else "category" if "category" in target else "templates",
                            "category": target.get("category"), "templates": ids,
                            "providers": list(dict.fromkeys(p for x in ids for p in self._default_providers(x)))})
        return {"show": True, "choices": choices}

    def welcome_close(self, m, body) -> dict:
        if body.get("dismissed") is not True:
            raise HTTPError(400, t("bad_request"))
        self._update_conf("library.json", "welcome_closed", "dismissed")
        return {"show": False}

    def template_get(self, m, body) -> dict:
        text = templates.read(m[1], m[2], self.home)
        out = templates.summary(m[1], m[2], self.home)
        out["yaml"] = text
        try:
            out["model"] = _jsonable(yamlio.load(text))
        except yamlio.YAMLError:
            out["model"] = None
        if out["valid"]:
            wf = schema.parse(text)
            out["graph"] = wf.graph()
            out["input_specs"] = list(wf.inputs.values())
            out["outputs"] = wf.data.get("outputs") or []
            out["warnings"] = [{**w.item(), "label": i18n.localized(wf.nodes[w.where[6:]].get("label")) or w.where[6:]
                                if w.where.startswith("nodes.") else ""} for w in schema.warnings(wf)]  # the run window
        return out

    def template_customize(self, m, body) -> dict:
        new_id = templates.customize(m[1], m[2], str(body.get("id", "")).strip(), self.home)
        return {"id": new_id, "ref": f"user:{new_id}"}

    def template_save(self, m, body) -> dict:
        templates.save(m[2], str(body.get("yaml", "")), self.home)
        return {"ok": True}

    def template_delete(self, m, body) -> dict:
        templates.delete(m[1], m[2], self.home)
        return {"ok": True}

    def template_import(self, m, body) -> dict:
        text = str(body.get("yaml", ""))
        if isinstance(body.get("id"), str) and body["id"].strip():  # the preview's new id for a file whose id is taken
            if not ID_RE.fullmatch(body["id"].strip()):
                raise HTTPError(400, t("bad_id", value=body["id"][:70]))
            text = templates.with_id(text, body["id"].strip())
        new_id = templates.import_text(text, self.home)
        return {"id": new_id, "ref": f"user:{new_id}"}

    def template_preview(self, m, body) -> dict:
        """What importing this YAML text would add (sharing.preview), with the AI tool of each model."""
        from . import sharing
        out = sharing.preview(str(body.get("yaml", "")), self.home, self.engine.provider_cfg)
        by_provider = {spec["provider"]: (tool, spec["name"]) for tool, spec in tools.TOOLS.items() if spec["provider"]}
        for item in out.get("models") or []:
            item["tool"], item["tool_name"] = by_provider.get(item["provider"], (None, None))
        return out

    def validate(self, m, body) -> dict:
        try:
            wf = schema.parse(str(body.get("yaml", "")))
        except schema.WorkflowError as e:
            return {"valid": False, "problems": e.messages()}
        return {"valid": True, "problems": [], "graph": wf.graph()}

    # --- uploads ---
    def upload(self, filename: str, length: int, stream) -> dict:
        name = safe_filename(filename)
        ext = Path(name).suffix.lower().lstrip(".")
        problem = None
        if ext not in schema.FILE_FORMATS:
            problem = HTTPError(400, t("upload_type", formats=", ".join(schema.FILE_FORMATS)))
        elif not 0 < length <= UPLOAD_LIMIT:
            problem = HTTPError(413, t("upload_size", limit=UPLOAD_LIMIT // 1024 // 1024))
        if problem:
            # Read the body before answering; otherwise the browser sees a broken connection instead of the reason.
            while 0 < length <= UPLOAD_LIMIT and (chunk := stream.read(min(1024 * 1024, length))):
                length -= len(chunk)
            raise problem
        upload_id = secrets.token_hex(16)
        folder = self.uploads / upload_id
        folder.mkdir()
        received = 0
        with open(folder / name, "wb") as f:
            while received < length:
                chunk = stream.read(min(1024 * 1024, length - received))
                if not chunk:
                    break
                f.write(chunk)
                received += len(chunk)
        if received != length:
            shutil.rmtree(folder, ignore_errors=True)
            raise HTTPError(400, t("bad_request"))
        return {"upload": upload_id, "name": name, "size": received}

    def _upload_file(self, upload_id) -> Path:
        if not isinstance(upload_id, str) or not UPLOAD_RE.match(upload_id):
            raise HTTPError(400, t("upload_not_found"))
        folder = paths.inside(self.uploads, upload_id)
        files = [p for p in folder.iterdir() if p.is_file()] if folder and folder.is_dir() else []
        if len(files) != 1:
            raise HTTPError(400, t("upload_not_found"))
        return files[0]

    # --- runs ---
    def run_start(self, m, body) -> dict:
        source, template_id = templates.resolve(str(body.get("template", "")), self.home)
        text = templates.read(source, template_id, self.home)
        values = body.get("values") or {}
        uploads = body.get("files") or {}
        if not isinstance(values, dict) or not isinstance(uploads, dict):
            raise HTTPError(400, t("bad_request"))
        # An input with "multiple: true" takes a list of uploads.
        ids = [str(v) for value in uploads.values() for v in (value if isinstance(value, list) else [value])]
        if len(set(ids)) != len(ids) or len(ids) > schema.MAX_FILES * max(len(uploads), 1):
            raise HTTPError(400, t("bad_request"))  # one uploaded file for two inputs: the run moves each file once
        files = {str(key): [self._upload_file(v) for v in value] if isinstance(value, list) else self._upload_file(value)
                 for key, value in uploads.items()}
        output_dir = self._output_dir(f"{source}:{template_id}", body)  # history.py: save the results there too
        if isinstance(body.get("batch"), dict):  # "once per file": one queued run per file of one input
            return self._batch_start(text, f"{source}:{template_id}", values, files, body["batch"], output_dir)
        run_id = self.engine.start(text, {str(k): v for k, v in values.items()}, files,
                                   template=f"{source}:{template_id}", move_files=True, launch=False,
                                   privacy="local" if body.get("privacy") == "local" else "")
        if output_dir:
            self.engine.store.update_run(run_id, output_dir=output_dir)
        self.engine.launch(run_id)
        if output_dir:
            self.automation.kick()
        for value in files.values():
            for path in value if isinstance(value, list) else [value]:
                shutil.rmtree(path.parent, ignore_errors=True)
        return {"id": run_id}

    def run_list(self, m, body) -> list:
        from . import history
        return history.listing(self.engine)

    # --- the history: names, deleting, batches, saving to a folder (history.py) ---
    def run_label(self, m, body) -> dict:
        from . import history
        return history.set_label(self.engine, m[1], body.get("label"), body.get("note"))

    def run_delete(self, m, body) -> dict:
        """{"dry_run": true}: the size and whether it can be deleted; else deletes the run and its files."""
        from . import history
        if body.get("dry_run") is True:
            run = self.engine.get(m[1])
            return {"size": history.run_size(self.engine, m[1]), "deletable": history.deletable(self.engine, run)}
        return {"deleted": True, "size": history.delete_run(self.engine, m[1])}

    def run_cleanup(self, m, body) -> dict:
        from . import history
        days = body.get("days")
        if not isinstance(days, int) or isinstance(days, bool) or not 1 <= days <= 3650:
            raise HTTPError(400, t("bad_request"))
        return history.cleanup(self.engine, days, body.get("dry_run") is True)

    def _output_dir(self, ref: str, body) -> str | None:
        """The checked folder of "save the results to a folder", or None. A folder used for the first time must be
        confirmed by the user ("output_confirmed": true); it is then remembered, also as this workflow's folder."""
        from . import history
        value = body.get("output_dir")
        if value in (None, ""):
            return None
        folder, problem = history.folder_problem(value, self.home)
        if problem:
            raise HTTPError(400, problem)
        with self.conf_lock:
            data = self._read_conf("output_folders.json")
            confirmed = [x for x in data.get("confirmed") or [] if isinstance(x, str)]
            if str(folder) not in confirmed:
                if body.get("output_confirmed") is not True:
                    raise HTTPError(409, t("folder_confirm", path=str(folder)))
                confirmed.append(str(folder))
            workflows = data.get("workflows") if isinstance(data.get("workflows"), dict) else {}
            workflows[ref] = str(folder)
            self._write_conf("output_folders.json", {**data, "confirmed": confirmed[-200:], "workflows": workflows})
        return str(folder)

    def output_folder_get(self, m, body) -> dict:
        """The folder remembered for this workflow ("" when none)."""
        value = (self._read_conf("output_folders.json").get("workflows") or {}).get(f"{m[1]}:{m[2]}")
        return {"path": value if isinstance(value, str) else ""}

    def output_folder_check(self, m, body) -> dict:
        from . import history
        folder, problem = history.folder_problem(body.get("path"), self.home)
        confirmed = self._read_conf("output_folders.json").get("confirmed") or []
        return {"path": str(folder) if folder else "", "problem": str(problem) if problem else None,
                "confirmed": bool(folder) and str(folder) in confirmed}

    def _batch_start(self, text: str, ref: str, values: dict, files: dict, batch: dict, output_dir: str | None) -> dict:
        from . import history
        input_id, ids = str(batch.get("input", "")), batch.get("files")
        if not isinstance(ids, list) or not ids or input_id in files or len(set(map(str, ids))) != len(ids) \
                or set(map(str, ids)) & {str(p.parent.name) for v in files.values() for p in (v if isinstance(v, list) else [v])}:
            raise HTTPError(400, t("bad_request"))
        if len(ids) > history.MAX_BATCH:
            raise HTTPError(400, t("batch_too_many", limit=history.MAX_BATCH))
        each = [self._upload_file(v) for v in ids]
        batch_id, run_ids = history.start_batch(self.engine, text, ref, {str(k): v for k, v in values.items()}, files,
                                                input_id, each, output_dir)
        self.automation.kick()
        for path in each + [p for v in files.values() for p in (v if isinstance(v, list) else [v])]:
            shutil.rmtree(path.parent, ignore_errors=True)
        return {"batch": batch_id, "ids": run_ids, "id": run_ids[0]}

    def run_get(self, m, body) -> dict:
        run = self.engine.get(m[1])
        wf = schema.parse(run.pop("workflow_yaml"))
        run.pop("provider_cfg", None)
        run["graph"] = wf.graph()
        run["input_specs"] = list(wf.inputs.values())
        run["outputs"] = [{**item, "path": run["nodes"].get(item["from"].partition(".")[0], {}).get("outputs", {})
                           .get(item["from"].partition(".")[2])} for item in wf.data.get("outputs") or []]
        run["node_info"] = {n: {"type": node["type"], "label": node.get("label"),
                                "instructions": (node.get("config") or {}).get("instructions"),
                                "ports": wf.ports(n)} for n, node in wf.nodes.items()}
        run["artifacts"] = self.engine.artifacts(m[1])
        run["events"] = self.engine.store.events(m[1])
        run["active"] = self.engine.is_active(m[1])
        return run

    def run_action(self, m, body) -> dict:
        if m[2] == "cancel":
            self.engine.cancel(m[1])
        else:
            self.engine.resume(m[1])
            self.automation.kick()  # a resumed run of a batch, or one that saves to a folder after success
        return {"ok": True}

    def node_action(self, m, body) -> dict:
        run_id, node_id, action = m[1], m[2], m[3]
        if action == "retry":
            self.engine.resume(run_id, node_id)
        else:
            self.engine.decide(run_id, node_id, action == "approve", str(body.get("comment", ""))[:20_000])
        self.automation.kick()
        return {"ok": True}

    # --- edited results: <run>/edited/<node>.<name>.md next to the original output, which is never changed ---
    def _editable(self, run_id: str, rel: str) -> tuple[Path, str]:
        """The edited copy of an original output (a Markdown file of a step: nodes/<node>/<name>.md): its path and
        its path in the run folder. Anything else (inputs, other folders, a path that leaves the run folder) is refused."""
        m = EDITABLE_RE.fullmatch(rel)
        try:
            original = self.engine.artifact(run_id, rel) if m else None
        except RunError:
            original = None
        rel = f"edited/{m[1]}.{m[2]}.md" if original else ""
        path = paths.inside(self.engine.run_dir(run_id), rel) if original else None
        if path is None or path.parent.name != "edited":  # also when the edited folder is a link elsewhere
            raise HTTPError(404, t("file_not_found"))
        return path, rel

    def edit_get(self, m, body) -> dict:
        path, rel = self._editable(m[1], m[2])
        if not path.is_file():
            return {"path": rel, "exists": False, "text": None, "modified": None, "limit": EDIT_LIMIT}
        return {"path": rel, "exists": True, "text": path.read_text(encoding="utf-8"), "modified": path.stat().st_mtime,
                "limit": EDIT_LIMIT}

    def edit_save(self, m, body) -> dict:
        path, rel = self._editable(m[1], m[2])
        text = body.get("text")
        if not isinstance(text, str):
            raise HTTPError(400, t("bad_request"))
        data = text.encode("utf-8")
        if len(data) > EDIT_LIMIT:
            raise HTTPError(413, t("edit_too_large", limit=EDIT_LIMIT // 1024))
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.name}.{secrets.token_hex(4)}.tmp")
        tmp.write_bytes(data)
        paths.replace(tmp, path)
        return {"path": rel, "exists": True, "size": len(data), "modified": path.stat().st_mtime}

    def edit_export(self, m, body) -> dict:
        """The edited text as one file of FORMATS, with document.export's code (nodes.export_document), next to it."""
        from .nodes import NodeError, export_document
        source, rel = self._editable(m[1], m[2])
        fmt = body.get("format")
        if fmt not in FORMATS:
            raise HTTPError(400, t("edit_bad_format", value=str(fmt)[:20], formats=", ".join(FORMATS)))
        if not source.is_file():
            raise HTTPError(404, t("edit_not_saved"))
        if fmt == "md":
            return {"path": rel, "size": source.stat().st_size}
        run = self.engine.get(m[1])
        wf = schema.parse(run["workflow_yaml"])
        lang = next((run["inputs"][key] for key, spec in wf.inputs.items()
                     if spec["type"] == "language" and isinstance(run["inputs"].get(key), str)), "en")
        try:
            out = export_document(source.read_text(encoding="utf-8"), [fmt], run["workflow_name"], lang, source.parent,
                                  source.stem)
        except NodeError as e:
            raise HTTPError(400, str(e)) from None
        return {"path": f"edited/{out[fmt].name}", "size": out[fmt].stat().st_size}


ID = r"([a-z][a-z0-9_-]{0,63})"
RUN = r"(\d{8}-\d{6}-[0-9a-f]{6})"
ROUTES = [
    ("GET", r"/api/info", App.info),
    ("GET", r"/api/strings", App.strings),
    ("GET", r"/api/languages", App.languages),
    ("GET", r"/api/templates", App.template_list),
    ("GET", rf"/api/templates/(builtin|user)/{ID}", App.template_get),
    ("POST", rf"/api/templates/(builtin|user)/{ID}/customize", App.template_customize),
    ("PUT", rf"/api/templates/(user)/{ID}", App.template_save),
    ("DELETE", rf"/api/templates/(builtin|user)/{ID}", App.template_delete),
    ("POST", r"/api/templates/import", App.template_import),
    ("POST", r"/api/templates/preview", App.template_preview),  # the import preview (sharing.py)
    ("PUT", rf"/api/templates/(builtin|user)/{ID}/favorite", App.template_favorite),
    ("PUT", r"/api/templates/(app)/(translation)/favorite", App.template_favorite),  # the book translation's card
    ("POST", rf"/api/templates/(builtin|user)/{ID}/estimate", App.template_estimate),
    ("GET", r"/api/welcome", App.welcome),
    ("PUT", r"/api/welcome", App.welcome_close),
    ("POST", r"/api/validate", App.validate),
    ("PUT", rf"/api/templates/(user)/{ID}/model", App.template_save_model),
    ("POST", r"/api/templates/new", App.template_create),
    ("PUT", rf"/api/templates/(user)/{ID}/draft", App.template_save_draft),
    ("GET", r"/api/node-types", App.node_types),
    ("GET", r"/api/local-tools", App.local_tools),
    ("POST", r"/api/local-tools/(ollama|ocr|ocr-languages|typst|pandoc|speech|speech-models|qpdf)/install", App.local_install),
    ("POST", r"/api/local-tools/(ollama|ocr|ocr-languages|typst|pandoc|speech|speech-models|qpdf)/cancel", App.local_cancel),
    ("GET", r"/api/ollama/models", App.ollama_models),
    ("POST", r"/api/ollama/pull", App.ollama_pull),
    ("GET", r"/api/ollama/pull", App.ollama_pull_state),
    ("POST", r"/api/ollama/pull/cancel", App.ollama_pull_cancel),
    ("POST", r"/api/ollama/delete", App.ollama_delete),
    ("GET", r"/api/usage", App.usage),
    ("POST", r"/api/usage/probe/([a-z][a-z0-9_-]{0,39})", App.usage_probe),
    ("POST", rf"/api/runs/{RUN}/nodes/{ID}/switch", App.node_switch),
    ("GET", r"/api/activity", App.activity),
    ("GET", r"/api/translation/runs", App.translation_runs),
    ("GET", r"/api/docs", App.docs),
    ("POST", r"/api/editor/check", App.editor_check),
    ("POST", r"/api/editor/yaml", App.editor_yaml),
    ("POST", r"/api/editor/parse", App.editor_parse),
    ("POST", r"/api/editor/rename", App.editor_rename),
    ("POST", r"/api/editor/draft", App.editor_draft),
    ("POST", r"/api/editor/try", App.editor_try),
    ("POST", r"/api/editor/try/source", App.editor_try_source),
    ("POST", r"/api/editor/jobs/([0-9a-f]{16})", App.editor_job_state),
    ("POST", r"/api/editor/jobs/([0-9a-f]{16})/cancel", App.editor_job_cancel),
    ("GET", r"/api/tools", App.tools),
    ("GET", r"/api/providers", App.providers_get),
    ("PUT", r"/api/providers", App.providers_put),
    ("POST", r"/api/tools/install-missing", App.install_missing),
    ("POST", r"/api/tools/([a-z]{1,20})/install", App.install_one),
    ("POST", r"/api/tools/([a-z]{1,20})/login", App.login),
    ("POST", r"/api/tools/([a-z]{1,20})/test", App.test_tool),
    ("GET", r"/api/tools/([a-z]{1,20})/models", App.models),
    ("POST", r"/api/models/test", App.test_model),
    ("POST", r"/api/runs", App.run_start),
    ("GET", r"/api/runs", App.run_list),
    ("GET", rf"/api/runs/{RUN}", App.run_get),
    # the history (history.py): a run's name and note, deleting runs, saving results to a folder
    ("PUT", rf"/api/runs/{RUN}/label", App.run_label),
    ("DELETE", rf"/api/runs/{RUN}", App.run_delete),
    ("POST", r"/api/runs/cleanup", App.run_cleanup),
    ("GET", rf"/api/output-folders/(builtin|user)/{ID}", App.output_folder_get),
    ("POST", r"/api/output-folders/check", App.output_folder_check),
    ("POST", rf"/api/runs/{RUN}/(cancel|resume)", App.run_action),
    ("POST", rf"/api/runs/{RUN}/nodes/{ID}/(retry|approve|reject)", App.node_action),
    # an edited result: GET reads it, PUT {text} saves it, POST {format} exports it (the path is the original output)
    ("GET", rf"/api/runs/{RUN}/edits/(.+)", App.edit_get),
    ("PUT", rf"/api/runs/{RUN}/edits/(.+)", App.edit_save),
    ("POST", rf"/api/runs/{RUN}/edits/(.+)", App.edit_export),
]
TEMPLATE_DOWNLOAD_RE = re.compile(rf"/api/templates/(builtin|user)/{ID}/download")
TEMPLATE_SHARE_RE = re.compile(rf"/api/templates/(builtin|user)/{ID}/share")  # ?author=<name>: the shared file
FILE_RE = re.compile(rf"/api/runs/{RUN}/files/(.+)")
LOG_RE = re.compile(rf"/api/runs/{RUN}/log")  # ?node=<id>&offset=<bytes>: a node's live log from offset


def make_handler(app: App, port: int):
    allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}

    class Handler(BaseHTTPRequestHandler):
        server_version = "Mehteran"
        sys_version = ""

        def log_message(self, fmt, *args):  # request bodies and keys are never logged
            pass

        def send(self, code: int, body: bytes, content_type: str, extra: dict | None = None):
            self.send_response(code)
            self.send_header("Content-Type", content_type + ("; charset=utf-8" if content_type.startswith("text/")
                                                             or content_type.endswith("json") else ""))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", CSP)
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
            pipeline_i18n.set_request(i18n.pipeline_lang())  # the messages of pipeline.tools: Turkish or English
            try:
                if self.headers.get("Host") not in allowed_hosts:
                    raise HTTPError(403, t("bad_host"))
                if not path.startswith("/api/"):
                    return self.static(method, path)
                if method == "GET" and path == "/api/version":  # no key needed: it tells only whether the code changed
                    return self.send_json(200, {"app": "Mehteran", "version": __version__, "stamp": app.stamp,
                                                "stale": code_stamp() != app.stamp})
                token = self.headers.get("X-Token") or query.get("token", [""])[0]
                if not hmac.compare_digest(token.encode(), app.token.encode()):
                    raise HTTPError(403, t("bad_token"))
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                except ValueError:
                    raise HTTPError(400, t("bad_request")) from None
                if length < 0:
                    raise HTTPError(400, t("bad_request"))

                # The book translation: the translation app's own API (mehteran/translation.py), after the checks above.
                if url.path.startswith(translation.PREFIX + "/"):
                    if not (app.translation and app.translation.app):
                        info = app.translation.info() if app.translation else {"error": "translation_not_started", "detail": ""}
                        raise HTTPError(503, t(info["error"] or "translation_not_started", error=info["detail"]))
                    return app.translation.handle(self, method, port)

                if method == "PUT" and path == "/api/uploads":
                    return self.send_json(200, app.upload(query.get("file", [""])[0], length, self.rfile))
                if method == "GET" and (m := LOG_RE.fullmatch(path)):
                    return self.send_json(200, app.run_log(m, {}, query))
                if method == "GET" and (m := FILE_RE.fullmatch(path)):
                    return self.send_file(m[1], m[2], bool(query.get("download")))
                if method == "GET" and (m := TEMPLATE_DOWNLOAD_RE.fullmatch(path)):
                    text = templates.read(m[1], m[2], app.home)
                    return self.send(200, text.encode("utf-8"), "application/x-yaml",
                                     {"Content-Disposition": f'attachment; filename="{m[2]}.yaml"'})
                if method == "GET" and (m := TEMPLATE_SHARE_RE.fullmatch(path)):  # "Share": <id>.mehteran.yaml
                    from . import sharing
                    name, text = sharing.share_text(m[1], m[2], app.home, query.get("author", [""])[0])
                    return self.send(200, text.encode("utf-8"), "application/x-yaml",
                                     {"Content-Disposition": f'attachment; filename="{name}"'})

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
                self.send_json(e.code, {"error": str(e), "problems": e.problems})
            except templates.TemplateError as e:
                self.send_json(e.code, {"error": e.messages[0] if len(e.messages) == 1 else t("cli_invalid", count=len(e.messages)),
                                        "problems": e.messages})
            except RunError as e:
                self.send_json(400, {"error": e.messages[0] if len(e.messages) == 1 else t("cli_invalid", count=len(e.messages)),
                                     "problems": e.messages})
            except schema.WorkflowError as e:
                self.send_json(400, {"error": t("cli_invalid", count=len(e.problems)), "problems": e.messages()})
            except PipelineError as e:  # from the translation app's code: install, sign-in, model test
                self.send_json(400, {"error": str(e), "problems": []})
            except Exception as e:  # keep the server alive; details only in the terminal
                print(f"[mehteran ui] unexpected error: {type(e).__name__}: {e}", flush=True)
                self.send_json(500, {"error": t("unexpected_error")})
            finally:
                i18n.set_request(None)
                pipeline_i18n.set_request(None)

        def send_file(self, run_id: str, rel: str, download: bool):
            try:
                path = app.engine.artifact(run_id, rel)
            except RunError:
                raise HTTPError(404, t("file_not_found")) from None
            name = quote(path.name)
            # Text is shown as plain text; everything else (Word, HTML) is only downloaded, never rendered here.
            if path.suffix.lower() in TEXT_FILES and not download:
                return self.send(200, path.read_bytes(), "text/plain")
            return self.send(200, path.read_bytes(), "application/octet-stream",
                             {"Content-Disposition": f"attachment; filename*=UTF-8''{name}"})

        def static(self, method: str, path: str):
            if method != "GET":
                raise HTTPError(405, t("not_allowed"))
            if path in translation.FILES:  # the translation app's interface, from its own folder
                name, kind = translation.FILES[path]
                return self.send(200, (translation.STATIC / name).read_bytes(), kind)
            flag, locale = FLAG_RE.match(path), TR_LOCALE_RE.match(path)
            if flag and (STATIC / "flags" / f"{flag[1]}.svg").is_file():
                return self.send(200, (STATIC / "flags" / f"{flag[1]}.svg").read_bytes(), "image/svg+xml")
            if locale and (translation.STATIC / "locales" / f"{locale[1]}.json").is_file():
                return self.send(200, (translation.STATIC / "locales" / f"{locale[1]}.json").read_bytes(), "application/json")
            name = "index.html" if path == "/" else path.lstrip("/")
            if name not in STATIC_TYPES or not (STATIC / name).is_file():
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


# --- stream P: what the page shows of an AI tool -----------------------------------------------------------------
def _provider_facts(name: str, spec: dict) -> dict:
    """What does not change while Mehteran runs: the tool's name, where the text goes, calls at once."""
    adapter = adapters.ADAPTERS.get(spec.get("adapter") or "")
    where = adapters.destination(name, spec.get("model") or "", spec)
    return {"label": adapter.name if adapter else name, "adapter": spec.get("adapter"), "vendor": where["vendor"],
            "local": where["local"],
            "concurrency": spec.get("concurrency"), "context": spec.get("context"),
            "default_billing": adapter.billing if adapter else None}


def _provider_state(name: str, st: dict, user: dict) -> dict:
    """The billing a call would use now and why `auto` cannot use the tool (a message key), from its state."""
    billing = adapters.effective_billing(name, st, user)
    return {"billing": billing, "api_key_allowed": user["providers"].get(name, {}).get("api_key", False),
            # an API key is in the environment, and the worker does not pass it on
            "key_dropped": st.get("key_source") in adapters.BILLED_KEYS and billing != "api_key",
            "problem": adapters.problem(name, st, user)}


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


class Server(ThreadingHTTPServer):
    # The page asks for its scripts, styles and first data at once, and a reload adds the closing connections of the
    # page before it: the default queue of 5 waiting connections can overflow, and the browser then gets a reset.
    request_queue_size = 64
    # Windows: SO_REUSEADDR lets a second server bind a port that another one listens on, so a second start would not
    # see "port busy". Windows frees a closed port without it.
    allow_reuse_address = sys.platform != "win32"


def serve(port: int = 8766, open_browser: bool = True, engine: Engine | None = None) -> None:
    url = f"http://127.0.0.1:{port}/"
    try:
        server = Server(("127.0.0.1", port), None)  # the port first: a busy port opens no database
    except OSError:
        # As in the translation app: usually the interface is already open. A Mehteran started before an update
        # would show the new page with its old code, so that case is named.
        stale = running_stale(port)
        print(t("ui_port_stale" if stale else "ui_port_busy", url=url, port=port), flush=True)
        if open_browser and not stale:
            webbrowser.open(url)
        return
    tools.extend_path(ROOT)
    app = App(engine or Engine())
    if resume_on_start():  # opt-in: configurations/engine.toml
        app.engine.resume_interrupted()
    server.RequestHandlerClass = make_handler(app, port)
    # The book translation: the translation app's API under /api/tr/ of this server, with this server's session key.
    app.translation = translation.Translation()
    if not app.translation.start(token=app.token):
        print(t(app.translation.error, error=app.translation.detail), flush=True)
    print(t("ui_running", url=url), flush=True)
    if open_browser:
        threading.Timer(0.5, webbrowser.open, args=[url]).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

