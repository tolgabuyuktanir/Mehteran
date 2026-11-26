"""Runs workflows: a graph of nodes, each started as soon as the nodes it depends on have finished.

Independent of the web interface; the command line and the tests use it directly.

- Ready nodes run in parallel, at most `parallel` at a time per run.
- Each node has a number of retries and a timeout per attempt. A timeout or a cancel stops the attempt; an AI call
  runs in its own process (mehteran.worker) and is stopped together with the tool it started.
- The state of the run and of every node is in SQLite (store.py). A run keeps a frozen copy of its workflow, of the
  resolved provider names and of the provider settings, so it can be resumed and reproduced later.
- Node outputs are files in executions/<run>/nodes/<node>/.
- Resume: the nodes that did not finish run again; finished nodes are kept.
- An approval node stops its branch until a person approves or rejects it; the run waits without a thread.
- A condition node outputs only the port of the branch it takes; the nodes on the other branch are skipped. A
  join (text.merge, document.export) runs when at least one of its incoming branches was taken; the output of a
  skipped branch is an empty text there.
- A usage limit reported by a tool does not fail the node: it waits ("waiting_quota") until the limit resets (at
  most quota_max_hours from the frozen settings) and tries again; a cancel ends the wait.
- One process at a time drives a run: it holds a lock on executions/<run>/.lock (released when the process ends).
  A run that is "running" without a lock holder was interrupted (the process ended) and can be resumed.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import shutil
import threading
import time
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

from .common import system

from . import i18n, languages, livelog, paths, placeholders, schema, settings
from . import providers as adapters
from .i18n import t
from .nodes import REGISTRY, PROVIDER_RE, Aborted, Ctx, NodeError, QuotaWait, wrap_data
from .store import ACTIVE_NODE, BLOCKING_NODE, FINISHED_RUN, Store

RUN_ID_RE = re.compile(r"^\d{8}-\d{6}-[0-9a-f]{6}\Z")
RESUMABLE = {"failed", "cancelled", "interrupted", "queued"}
FILES_SIZE_LIMIT = 500 * 1024 * 1024  # all files of one input together
STOPPED = {"failed", "rejected", "cancelled", "interrupted"}  # a node after these cannot run


def readiness(wf: schema.Workflow, nodes: dict, node_id: str) -> str:
    """"run", "skip" or "wait" for a pending node. A connection is open (its source has not finished), live, dead
    (from a skipped branch: the port a condition did not take, or a node skipped for that reason) or stopped (from a
    failed, rejected, cancelled or interrupted node, or one skipped for that reason). Any stopped connection skips the
    node; a join runs when at least one connection is live, any other node only when all are."""
    state: dict[str, str] = {}

    def node_state(n: str) -> str:
        if n not in state:
            status = nodes[n]["status"]
            if status == "succeeded":
                state[n] = "done"
            elif status in STOPPED:
                state[n] = "stopped"
            elif status == "skipped":  # skipped on a branch not taken, unless something before it stopped
                state[n] = "stopped" if any(edge(*e) == "stopped" for e in wf.incoming(n)) else "dead"
            else:
                state[n] = "open"
        return state[n]

    def edge(source: str, port: str) -> str:
        s = node_state(source)
        if s == "done":
            return "dead" if wf.nodes[source]["type"] == "condition" and port not in nodes[source]["outputs"] else "live"
        return s

    edges = [edge(*e) for e in wf.incoming(node_id)]
    if "stopped" in edges:
        return "skip"
    if "open" in edges:
        return "wait"
    if REGISTRY[wf.nodes[node_id]["type"]].joins:
        return "run" if "live" in edges or not edges else "skip"
    return "skip" if "dead" in edges else "run"


class RunError(ValueError):
    """The run cannot start or change as asked; the messages are shown to the user."""

    def __init__(self, messages: list[str]):
        self.messages = messages
        super().__init__("\n".join(messages))


def new_run_id() -> str:
    return time.strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(3)



def step_timeout(node: dict, node_type, general: dict) -> int:
    """Seconds a step may take: its own "timeout", else for a step that calls a model the configured timeout of a
    call (general.timeout, 1200 s), else its type's default. A type that needs longer than one call (a browser agent:
    1800 s) never gets less than its own default."""
    if "timeout" in node:
        return node["timeout"]
    if not (node.get("config") or {}).get("provider"):
        return node_type.default_timeout
    call = general.get("timeout", 1200)
    return max(call, node_type.default_timeout) if node_type.default_timeout > 1200 else call

class Engine:
    def __init__(self, home: Path | None = None, provider_cfg: dict | None = None, parallel: int = 4,
                 retry_delay: float = 2.0, quota_delay: float | None = None):
        self.home = Path(home) if home else paths.home()
        self.store = Store(self.home / "databases" / "mehteran.sqlite3")
        self._provider_cfg = provider_cfg
        self.parallel = max(1, parallel)
        self.retry_delay = retry_delay
        self.quota_delay = quota_delay  # tests: seconds to wait for a usage limit instead of the tool's reset time
        self.heartbeat = 30.0  # seconds between the "still working" lines of a node's live log
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.Lock()
        self.awake = True  # keep the computer awake while runs work (tests switch it off)

    _awake_started = False

    @property
    def provider_cfg(self) -> dict:
        if self._provider_cfg is None:
            self._provider_cfg = settings.provider_config()
        return self._provider_cfg

    def run_dir(self, run_id: str) -> Path:
        if not RUN_ID_RE.match(run_id or ""):
            raise RunError([t("run_not_found", id=run_id)])
        return self.home / "executions" / run_id

    # --- starting ----------------------------------------------------------------

    def start(self, workflow_yaml: str, values: dict | None = None, files: dict | None = None, template: str = "",
              move_files: bool = False, launch: bool = True, privacy: str = "", every_step: str = "",
              unattended: bool = False) -> str:
        """Checks the workflow and the inputs, records the run and starts it in a background thread (launch=False:
        the run stays "queued" until launch(); the batches of history.py start their runs a few at a time).

        values: {input id: text} for text, choice and provider inputs. files: {input id: path, or a list of paths for
        an input with "multiple: true"} for file inputs (copied into the run folder, or moved when move_files is set).
        privacy "local" (or the workflow's "privacy: local"): only models that run on this computer.
        every_step: one model ("codex", "claude/opus@high", or an `auto` kind) for every model step of the run, in
        place of the models the workflow and its inputs set (for a person who has only one of the AI tools).
        unattended: a scheduled or batch run: see unattended_problem."""
        wf = schema.parse(workflow_yaml)
        inputs, problems = self._inputs(wf, values or {}, files or {})
        every_step = (every_step or "").strip()
        if every_step and not PROVIDER_RE.match(every_step):
            problems.append(t("bad_provider", value=every_step))
            every_step = ""
        if every_step:
            for input_id, spec in wf.inputs.items():
                if spec["type"] == "provider":
                    inputs[input_id] = every_step  # the run's record says which model the steps used
        privacy = "local" if "local" in (privacy, wf.data.get("privacy")) else ""
        providers, auto = self._resolve_providers(wf, inputs, problems, privacy,
                                                  every_step, unattended)
        if problems:
            raise RunError(problems)
        input_bytes = sum(Path(item).stat().st_size for value in (files or {}).values() for item in _as_list(value))
        if input_bytes > shutil.disk_usage(self.home).free:
            raise RunError([t("run_disk_full")])
        cap = engine_options(self.home).get("max_run_storage_gib")
        if type(cap) is int and cap > 0:
            from .history import folder_size
            if folder_size(self.home / "executions") + input_bytes >= cap * 1024**3:
                raise RunError([t("run_storage_limit", gib=cap)])

        run_id = new_run_id()
        if template.startswith("builtin:"):
            from .templates import remember_builtin
            remember_builtin(template, workflow_yaml, self.home)
        run_dir = self.run_dir(run_id)
        (run_dir / "inputs").mkdir(parents=True)
        try:
            self._create(run_id, run_dir, wf, workflow_yaml, template, inputs, providers, files, move_files, auto, privacy)
        except BaseException:
            shutil.rmtree(run_dir, ignore_errors=True)  # no run without its database row
            raise
        self.store.event(run_id, None, "created", template or wf.id)
        if launch:
            self._launch(run_id)
        return run_id

    def launch(self, run_id: str) -> None:
        """Starts a run created with start(..., launch=False)."""
        self._launch(run_id)

    def _create(self, run_id, run_dir, wf, workflow_yaml, template, inputs, providers, files, move_files,
                auto: dict | None = None, privacy: str = "") -> None:
        for input_id, source in (files or {}).items():
            target_dir = run_dir / "inputs" / input_id
            target_dir.mkdir()
            several = wf.inputs[input_id].get("multiple", False)
            stored = []
            for n, item in enumerate(_as_list(source), 1):
                folder = target_dir / str(n) if several else target_dir
                folder.mkdir(exist_ok=True)
                target = folder / safe_filename(Path(item).name)
                (shutil.move if move_files else shutil.copyfile)(str(item), str(target))
                stored.append(target.relative_to(run_dir).as_posix())
            inputs[input_id] = stored if several else stored[0]
        (run_dir / "workflow.yaml").write_text(workflow_yaml, encoding="utf-8", newline="\n")
        auto = auto or {"nodes": {}, "candidates": {}}
        used = {name.partition("@")[0].partition("/")[0]
                for name in [*providers.values(), *(c for found in auto["candidates"].values() for c in found)]}
        cfg = self.provider_cfg
        frozen = {"providers": {name: cfg["providers"][name] for name in sorted(used)}, "general": cfg["general"]}
        if privacy:
            frozen["privacy"] = privacy
        if auto["nodes"]:  # the steps of an `auto` model and the models each kind may move to (frozen with the run)
            frozen["auto"] = auto
        self.store.create_run({"id": run_id, "workflow_id": wf.id, "workflow_name": json.dumps(wf.data["name"], ensure_ascii=False),
                               "template": template, "inputs": inputs, "providers": providers, "provider_cfg": frozen,
                               "workflow_yaml": workflow_yaml, "lang": i18n.current()}, wf.order)

    def provider_problem(self, name: str) -> str | None:
        if not PROVIDER_RE.match(name or ""):
            return t("bad_provider", value=name)
        if name in adapters.AUTO:
            return None  # chosen when the run starts (_resolve_providers)
        name = adapters.canonical(name, self.provider_cfg["providers"])
        provider, _, rest = name.partition("/")
        provider = provider.partition("@")[0]
        effort = name.partition("@")[2]
        spec = self.provider_cfg["providers"].get(provider)
        if spec is None:
            return t("provider_not_configured", name=provider, names=", ".join(self.provider_cfg["providers"]) or "-")
        if effort and effort not in (spec.get("efforts") or []):
            return t("effort_not_offered", effort=effort, name=provider)
        return None

    # --- stream P: the model of each step (aliases, `auto`, privacy, known usage limits) -------------------------
    tool_states = None  # tests: a function that gives providers.statuses() without asking the real tools

    def unattended_problem(self, name: str) -> str | None:
        """Why a scheduled or batch run may not use this model (a message), or None. Unless the user allowed it on
        the Setup tab (providers.toml: unattended_subscriptions), such runs use only local models and API keys: the
        providers' consumer terms do not clearly allow automated use of a subscription (docs: "Subscriptions and
        the providers' terms"). A provider given by its command has no known billing and is not refused."""
        provider = adapters.split(name)[0]
        adapter = (self.provider_cfg["providers"].get(provider) or {}).get("adapter")
        if adapter not in adapters.ADAPTERS:
            return None
        user = adapters.read_settings(self.home)
        if user["unattended_subscriptions"]:
            return None
        state = ((self.tool_states or adapters.statuses)()).get(adapter) or {}
        if adapters.effective_billing(adapter, state, user) in ("subscription", "free"):
            return t("unattended_subscription", name=adapters.ADAPTERS[adapter].name)
        return None

    def unattended_check(self, workflow_yaml: str, values: dict, privacy: str = "", every_step: str = "") -> None:
        """The models a scheduled run of this workflow would use, checked now (a schedule is refused when it is
        made, not later at its time). Raises RunError."""
        wf = schema.parse(workflow_yaml)
        inputs, problems = self._inputs(wf, values or {}, {})
        if every_step:
            inputs.update({i: every_step for i, spec in wf.inputs.items() if spec["type"] == "provider"})
        privacy = "local" if "local" in (privacy, wf.data.get("privacy")) else ""
        self._resolve_providers(wf, inputs, problems, privacy, every_step, True)
        if problems:
            raise RunError(problems)

    def _resolve_providers(self, wf: schema.Workflow, inputs: dict, problems: list, privacy: str,
                           every_step: str = "", unattended: bool = False) -> tuple[dict, dict]:
        """({node_id: model, "<node>:fallback": model}, {"nodes": {node_id: kind}, "candidates": {kind: [model]}}).

        An old name becomes the adapter's ("chatgpt" -> "codex"). `auto` kinds take the first usable model of the
        user's model order whose provider has no known usage limit now; the others stay as candidates for a later
        usage limit. privacy "local": `auto` becomes auto:local and any model that does not run here is refused.
        every_step: this model for every step and every fallback, whatever the workflow sets (a browser agent keeps its
        own model unless every_step is Claude Code or `auto`). privacy "local" refuses a browser agent: it reads sites.
        unattended (a scheduled or batch run): `auto` takes only the models that unattended_problem accepts, and a
        model named by the workflow or the form that it refuses is a problem."""
        cfg = self.provider_cfg
        local_only = privacy == "local"
        auto: dict = {"nodes": {}, "candidates": {}}
        known: dict = {}

        def choose(kind: str) -> list[str]:
            if kind not in auto["candidates"]:
                if "states" not in known:
                    known["user"] = adapters.read_settings(self.home)
                    known["states"] = (self.tool_states or adapters.statuses)()
                    known["blocked"] = self.known_limits()
                found = [c for c in adapters.candidates(kind, known["states"], known["user"], local_only)
                         if adapters.split(c)[0] in cfg["providers"] and not (unattended and self.unattended_problem(c))]
                auto["candidates"][kind] = sorted(found, key=lambda c: adapters.split(c)[0] in known["blocked"])
            return auto["candidates"][kind]

        def resolve(template: str, where: str, agent: bool = False) -> str:
            name = adapters.canonical(placeholders.render(template.strip(), lambda ref: inputs.get(ref[7:], "")), cfg["providers"])
            if name in adapters.AUTO:
                kind = "auto:local" if local_only else name
                found = choose(kind)
                if agent:  # a browser agent: only Claude Code
                    found = [c for c in found if adapters.split(c)[0] == "claude"]
                if not found:
                    problems.append(f"{where}: {t('auto_none_local' if kind == 'auto:local' else 'auto_none_unattended' if unattended else 'auto_none')}")
                    return name
                if where.count(".") == 1:  # a step's own model (not its fallback)
                    auto["nodes"][where.split(".")[1]] = kind
                return found[0]
            problem = self.provider_problem(name)
            if not problem and local_only and not self.is_local(name):
                problem = t("privacy_refused", name=name)
            if not problem and unattended:
                problem = self.unattended_problem(name)
            if problem:
                problems.append(f"{where}: {problem}")
            return name

        providers = {}
        for node_id, node in wf.nodes.items():
            if isinstance(node.get("fallback_provider"), str):  # used when the step's model reports a usage limit
                providers[f"{node_id}:fallback"] = resolve(every_step or node["fallback_provider"],
                                                           f"nodes.{node_id}.fallback_provider")
            if isinstance((node.get("config") or {}).get("provider"), str):  # else no model (a plain condition)
                agent = node["type"] == "ai.agent"
                if agent and local_only:  # it reads sites with Claude Code: one clear reason, not two
                    problems.append(f"nodes.{node_id}: {t('agent_not_local')}")
                    providers[node_id] = node["config"]["provider"]
                    continue
                # "Model for every step" with another tool leaves a browser agent on its own model (Claude Code)
                own = node["config"]["provider"]
                chosen = every_step if every_step and (not agent or every_step in adapters.AUTO
                                                       or adapters.split(every_step)[0] == "claude") else own
                providers[node_id] = resolve(chosen, f"nodes.{node_id}", agent)
                if agent and adapters.split(providers[node_id])[0] != "claude":
                    problems.append(f"nodes.{node_id}: {t('agent_needs_claude', name=providers[node_id])}")
        return providers, auto

    def resolve_model(self, name: str) -> str:
        """The model a single call uses now (the editor's drafts and tests): `auto` from the model order ("" when
        none can), an old name as the adapter's."""
        if name not in adapters.AUTO:
            return adapters.canonical(name, self.provider_cfg["providers"])
        problems: list = []
        wf = schema.parse(f"schema_version: {schema.SCHEMA_VERSION}\nid: one-call\nname: x\nnodes:\n"
                          f"  - {{id: a, type: ai.cli, config: {{provider: '{name}', prompt: x}}}}\n")
        found, _ = self._resolve_providers(wf, {}, problems, "")
        return "" if problems else found["a"]

    def reload_providers(self) -> None:
        """The user changed providers.toml: read the settings again at the next run (not when a test gave them)."""
        if self._provider_cfg is not None and "source" in self._provider_cfg:
            self._provider_cfg = None

    def is_local(self, name: str) -> bool:
        provider, model, _ = adapters.split(name)
        spec = self.provider_cfg["providers"].get(provider) or {}
        return adapters.destination(provider, model or spec.get("model") or "", spec)["local"]

    def known_limits(self, exclude: tuple[str, str] | None = None) -> dict[str, float]:
        """{provider: until} of the usage limits that have not reset (all runs). exclude: (run id, node id) whose
        own limits do not count (the step waits for them itself; a resume tries again)."""
        return adapters.blocked(self.store, exclude=exclude)

    def _next_auto(self, run: dict, node_id: str, provider: str, until: float) -> str | None:
        """After a usage limit of an `auto` step: the next candidate without a known limit, or, when every one has
        a limit, the one that resets first. None: stay with this provider (it resets first, or the step is not
        `auto`)."""
        auto = run["provider_cfg"].get("auto") or {}
        kind = (auto.get("nodes") or {}).get(node_id)
        found = (auto.get("candidates") or {}).get(kind) or []
        if not kind or len(found) < 2:
            return None
        blocked = {**self.known_limits()}
        current = adapters.split(provider)[0]
        blocked[current] = max(blocked.get(current, 0), until or time.time() + 60)
        free = [c for c in found if adapters.split(c)[0] not in blocked]
        best = free[0] if free else min(found, key=lambda c: blocked[adapters.split(c)[0]])
        return best if adapters.split(best)[0] != current else None

    def _inputs(self, wf: schema.Workflow, values: dict, files: dict) -> tuple[dict, list[str]]:
        inputs, problems = {}, []
        for key in set(values) | set(files):
            if key not in wf.inputs:
                problems.append(t("unknown_run_input", id=key))
        for input_id, spec in wf.inputs.items():
            required = spec.get("required", True)
            if spec["type"] == "file":
                if input_id in values:
                    problems.append(t("input_needs_file", id=input_id))
                sources = _as_list(files.get(input_id))
                several = spec.get("multiple", False)
                if not sources:
                    if required:
                        problems.append(t("input_missing", id=input_id))
                    else:
                        inputs[input_id] = [] if several else ""
                    continue
                if len(sources) > 1 and not several:
                    problems.append(t("input_one_file", id=input_id))
                elif len(sources) > schema.MAX_FILES:
                    problems.append(t("input_too_many_files", id=input_id, limit=schema.MAX_FILES))
                formats = spec.get("formats", list(schema.FILE_FORMATS))
                size = 0
                for source in sources:
                    ext = Path(source).suffix.lower().lstrip(".")
                    if ext not in formats:
                        problems.append(t("input_bad_format", id=input_id, formats=", ".join(formats)))
                    elif not Path(source).is_file():
                        problems.append(t("input_file_missing", id=input_id, path=source))
                    else:
                        size += Path(source).stat().st_size
                if size > FILES_SIZE_LIMIT:
                    problems.append(t("input_files_too_large", id=input_id, limit=FILES_SIZE_LIMIT // 1024 // 1024))
                continue
            default = spec.get("default")
            if spec["type"] == "text" and isinstance(default, dict):
                default = i18n.localized(default)
            value = values.get(input_id, default)
            if spec["type"] == "language" and not value:
                value = i18n.current()  # no language given and no default: the language of whoever starts the run
            if value is None or (isinstance(value, str) and not value.strip() and spec["type"] != "text"):
                if required:
                    problems.append(t("input_missing", id=input_id))
                inputs[input_id] = ""
                continue
            if not isinstance(value, str):
                problems.append(t("input_not_text", id=input_id))
                continue
            if spec["type"] == "choice":
                options = [o["value"] if isinstance(o, dict) else o for o in spec["options"]]
                if value not in options:
                    problems.append(t("input_not_option", id=input_id, options=", ".join(options)))
            elif spec["type"] == "language":
                if value not in languages.BY_CODE:
                    problems.append(t("input_not_language", id=input_id, value=value))
            elif spec["type"] == "provider":
                problem = self.provider_problem(value)
                if problem:
                    problems.append(f"{input_id}: {problem}")
            elif spec["type"] == "url" and spec.get("multiple"):  # one address per line
                from .nodes import url_lines
                from .urlfetch import url_problem
                lines = url_lines(value)
                if len(lines) > schema.MAX_URLS:
                    problems.append(t("input_too_many_urls", id=input_id, limit=schema.MAX_URLS))
                for line in lines:
                    problem = url_problem(line)
                    if problem:
                        problems.append(f"{input_id}: {problem}")
                value = "\n".join(lines)
            elif spec["type"] == "url":  # read by document.extract (urlfetch.py); the form only is checked here
                from .urlfetch import url_problem
                value = value.strip()
                problem = url_problem(value) if value else None
                if problem:
                    problems.append(f"{input_id}: {problem}")
            elif len(value) > schema.TEXT_LIMIT:
                problems.append(t("input_too_long", id=input_id))
            if required and not value.strip():
                problems.append(t("input_missing", id=input_id))
            inputs[input_id] = value
        return inputs, problems

    # --- control -----------------------------------------------------------------

    def resume(self, run_id: str, node: str | None = None) -> None:
        """Continues a run from the nodes that did not finish. node: retry only this failed node (and what follows it)."""
        run = self.get(run_id)
        wf = schema.parse(run["workflow_yaml"])
        states = {n: info["status"] for n, info in run["nodes"].items()}
        if self.is_active(run_id):
            raise RunError([t("run_active")])
        if node is not None:
            if states.get(node) not in BLOCKING_NODE:
                raise RunError([t("node_not_retryable", id=node)])
            reset = [node] + [n for n in wf.downstream(node) if states[n] in BLOCKING_NODE]
        else:
            # A finished run's skipped nodes are branches it did not take: nothing to resume.
            if run["status"] == "succeeded" or \
                    run["status"] not in RESUMABLE and not any(s in BLOCKING_NODE for s in states.values()):
                raise RunError([t("run_not_resumable", status=t("status_" + run["status"]))])
            reset = [n for n, s in states.items() if s in BLOCKING_NODE or s in ACTIVE_NODE]
        self.store.reset_nodes(run_id, reset)
        self.store.update_run(run_id, status="queued", cancel_requested=0, error=None, finished=None)
        self.store.event(run_id, node, "resumed", ", ".join(reset))
        self._launch(run_id)

    def cancel(self, run_id: str) -> None:
        """Asks the process that drives the run to stop it; a run that nobody drives is cancelled at once."""
        run = self.get(run_id)
        if run["status"] in FINISHED_RUN:
            raise RunError([t("run_finished_already", status=t("status_" + run["status"]))])
        self.store.update_run(run_id, cancel_requested=1)
        self.store.event(run_id, None, "cancel_requested")
        if not self.is_active(run_id):
            for node_id, info in run["nodes"].items():
                if info["status"] in ACTIVE_NODE | {"waiting_approval"}:
                    self.store.update_node(run_id, node_id, status="cancelled", finished=time.time())
            self.store.update_run(run_id, status="cancelled", finished=time.time())

    def decide(self, run_id: str, node_id: str, approve: bool, comment: str = "") -> None:
        """Approves or rejects a waiting approval node, then continues the run."""
        run = self.get(run_id)
        info = run["nodes"].get(node_id)
        if not info or info["status"] != "waiting_approval":
            raise RunError([t("node_not_waiting", id=node_id)])
        comment = str(comment or "")[:20_000]
        node_dir = self.run_dir(run_id) / "nodes" / node_id
        draft = node_dir / f"comment.{threading.get_ident()}.tmp"
        draft.write_text(comment, encoding="utf-8")
        outputs = {**info["outputs"], "comment": f"nodes/{node_id}/comment.md"}
        fields = {"status": "succeeded"} if approve else \
            {"status": "rejected", "error": t("rejected_with_comment", comment=comment) if comment else t("rejected_by_user")}
        # Two decisions at once (a double click, the interface and the command line): only the first one counts.
        if not self.store.change_node(run_id, node_id, "waiting_approval", outputs=outputs, comment=comment,
                                      finished=time.time(), **fields):
            draft.unlink(missing_ok=True)
            raise RunError([t("node_not_waiting", id=node_id)])
        paths.replace(draft, node_dir / "comment.md")
        self.store.event(run_id, node_id, "approved" if approve else "rejected", comment)
        if not self.is_active(run_id):
            self.store.update_run(run_id, status="queued", cancel_requested=0)
        self._launch(run_id)

    def wait(self, run_id: str, timeout: float | None = None, statuses=FINISHED_RUN | {"waiting_approval"}) -> str:
        """Waits until the run reaches one of the statuses (finished or waiting for a person). Returns the status."""
        end = time.time() + timeout if timeout else None
        while True:
            status = self.get(run_id)["status"]
            if status in statuses and not self.thread_alive(run_id):
                return status
            if end and time.time() > end:
                return status
            time.sleep(0.05)

    # --- reading -------------------------------------------------------------------

    def get(self, run_id: str) -> dict:
        self.run_dir(run_id)  # checks the form of the id
        run = self.store.run(run_id)
        if run is None or run.get("trashed_at"):
            raise RunError([t("run_not_found", id=run_id)])
        run["nodes"] = self.store.nodes(run_id)
        for info in run["nodes"].values():
            info["error_summary"] = error_summary(info.get("error"), info.get("error_key"))
        run["workflow_name"] = display_name(run["workflow_name"])
        if run["status"] == "running" and not self.is_active(run_id):
            # Nobody drives it. Either the driver ended normally between the read above and this check (it wrote
            # the result before it ended: read again), or its process died without finishing the run.
            if self.store.run(run_id)["status"] != "running" or self.is_active(run_id):
                return self.get(run_id)
            for node_id, info in run["nodes"].items():
                if info["status"] in ACTIVE_NODE:
                    self.store.update_node(run_id, node_id, status="interrupted")
                    info["status"] = "interrupted"
            self.store.update_run(run_id, status="interrupted")
            self.store.event(run_id, None, "interrupted")
            run["status"] = "interrupted"
        return run

    def list(self, before: str = "", *, matches=None) -> list[dict]:
        runs = self.store.runs(before=before, matches=matches)
        for run in runs:
            run["workflow_name"] = display_name(run["workflow_name"])
            if run["status"] == "running":
                detail = self.get(run["id"])
                run["status"] = detail["status"]
                run["waiting_quota"] = any(n["status"] == "waiting_quota" for n in detail["nodes"].values())
        return runs

    def _keep_awake(self) -> None:
        """Keeps the computer awake from the first run on. mehteran.common.system.keep_awake holds until this process ends,
        so it is called once, not per run."""
        with self._lock:
            if self.awake and not Engine._awake_started:
                Engine._awake_started = True
                system.keep_awake()

    def resume_interrupted(self) -> list[str]:
        """Resumes the runs that were running (or waiting for a usage limit) when the previous process ended. A run
        that another process drives is left alone. Returns the ids. They continue with their frozen settings."""
        resumed = []
        for run in self.store.runs(status="running"):
            if run["status"] != "running" or self.is_active(run["id"]):
                continue
            try:
                self.get(run["id"])  # records the interruption
                self.resume(run["id"])
                resumed.append(run["id"])
            except (RunError, ValueError, KeyError, OSError):
                continue
        return resumed

    def is_active(self, run_id: str) -> bool:
        return self.thread_alive(run_id) or system.is_locked(self.run_dir(run_id) / ".lock")

    def busy(self) -> bool:
        """True while a run of this process goes on (its thread is alive)."""
        return any(thread.is_alive() for thread in list(self._threads.values()))

    def thread_alive(self, run_id: str) -> bool:
        thread = self._threads.get(run_id)  # a thread that decided to end has removed itself already
        return bool(thread and thread.is_alive())

    # --- driving -------------------------------------------------------------------

    def _launch(self, run_id: str) -> None:
        with self._lock:
            if self.thread_alive(run_id):
                return  # that thread checks for new work under this lock before it ends (see _execute)
            thread = threading.Thread(target=self._execute, args=(run_id,), name=f"run-{run_id}", daemon=True)
            self._threads[run_id] = thread
            thread.start()
        self._keep_awake()

    def _execute(self, run_id: str) -> None:
        try:
            self._execute_passes(run_id)
        finally:
            with self._lock:
                if self._threads.get(run_id) is threading.current_thread():
                    self._threads.pop(run_id)

    def _execute_passes(self, run_id: str) -> None:
        lock_path = self.run_dir(run_id) / ".lock"
        i18n.set_request((self.store.run(run_id) or {}).get("lang"))
        while True:
            handle = open(lock_path, "a+")
            try:
                if not system.try_lock(handle):
                    return  # another process drives this run
                self._drive(run_id)
            except Exception as e:  # noqa: BLE001 - an engine error ends the run as failed, never silently
                self.store.update_run(run_id, status="failed", error=f"{type(e).__name__}: {e}", finished=time.time())
                self.store.event(run_id, None, "engine_error", f"{type(e).__name__}: {e}")
                return
            finally:
                handle.close()
            # An approval, rejection or cancel that arrived while this thread was finishing: continue with it.
            # Checked under the lock of _launch, and the thread leaves _threads there: a request either is seen
            # here, or finds no thread and starts a new one.
            with self._lock:
                if not self._has_more(run_id):
                    self._threads.pop(run_id, None)
                    return

    def _has_more(self, run_id: str) -> bool:
        run = self.store.run(run_id)
        if run is None or run["status"] in FINISHED_RUN:
            return False
        if run["cancel_requested"]:
            return True
        wf = schema.parse(run["workflow_yaml"])
        nodes = self.store.nodes(run_id)
        if run["status"] == "waiting_approval" and not any(i["status"] == "waiting_approval" for i in nodes.values()):
            return True  # the last approval was decided after the status was written
        return any(nodes[n]["status"] == "pending" and readiness(wf, nodes, n) != "wait" for n in wf.order)

    def _drive(self, run_id: str) -> None:
        run = self.store.run(run_id)
        wf = schema.parse(run["workflow_yaml"])
        self.store.update_run(run_id, status="running", started=run["started"] or time.time(), finished=None, error=None)
        cancel = threading.Event()
        slots = threading.BoundedSemaphore(self.parallel)  # model calls at once, also those of loop parts
        running: dict = {}
        with ThreadPoolExecutor(self.parallel, thread_name_prefix=f"node-{run_id}") as pool:
            while True:
                if not cancel.is_set() and self.store.cancel_requested(run_id):
                    cancel.set()
                nodes = self.store.nodes(run_id)
                if not cancel.is_set():
                    for node_id in wf.order:
                        if nodes[node_id]["status"] != "pending" or node_id in running.values():
                            continue
                        ready = readiness(wf, nodes, node_id)
                        if ready == "skip":
                            self.store.update_node(run_id, node_id, status="skipped", finished=time.time())
                            nodes[node_id]["status"] = "skipped"
                            continue
                        if ready == "wait":
                            continue
                        if wf.nodes[node_id]["type"] == "approval":
                            self._ask_approval(run, wf, node_id)
                            continue
                        self.store.update_node(run_id, node_id, status="running", started=time.time())
                        future = pool.submit(self._run_node, run, wf, node_id, cancel, slots)
                        running[future] = node_id
                if not running:
                    break
                done, _ = wait(list(running), timeout=0.2, return_when=FIRST_COMPLETED)
                for future in done:
                    node_id = running.pop(future)
                    error = future.exception()
                    if error is not None:  # a bug, not a node failure: record it on the node
                        self.store.update_node(run_id, node_id, status="failed", error=f"{type(error).__name__}: {error}",
                                               finished=time.time())
        self._finish(run_id, cancel.is_set())

    def _finish(self, run_id: str, cancelled: bool) -> None:
        nodes = self.store.nodes(run_id)
        states = {n: info["status"] for n, info in nodes.items()}
        failed = [n for n, s in states.items() if s in ("failed", "rejected")]
        if cancelled:
            for node_id, state in states.items():
                if state in ACTIVE_NODE | {"waiting_approval"}:
                    self.store.update_node(run_id, node_id, status="cancelled", finished=time.time())
            status, error = "cancelled", None
        elif all(s in ("succeeded", "skipped") for s in states.values()):  # skipped here: a branch not taken
            status, error = "succeeded", None
        elif failed:
            status = "failed"
            # Each node's error as stored (its key and values when it is a message of ours): shown in any language.
            error = t("run_failed_nodes", nodes=[
                [n, {"$key": nodes[n]["error_key"], "params": nodes[n]["error_params"] or {}} if nodes[n].get("error_key")
                 else error_summary(nodes[n]["error"])[:300]] for n in failed])
        elif "waiting_approval" in states.values():
            status, error = "waiting_approval", None
        else:
            status, error = "failed", t("run_stuck")
        finished = None if status == "waiting_approval" else time.time()
        self.store.update_run(run_id, status=status, error=error, finished=finished)
        self.store.event(run_id, None, status, error or "")
        try:
            self.write_manifest(run_id)
        except OSError as exc:
            self.store.event(run_id, None, "manifest_error", str(exc))

    def write_manifest(self, run_id: str) -> None:
        """Write a portable index of the saved workflow, input files and current node outputs."""
        run = self.store.run(run_id)
        folder = self.run_dir(run_id)
        nodes = self.store.nodes(run_id)
        files = {"workflow.yaml"}
        wf = schema.parse(run["workflow_yaml"])
        for name, spec in wf.inputs.items():
            if spec["type"] == "file":
                files.update(p for p in _as_list(run["inputs"].get(name)) if p)
        for node in nodes.values():
            files.update(node["outputs"].values())
        entries = []
        for rel in sorted(files):
            path = paths.inside(folder, rel)
            if path is None or not path.is_file():
                continue
            with path.open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            entries.append({"path": rel, "bytes": path.stat().st_size, "sha256": digest})
        data = {key: run[key] for key in ("id", "workflow_id", "created", "finished", "status", "providers")}
        data.update(schema_version=1, files=entries)
        tmp = folder / "manifest.json.tmp"
        try:
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            paths.replace(tmp, folder / "manifest.json")
        finally:
            tmp.unlink(missing_ok=True)

    def _ask_approval(self, run: dict, wf: schema.Workflow, node_id: str) -> None:
        node_dir = self.run_dir(run["id"]) / "nodes" / node_id
        node_dir.mkdir(parents=True, exist_ok=True)
        resolve = self._resolver(run, wf)
        show = (wf.nodes[node_id].get("config") or {}).get("show") or ""
        text = placeholders.render(show, resolve) if show.strip() else \
            "\n\n".join(x.strip() for x in (resolve(ref) for ref, _ in self._upstream(run, wf, node_id)) if x.strip())
        (node_dir / "text.md").write_text(text, encoding="utf-8", newline="\n")
        self.store.update_node(run["id"], node_id, status="waiting_approval", started=time.time(),
                               outputs={"text": f"nodes/{node_id}/text.md"})
        self.store.event(run["id"], node_id, "waiting_approval")

    def _resolver(self, run: dict, wf: schema.Workflow, wrap: bool = False):
        run_dir = self.run_dir(run["id"])
        nodes = self.store.nodes(run["id"])

        def value(ref: str) -> str:
            kind, ident, port = placeholders.parse(ref)
            if kind == "inputs":
                text = run["inputs"].get(ident, "")
                if wf.inputs[ident]["type"] == "file":
                    return "\n".join(str(run_dir / rel) for rel in _as_list(text) if rel)
                return text
            if nodes[ident]["status"] == "skipped" or (wf.nodes[ident]["type"] == "condition"
                                                        and port not in nodes[ident]["outputs"]):
                return ""  # a join: the branch that was not taken adds nothing
            rel = nodes[ident]["outputs"].get(port)
            if not rel:
                raise NodeError(t("output_missing", ref=ref))
            path = paths.inside(run_dir, rel)
            if path is None:
                raise NodeError(t("output_missing", ref=ref))
            if wf.ports(ident).get(port) == "file":
                return str(path)
            text = path.read_text(encoding="utf-8")
            return wrap_data(ref, text) if wrap else text
        return value

    def _upstream(self, run: dict, wf: schema.Workflow, node_id: str) -> list[tuple[str, str]]:
        """The text outputs connected to node_id, in connection order: [(reference, label)]. A connection from a
        whole node brings its "text" output."""
        out: list[tuple[str, str]] = []
        for source, port in wf.incoming(node_id):
            ports = wf.ports(source)
            names = [port] if port else (["text"] if "text" in ports else list(ports))
            label = i18n.localized(wf.nodes[source].get("label"), run["lang"]) or source
            for name in names:
                ref = f"nodes.{source}.{name}"
                if ports.get(name) == "text" and ref not in (r for r, _ in out):
                    out.append((ref, label))
        return out

    def _files(self, run: dict, wf: schema.Workflow):
        """A file reference -> (its files, whether the input takes several)."""
        run_dir = self.run_dir(run["id"])
        resolve = self._resolver(run, wf)

        def files(ref: str) -> tuple[list[Path], bool]:
            kind, ident, _ = placeholders.parse(ref)
            if kind == "inputs":
                return [run_dir / rel for rel in _as_list(run["inputs"].get(ident)) if rel], \
                    bool(wf.inputs[ident].get("multiple"))
            path = resolve(ref)
            return ([Path(path)] if path else []), False
        return files

    def _run_node(self, run: dict, wf: schema.Workflow, node_id: str, cancel: threading.Event,
                  slots: threading.Semaphore | None = None) -> None:
        run_id = run["id"]
        node = wf.nodes[node_id]
        node_type = REGISTRY[node["type"]]
        retries = node.get("retries", node_type.default_retries)
        timeout = step_timeout(node, node_type, run["provider_cfg"]["general"])
        general = run["provider_cfg"]["general"]
        node_dir = self.run_dir(run_id) / "nodes" / node_id
        error = ""
        attempt_no = 0
        quota_since = None
        waited = None  # the provider this step waited for last (stream P: known usage limits)
        log = node_dir / livelog.NAME
        saved = self.store.nodes(run_id)[node_id]
        wake_at = float(saved.get("quota_until") or 0)
        if wake_at > time.time():
            provider_before = run["providers"].get(node_id)
            until = time.strftime("%H:%M", time.localtime(wake_at))
            message = t("quota_waiting", time=until)
            self.store.update_node(run_id, node_id, status="waiting_quota", error=message)
            self.store.event(run_id, node_id, "quota_wait", message)
            while time.time() < wake_at and not cancel.wait(min(0.5, max(0.0, wake_at - time.time()))):
                if self.store.run(run_id)["providers"].get(node_id) != provider_before:
                    break
        while True:
            if cancel.is_set():
                self.store.update_node(run_id, node_id, status="cancelled", finished=time.time(), quota_until=None)
                return
            attempt = self.store.begin_attempt(run_id, node_id)
            fresh = self.store.run(run_id)  # the model may have been switched (switch, fallback_provider)
            provider = fresh["providers"].get(node_id, "")
            livelog.append(log, t("log_attempt", attempt=attempt, node=node_id) + (f" ({provider})" if provider else ""),
                           stamp=True)
            abort = threading.Event()
            ctx = Ctx(run_dir=self.run_dir(run_id), node_dir=node_dir, node_id=node_id, config=node.get("config") or {},
                      value=self._resolver(run, wf), wrapped=self._resolver(run, wf, wrap=True),
                      provider=provider, provider_cfg=fresh["provider_cfg"], abort=abort,
                      timeout=timeout, attempt=attempt, lang=run["lang"], files=self._files(run, wf), slots=slots,
                      progress=lambda message: (self.store.event(run_id, node_id, "progress", message),
                                                livelog.append(log, str(message), stamp=True)),
                      upstream=lambda: self._upstream(run, wf, node_id),
                      input_types={i: spec["type"] for i, spec in wf.inputs.items()},
                      several_urls=frozenset(i for i, spec in wf.inputs.items()
                                             if spec["type"] == "url" and spec.get("multiple")),
                      record=lambda name, started, outcome, until=None, message="": self.store.record_call(
                          run_id, node_id, name, started, outcome, until, message),
                      log=log,
                      # a usage limit known from another call blocks the provider without a call; not right after
                      # this step waited for it (the wait was for that limit)
                      blocked=None if waited == provider else
                      lambda name: self.known_limits((run_id, node_id)).get(name, 0))
            result: dict = {}

            def work():
                i18n.set_request(run["lang"])
                try:
                    result["outputs"] = node_type.run(ctx)
                except Aborted:
                    result["aborted"] = True
                except QuotaWait as e:
                    result["quota"] = e
                except NodeError as e:
                    result["error"] = i18n.message_of(e)
                except Exception as e:  # noqa: BLE001 - shown on the node
                    result["error"] = f"{type(e).__name__}: {e}"

            worker = threading.Thread(target=work, name=f"attempt-{node_id}", daemon=True)
            worker.start()
            # A loop applies the timeout to each model call itself; the whole node has no deadline.
            deadline = float("inf") if node_type.timeout_per_call else time.time() + timeout
            stopped = ""
            began = beat = time.time()
            while worker.is_alive():
                worker.join(0.05)
                if time.time() - beat >= self.heartbeat:  # the log shows that a long call is still alive
                    beat = time.time()
                    livelog.append(log, t("log_heartbeat", seconds=int(beat - began)), stamp=True)
                if worker.is_alive() and cancel.is_set():
                    stopped = "cancel"
                elif worker.is_alive() and time.time() > deadline:
                    stopped = "timeout"
                if stopped:
                    abort.set()
                    worker.join(10)
                    break
            if stopped == "cancel":
                self.store.update_node(run_id, node_id, status="cancelled", error=t("cancelled"), finished=time.time())
                self.store.event(run_id, node_id, "cancelled")
                return
            if stopped == "timeout":
                error = t("node_timeout", seconds=timeout)
            elif "outputs" in result:
                livelog.append(log, t("log_done", seconds=int(time.time() - began)), stamp=True)
                outputs = self._store_outputs(run_id, wf, node_id, node_dir, result["outputs"])
                self.store.update_node(run_id, node_id, status="succeeded", outputs=outputs, error=None, finished=time.time())
                self.store.event(run_id, node_id, "succeeded", t("event_attempt", attempt=attempt))
                return
            elif "quota" in result:
                # A usage limit: wait until it resets and try again; not counted as a failed attempt.
                limit = result["quota"]
                nxt = self._next_auto(fresh, node_id, provider, limit.until)
                if nxt:  # an `auto` step: the next model of the user's order that has no usage limit now
                    self._set_provider(run_id, node_id, nxt, auto=True)
                    quota_since = None
                    continue
                fallback = fresh["providers"].get(f"{node_id}:fallback")
                if fallback and fallback != provider:  # the workflow names another model for this case: no waiting
                    self._set_provider(run_id, node_id, fallback, auto=True)
                    quota_since = None
                    continue
                quota_since = quota_since or time.time()
                delay = self.quota_delay if self.quota_delay is not None else \
                    max(limit.until - time.time(), 30.0) if limit.until else general.get("quota_wait_minutes", 30) * 60
                if time.time() + delay - quota_since <= general.get("quota_max_hours", 24) * 3600:
                    until = time.strftime("%H:%M", time.localtime(time.time() + delay))
                    message = t("quota_waiting", time=until)
                    # The reason first, then the status: whoever sees "waiting_quota" finds why in the log.
                    livelog.append(log, str(t("quota_wait_event", time=until, error=limit)), stamp=True)
                    self.store.event(run_id, node_id, "quota_wait", t("quota_wait_event", time=until, error=limit))
                    self.store.update_node(run_id, node_id, status="waiting_quota", error=message, quota_until=time.time() + delay)
                    # Wait, but end the wait when the model of this node is switched (switch(), any process).
                    end = time.time() + delay
                    while time.time() < end and not cancel.wait(min(0.5, max(0.0, end - time.time()))):
                        if self.store.run(run_id)["providers"].get(node_id, "") != provider:
                            quota_since = None
                            break
                    else:
                        if not cancel.is_set():
                            self.store.event(run_id, node_id, "quota_resumed")
                            waited = provider
                    continue  # the loop top records a cancel
                error = t("quota_gave_up", hours=general.get("quota_max_hours", 24), error=limit)
            else:
                error = result.get("error") or t("cancelled")
            self.store.event(run_id, node_id, "attempt_failed", t("event_attempt_failed", attempt=attempt, error=error))
            if attempt_no >= retries or "quota" in result:
                break
            attempt_no += 1
            self.store.update_node(run_id, node_id, error=error)
            cancel.wait(self.retry_delay * attempt_no)  # the loop top records a cancel
        self.store.update_node(run_id, node_id, status="failed", error=error, finished=time.time())

    # --- switching the model of a step ------------------------------------------------

    def switch(self, run_id: str, node_id: str, provider: str) -> None:
        """Gives an AI step another model ("gemini/<model>"). A step waiting for a usage limit stops waiting and runs
        again at once (a loop keeps its finished parts); a failed, cancelled or interrupted one is retried."""
        run = self.get(run_id)
        wf = schema.parse(run["workflow_yaml"])
        if node_id not in wf.nodes or not isinstance((wf.nodes[node_id].get("config") or {}).get("provider"), str):
            raise RunError([t("node_no_model", id=node_id)])
        status = run["nodes"][node_id]["status"]
        if status not in ("waiting_quota", "failed", "interrupted", "cancelled"):
            raise RunError([t("node_not_switchable", id=node_id, status=t("status_" + status))])
        provider = str(provider or "").strip()
        provider = adapters.canonical(provider, self.provider_cfg["providers"])
        local_only = run["provider_cfg"].get("privacy") == "local" or wf.data.get("privacy") == "local"
        if provider in adapters.AUTO:
            provider = self.resolve_model("auto:local" if local_only else provider)
        problem = self.provider_problem(provider)
        if problem:
            raise RunError([problem])
        if local_only and not self.is_local(provider):
            raise RunError([t("privacy_refused", name=provider)])
        self._set_provider(run_id, node_id, provider, auto=False)
        if status != "waiting_quota":  # the waiting thread sees the switch by itself
            self.store.update_node(run_id, node_id, quota_until=None)
            self.resume(run_id, node_id)

    def _set_provider(self, run_id: str, node_id: str, provider: str, auto: bool) -> None:
        run = self.store.run(run_id)
        old = run["providers"].get(node_id, "")
        cfg = run["provider_cfg"]
        name = provider.partition("@")[0].partition("/")[0]
        if name not in cfg["providers"]:  # frozen with the run from now on, like the others
            cfg["providers"][name] = self.provider_cfg["providers"][name]
        self.store.update_run(run_id, providers=json.dumps({**run["providers"], node_id: provider}),
                              provider_cfg=json.dumps(cfg, ensure_ascii=False))
        message = t("event_switched_auto" if auto else "event_switched", old=old, new=provider)
        self.store.event(run_id, node_id, "provider_switched", message)
        livelog.append(self.run_dir(run_id) / "nodes" / node_id / livelog.NAME, str(message), stamp=True)

    # --- activity: what runs now -------------------------------------------------------

    def activity(self) -> list[dict]:
        """The runs that are running, queued or waiting, with what each of their nodes is doing."""
        out, now = [], time.time()
        for run in self.list():
            if run["status"] not in ("running", "queued", "waiting_approval"):
                continue
            nodes = self.store.nodes(run["id"])
            progress = {}
            for event in self.store.events(run["id"], limit=100):
                if event["kind"] == "progress":
                    progress[event["node_id"]] = event["text"]
            busy = [{"id": n, "status": info["status"], "started": info["started"],
                     "elapsed": round(now - info["started"], 1) if info["started"] else None,
                     "waiting_reason": info["error"] if info["status"] in ("waiting_quota", "waiting_approval") else None,
                     "progress": progress.get(n), "attempts": info["attempts"]}
                    for n, info in nodes.items() if info["status"] in ("running", "waiting_quota", "waiting_approval")]
            out.append({"id": run["id"], "workflow_name": run["workflow_name"], "status": run["status"],
                        "started": run["started"], "elapsed": round(now - run["started"], 1) if run["started"] else None,
                        "done": sum(info["status"] in ("succeeded", "skipped") for info in nodes.values()),
                        "total": len(nodes), "nodes": busy,
                        "waiting_quota": any(n["status"] == "waiting_quota" for n in busy)})
        return out

    def node_log(self, run_id: str, node_id: str, offset: int = 0) -> dict:
        """A piece of a node's live log from offset (bytes): {text, offset, done, size}."""
        run = self.get(run_id)
        if node_id not in run["nodes"]:
            raise RunError([t("unknown_node", id=node_id)])
        path = self.run_dir(run_id) / "nodes" / node_id / livelog.NAME
        text, next_offset = livelog.read(path, offset)
        status = run["nodes"][node_id]["status"]
        size = path.stat().st_size if path.exists() else 0
        done = status not in ("pending", "running", "waiting_quota") and next_offset >= size
        return {"text": text, "offset": next_offset, "size": size, "done": done, "status": status}

    def _store_outputs(self, run_id: str, wf: schema.Workflow, node_id: str, node_dir: Path, outputs: dict) -> dict:
        node_dir.mkdir(parents=True, exist_ok=True)
        run_dir = self.run_dir(run_id)
        stored = {}
        for port, kind in wf.ports(node_id).items():
            value = outputs.get(port)
            if value is None:
                continue
            if kind == "text":
                path = node_dir / f"{port}.md"
                tmp = path.with_name(path.name + ".tmp")
                tmp.write_text(str(value), encoding="utf-8", newline="\n")
                paths.replace(tmp, path)
            else:
                path = Path(value)
            stored[port] = path.resolve().relative_to(run_dir.resolve()).as_posix()
        return stored

    # --- files -----------------------------------------------------------------------

    def artifact(self, run_id: str, rel: str) -> Path:
        """A file of the run folder by its relative path; never a path outside it, never the lock file."""
        run_dir = self.run_dir(run_id)
        path = paths.inside(run_dir, rel)
        if path is None or not path.is_file() or path.name == ".lock" or path.name.endswith(".job.json"):
            raise RunError([t("file_not_found")])
        return path

    def artifacts(self, run_id: str) -> list[dict]:
        run_dir = self.run_dir(run_id)
        out = []
        for path in sorted(run_dir.rglob("*")):
            if path.is_file() and path.name != ".lock" and not path.name.endswith((".job.json", ".tmp")):
                out.append({"path": path.relative_to(run_dir).as_posix(), "size": path.stat().st_size})
        return out


def _as_list(value) -> list:
    """A file input's value: one path, a list of paths, or nothing."""
    if value is None or value == "":
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def engine_options(home: Path) -> dict:
    import tomllib
    try:
        with (home / "configurations" / "engine.toml").open("rb") as f:
            return tomllib.load(f)
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def resume_on_start(home: Path | None = None) -> bool:
    """Whether the server automatically resumes work left by an earlier process."""
    return engine_options(home if home is not None else paths.home()).get("resume_interrupted") is True


_FRAME = re.compile(r"^\s+|^(Traceback \(most recent call last\)|During handling|The above exception|\^+$)")


def error_summary(error: str | None, key: str | None = None) -> str:
    """One line for an error that a tool wrote: its last meaningful line (not a traceback frame). A message of ours
    (it has a key) and a one-line error are returned as they are. The full text stays in `error`."""
    text = (error or "").strip()
    if key or "\n" not in text:
        return text
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    meaningful = [line for line in lines if not _FRAME.match(line)]
    return (meaningful or lines)[-1][:300]


def display_name(stored: str) -> str:
    """The workflow name of a run (stored as written: a text or a {tr, en} map) in the current language."""
    try:
        return i18n.localized(json.loads(stored))
    except ValueError:
        return stored


def safe_filename(name: str) -> str:
    """A file name without folders, control characters or characters that Windows does not allow."""
    name = Path(name.replace("\\", "/")).name
    name = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "_", name).strip(" .")
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    stem = stem[:100] or "file"
    if stem.upper().split(".")[0] in {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
                                      *(f"LPT{i}" for i in range(1, 10))}:
        stem = "_" + stem
    return f"{stem}.{ext[:10]}" if ext else stem
