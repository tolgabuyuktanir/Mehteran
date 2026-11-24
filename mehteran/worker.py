"""One model call in its own process: python -m mehteran.worker <job.json>

The engine starts this process for each ai.cli attempt, so that a cancel or a timeout can stop it together with
the command-line tool it started. An adapter's tool (mehteran/providers/) gets the prompt on stdin, in an empty
temporary folder, and its stdout goes to the node's live log as it arrives (mehteran/toolstream.py). A provider that
is given by its command (MEHTERAN_CONFIG, config.toml) runs through mehteran.common.calls.call_command. The
environment has no API key that would bill an account, unless the user allowed it (nodes.call_worker).
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from pathlib import Path

from mehteran import livelog, toolstream
from mehteran import providers as adapters
from mehteran.providers import base


def _write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8", newline="\n")
    os.replace(tmp, path)


def _end_with_parent() -> None:
    """If the engine process dies (killed, or the terminal closed), this process and the tool it started end too;
    otherwise the tool would go on using the account's quota for an answer that nobody reads. POSIX only: there
    this process leads its own process group (see mehteran.common.system.new_process_group)."""
    if os.name != "posix":
        return
    parent = os.getppid()

    def watch() -> None:
        while os.getppid() == parent:
            time.sleep(1)
        os.killpg(os.getpgrp(), signal.SIGKILL)

    threading.Thread(target=watch, daemon=True).start()


def main(job_file: str) -> int:
    _end_with_parent()
    job = json.loads(Path(job_file).read_text(encoding="utf-8"))
    root = Path(job["root"])
    from mehteran import i18n
    from mehteran.common import calls, tools
    i18n.set_default(job.get("lang"))
    tools.extend_path(root)
    prompt = Path(job["prompt"]).read_text(encoding="utf-8")
    log = Path(job["log"]) if job.get("log") else None
    prefix = f"{job['label']}: " if job.get("label") else ""
    provider, _, model = job["name"].partition("@")[0].partition("/")
    spec = job["cfg"]["providers"].get(provider) or {}
    if spec.get("api") == "ollama":  # a local model: Ollama's HTTP API on 127.0.0.1, no command-line tool
        from mehteran import i18n as messages
        from mehteran import ollama
        from mehteran.settings import SYSTEM_PROMPT
        messages.set_default(job.get("lang"))
        try:
            if not (model or spec.get("model")):
                raise ollama.OllamaError(messages.t("ollama_choose_model"))
            if log:
                livelog.append(log, f"{prefix}--- {job['name']} ---\n")
            answer = ollama.chat(model or spec["model"], prompt, SYSTEM_PROMPT, job["timeout"], spec.get("options"),
                                 on_text=(lambda piece: livelog.append(log, piece)) if log else None)  # as it streams
            if log:
                livelog.append(log, "\n")
        except ollama.OllamaError as e:
            _write(Path(job["error"]), str(e))
            return 1
        _write(Path(job["answer"]), answer)
        return 0
    if spec.get("adapter") == "openai-local":  # a local server with an OpenAI-compatible API, on 127.0.0.1
        return _local_server_call(job, spec, prompt, log, prefix, model)
    if spec.get("adapter") in adapters.ADAPTERS:  # one of Mehteran's own adapters (mehteran/providers/)
        return _adapter_call(job, spec, prompt, log, prefix)
    # A provider given by its command. One attempt and no waiting for a usage limit here: the engine counts attempts,
    # applies the timeout and waits for a usage limit itself (it can be cancelled meanwhile).
    if log:
        livelog.append(log, f"{prefix}--- {job['name']}: {' '.join(Path(a).name for a in spec.get('command', [])[:1])} ---\n")
    try:
        if not spec.get("command"):
            raise calls.CommandError(i18n.t("provider_not_configured", name=provider))
        answer = calls.call_command(provider, spec, model, job["name"].partition("@")[2], prompt, job["timeout"],
                                    job["cfg"]["general"].get("quota_wait_minutes", 30) * 60)
    except calls.QuotaError as e:
        _write(Path(job["error"]), str(e))
        if job.get("quota"):
            _write(Path(job["quota"]), json.dumps({"until": e.until}))
        return 1
    except calls.CommandError as e:
        _write(Path(job["error"]), str(e))
        return 1
    except Exception as e:  # noqa: BLE001 - reported to the engine as the node's error
        _write(Path(job["error"]), f"{type(e).__name__}: {e}")
        return 1
    _write(Path(job["answer"]), answer)
    if log:
        livelog.append(log, answer.rstrip() + "\n")
    return 0


def _local_server_call(job: dict, spec: dict, prompt: str, log: Path | None, prefix: str, model: str) -> int:
    """One call to the local OpenAI-compatible server; its text streams into the live log."""
    adapter = adapters.ADAPTERS["openai-local"]
    if log:
        livelog.append(log, f"{prefix}--- {job['name']} ---\n")
    try:
        answer = adapter.chat(spec.get("url", ""), model or spec.get("model", ""), prompt, base.SYSTEM_PROMPT,
                              job["timeout"], on_text=(lambda piece: livelog.append(log, piece)) if log else None)
    except base.UsageLimit as e:
        _write(Path(job["error"]), str(e))
        if job.get("quota"):
            _write(Path(job["quota"]), json.dumps({"until": e.until}))
        return 1
    except base.CallError as e:
        _write(Path(job["error"]), str(e))
        return 1
    if log:
        livelog.append(log, "\n")
    _write(Path(job["answer"]), answer)
    return 0


def _agent(job: dict, log: Path | None, prefix: str) -> dict | None:
    """An agent step's browser (job["agent"]: mcp_file, tools, hosts): the guard stops the step when it leaves its
    sites, and writes each browser action to the live log."""
    spec = job.get("agent")
    if not spec:
        return None
    from mehteran import browser
    check = browser.guard(spec["hosts"])

    def guard(line: str) -> str | None:
        stop, action = check(line)
        if action and log:
            livelog.append(log, "".join(f"{prefix}» {a}\n" for a in action.splitlines()), stamp=True)
        return stop
    return {"mcp_file": spec["mcp_file"], "tools": spec["tools"], "guard": guard}


def _adapter_call(job: dict, spec: dict, prompt: str, log: Path | None, prefix: str) -> int:
    """One call through an adapter: the tool's output goes to the live log as it arrives (toolstream.py)."""
    from mehteran import usage
    from mehteran.i18n import t
    adapter = adapters.ADAPTERS[spec["adapter"]]
    provider, model, effort = adapters.split(job["name"])
    if log:
        livelog.append(log, f"{prefix}--- {job['name']}: {adapter.program} ---\n")
    live = toolstream.LiveOutput(log, [], prefix, stream_json=adapter.stream_json) if log else None
    shown, stdout = "", ""
    try:
        answer, stdout = base.run(adapter, spec, model, effort, prompt, job["timeout"], live.feed if live else None,
                                  default_wait=job["cfg"]["general"].get("quota_wait_minutes", 30) * 60,
                                  agent=_agent(job, log, prefix))
    except base.UsageLimit as e:
        _write(Path(job["error"]), t("quota_hit", name=provider, time=time.strftime("%H:%M", time.localtime(e.until))))
        if job.get("quota"):
            _write(Path(job["quota"]), json.dumps({"until": e.until}))
        return 1
    except base.CallError as e:
        _write(Path(job["error"]), str(e))
        return 1
    except Exception as e:  # noqa: BLE001 - reported to the engine as the node's error
        _write(Path(job["error"]), f"{type(e).__name__}: {e}")
        return 1
    finally:
        if live:
            shown = live.close()
    seen = adapter.usage_seen(stdout)
    if seen and job.get("home"):  # the tool's own usage report (Claude Code's rate_limit_event), for the usage page
        usage.remember(Path(job["home"]), adapter.id, seen)
    _write(Path(job["answer"]), answer)
    if log and not toolstream.same_text(shown, answer):  # the answer was not shown while the tool ran
        livelog.append(log, answer.rstrip() + "\n")
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
