"""One model call in its own process: python -m mehteran.worker <job.json>

The engine starts this process for each ai.cli attempt, so that a cancel or a timeout can stop it together with
the command-line tool it started. The call itself is pipeline.providers.run (used read-only): the prompt goes on
stdin to the tool, in an empty temporary folder.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from pathlib import Path

from mehteran import livelog


def _write(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def _end_with_parent() -> None:
    """If the engine process dies (killed, or the terminal closed), this process and the tool it started end too;
    otherwise the tool would go on using the account's quota for an answer that nobody reads. POSIX only: there
    this process leads its own process group (see pipeline.system.new_process_group)."""
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
    sys.path.insert(0, str(root))
    from pipeline import i18n, providers, tools
    from pipeline.core import PipelineError, Project
    i18n.set_default(job.get("lang"))
    tools.extend_path(root)
    proj = Project(root, job["cfg"])
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
    if log:  # the translation app's provider code returns the answer at the end; nothing streams before that
        livelog.append(log, f"{prefix}--- {job['name']}: {' '.join(Path(a).name for a in spec.get('command', [])[:1])} ---\n")
    try:
        # One attempt and no waiting for a usage limit here: the engine counts attempts, applies the timeout and
        # waits for a usage limit itself (it can be cancelled meanwhile). The translation app detects the limit.
        answer = providers.run(proj, job["name"], prompt, wait_for_quota=False, attempts=1, timeout=job["timeout"])
    except providers.QuotaError as e:
        _write(Path(job["error"]), str(e))
        if job.get("quota"):
            _write(Path(job["quota"]), json.dumps({"until": e.until}))
        return 1
    except PipelineError as e:
        _write(Path(job["error"]), str(e))
        return 1
    except Exception as e:  # noqa: BLE001 - reported to the engine as the node's error
        _write(Path(job["error"]), f"{type(e).__name__}: {e}")
        return 1
    _write(Path(job["answer"]), answer)
    if log:
        livelog.append(log, answer.rstrip() + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
