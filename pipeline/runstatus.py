"""Live status of a run, written to books/<book>/work/run.json so that the web interface can show it.

Also keeps the last quota event of each provider in .jobs/quota.json (shown on the Setup tab).
All methods do nothing until start() is called, so the pipeline also works without a status file.
"""

from __future__ import annotations

import threading
import time
from pathlib import Path

from .core import read_json, write_json


class RunStatus:
    def __init__(self):
        self.path: Path | None = None
        self.quota_path: Path | None = None
        self.data: dict = {}
        self.lock = threading.Lock()
        self.local = threading.local()
        self.stopping = False
        self._written = 0.0

    # --- life cycle ---
    def start(self, path: Path, quota_path: Path, **info) -> None:
        with self.lock:
            self.path, self.quota_path = path, quota_path
            self.data = {"state": "running", "started": time.time(), "finished": None, "stage": None,
                         "stages": {}, "durations": {}, "quota": {}, "quota_events": [], "failures": [],
                         "error": None, **info}
            self._write(force=True)

    def finish(self, state: str, error: str | None = None) -> None:
        with self.lock:
            if not self.path:
                return
            self.data.update(state=state, error=error, finished=time.time(), quota={})
            self._write(force=True)

    def update(self, **info) -> None:
        with self.lock:
            self.data.update(info)
            self._write(force=True)

    # --- stages and tasks ---
    def stage(self, name: str, total: int) -> None:
        with self.lock:
            self.data["stage"] = name
            self.data["stages"][name] = {"done": 0, "failed": 0, "total": total}
            self._write(force=True)

    def set_thread_stage(self, name: str) -> None:
        self.local.stage = name

    def task_done(self, stage: str, name: str, error: str | None = None) -> None:
        with self.lock:
            entry = self.data.get("stages", {}).get(stage)
            if entry is not None:
                entry["failed" if error else "done"] += 1
            if error:
                self.data["failures"] = (self.data["failures"] + [{"stage": stage, "task": name, "error": error[:400]}])[-50:]
            self._write()

    def call_finished(self, seconds: float) -> None:
        """Duration of one successful model call, recorded under the stage of the calling thread."""
        stage = getattr(self.local, "stage", None)
        if not stage:
            return
        with self.lock:
            count, total = self.data.setdefault("durations", {}).get(stage, [0, 0.0])
            self.data["durations"][stage] = [count + 1, total + seconds]
            self._write()

    # --- quota ---
    def quota_wait(self, provider: str, until: float, message: str) -> None:
        with self.lock:
            event = {"provider": provider, "until": until, "since": time.time(), "message": message[:300]}
            known = self.data.get("quota", {}).get(provider)
            if known and known.get("until") == until:
                return  # another thread reported the same wait
            self.data.setdefault("quota", {})[provider] = event
            self.data["quota_events"] = (self.data.get("quota_events", []) + [event])[-20:]
            if self.path:
                self.data["state"] = "waiting_quota"
            self._write(force=True)
            self._write_quota(provider, event)

    def quota_clear(self, provider: str) -> None:
        with self.lock:
            if provider not in self.data.get("quota", {}):
                return
            del self.data["quota"][provider]
            if not self.data["quota"] and self.data.get("state") == "waiting_quota":
                self.data["state"] = "running"
            self._write(force=True)
            self._write_quota(provider, {"cleared": time.time()})

    # --- files ---
    def _write(self, force: bool = False) -> None:
        if not self.path or (not force and time.time() - self._written < 1.0):
            return
        self.data["updated"] = time.time()
        write_json(self.path, self.data)
        self._written = time.time()

    def _write_quota(self, provider: str, event: dict) -> None:
        if not self.quota_path:
            return
        known = read_json(self.quota_path, {})
        known[provider] = {**known.get(provider, {}), **event}
        write_json(self.quota_path, known)


STATUS = RunStatus()
