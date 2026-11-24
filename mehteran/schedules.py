"""Scheduled runs: a workflow that starts by itself at set times, with the inputs saved in the schedule.

- A schedule: {id, name, template ("builtin:<id>" or "user:<id>"), values, every_step, privacy, output_dir, lang,
  rule, enabled, created, next_at, last_at, last_run, last_error}, kept in <data>/configurations/schedules.json.
- A rule: {"days": [0..6] (0 is Monday), "time": "HH:MM"} in local time, or {"every_hours": 1..168}.
- The Scheduler thread of the web server starts a schedule's run when its time has come. Times that passed while
  Mehteran was closed start one run when it opens again, not one per missed time. While the schedule's last run is
  still queued or running, the time is skipped. A run that waits for an approval does not hold up the next one.
- New schedules keep their workflow YAML. At startup, older schedules acquire a snapshot when one is available.
- File inputs cannot be scheduled: a schedule keeps only text values.
- A desktop notification tells when a scheduled run waits for an approval, succeeded or failed (notify()).
"""

from __future__ import annotations

import json
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

from . import i18n, paths, schema, templates
from .engine import RunError
from .i18n import t

MAX_SCHEDULES = 50
NAME_LIMIT = 120
TICK = 20  # seconds between two checks of the Scheduler thread
TIME_RE = re.compile(r"([01]\d|2[0-3]):([0-5]\d)")
NOTIFY = {"waiting_approval": "notify_approval", "succeeded": "notify_succeeded", "failed": "notify_failed",
          "interrupted": "notify_failed"}
_lock = threading.Lock()  # the HTTP threads and the Scheduler thread change the same file


def _file(home: Path) -> Path:
    return Path(home) / "configurations" / "schedules.json"


def load(home: Path) -> list[dict]:
    try:
        data = json.loads(_file(home).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    return [s for s in data.get("schedules") or [] if isinstance(s, dict) and s.get("id")] if isinstance(data, dict) else []


def _save(home: Path, items: list[dict]) -> None:
    target = _file(home)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps({"schedules": items}, ensure_ascii=False, indent=1), encoding="utf-8")
    paths.replace(tmp, target)


def _change(home: Path, schedule_id: str, fn) -> dict:
    """fn(schedule) changes one schedule in place, under the lock. Returns the changed schedule."""
    with _lock:
        items = load(home)
        found = next((s for s in items if s["id"] == schedule_id), None)
        if found is None:
            raise RunError([t("schedule_not_found", id=schedule_id)])
        fn(found)
        _save(home, items)
        return found


# --- rules ---------------------------------------------------------------------------------------------------

def clean_rule(rule) -> dict:
    if not isinstance(rule, dict):
        raise RunError([t("schedule_bad_rule")])
    if "every_hours" in rule:
        hours = rule["every_hours"]
        if not isinstance(hours, int) or isinstance(hours, bool) or not 1 <= hours <= 168:
            raise RunError([t("schedule_bad_rule")])
        return {"every_hours": hours}
    days, at = rule.get("days"), str(rule.get("time") or "")
    if not isinstance(days, list) or not days or not all(isinstance(d, int) and not isinstance(d, bool) and 0 <= d <= 6
                                                         for d in days) or not TIME_RE.fullmatch(at):
        raise RunError([t("schedule_bad_rule")])
    return {"days": sorted(set(days)), "time": at}


def next_time(rule: dict, after: float) -> float:
    """The first time after `after` (epoch seconds) that the rule names."""
    if "every_hours" in rule:
        return after + rule["every_hours"] * 3600
    hour, minute = map(int, rule["time"].split(":"))
    start = datetime.fromtimestamp(after)
    for offset in range(8):
        day = start + timedelta(days=offset)
        moment = day.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if moment.weekday() in rule["days"] and moment.timestamp() > after:
            return moment.timestamp()
    raise AssertionError("a rule with days always has a time within 8 days")


# --- the schedules -------------------------------------------------------------------------------------------

def _workflow(ref: str, home: Path) -> tuple[str, str]:
    source, template_id = templates.resolve(ref, home)
    return templates.read(source, template_id, home), f"{source}:{template_id}"


def pin_legacy_schedules(engine) -> None:
    """Prefer a schedule's own last executed version, then its current template."""
    with _lock:
        items = load(engine.home)
        changed = False
        for item in items:
            if "workflow_yaml" in item:
                continue
            prior = engine.store.run(item["last_run"]) if item.get("last_run") else None
            try:
                text = prior["workflow_yaml"] if prior and prior.get("schedule") == item["id"] else \
                    _workflow(item["template"], engine.home)[0]
                _check_inputs(engine, text, item.get("values") or {})
            except (RunError, templates.TemplateError, schema.WorkflowError):
                continue
            item["workflow_yaml"] = text
            changed = True
        if changed:
            _save(engine.home, items)


def _check_inputs(engine, text: str, values: dict) -> None:
    wf = schema.parse(text)
    if any(spec["type"] == "file" and spec.get("required", True) for spec in wf.inputs.values()):
        raise RunError([t("schedule_needs_files")])
    _, problems = engine._inputs(wf, values, {})
    if problems:
        raise RunError(problems)


def create(engine, ref: str, values: dict, rule, name: str = "", every_step: str = "", privacy: str = "",
           output_dir: str | None = None) -> dict:
    home = engine.home
    text, ref = _workflow(ref, home)
    values = {str(k): v for k, v in (values or {}).items()}
    _check_inputs(engine, text, values)
    engine.unattended_check(text, values, privacy, every_step)  # its models, as at its time
    rule = clean_rule(rule)
    name = " ".join(str(name or "").split())
    if len(name) > NAME_LIMIT:
        raise RunError([t("label_too_long", limit=NAME_LIMIT)])
    now = time.time()
    item = {"id": secrets.token_hex(6), "name": name or i18n.localized(schema.parse(text).data.get("name")) or ref,
            "template": ref, "workflow_yaml": text, "values": values, "every_step": every_step or "", "privacy": privacy or "",
            "output_dir": output_dir, "lang": i18n.current(), "rule": rule, "enabled": True, "created": now,
            "next_at": next_time(rule, now), "last_at": None, "last_run": None, "last_error": None}
    with _lock:
        items = load(home)
        if len(items) >= MAX_SCHEDULES:
            raise RunError([t("schedule_too_many", limit=MAX_SCHEDULES)])
        _save(home, [*items, item])
    return item


def update(home: Path, schedule_id: str, changes: dict) -> dict:
    rule = clean_rule(changes["rule"]) if "rule" in changes else None
    name = " ".join(str(changes.get("name") or "").split()) if "name" in changes else None
    if name is not None and (not name or len(name) > NAME_LIMIT):
        raise RunError([t("label_too_long", limit=NAME_LIMIT)])

    def apply(item: dict) -> None:
        if "enabled" in changes:
            item["enabled"] = changes["enabled"] is True
        if rule is not None:
            item["rule"] = rule
        if name is not None:
            item["name"] = name
        if rule is not None or (item["enabled"] and "enabled" in changes):
            item["next_at"] = next_time(item["rule"], time.time())  # turned on again: from now, no missed times
    return _change(home, schedule_id, apply)


def delete(home: Path, schedule_id: str) -> None:
    with _lock:
        items = load(home)
        if not any(s["id"] == schedule_id for s in items):
            raise RunError([t("schedule_not_found", id=schedule_id)])
        _save(home, [s for s in items if s["id"] != schedule_id])


def listing(engine) -> list[dict]:
    """The schedules with the status of each one's last run."""
    out = []
    for item in load(engine.home):
        run = engine.store.run(item["last_run"]) if item.get("last_run") else None
        out.append({**{key: value for key, value in item.items() if key != "workflow_yaml"},
                    "last_status": run["status"] if run else None})
    return out


def start(engine, item: dict, kick=None) -> str:
    """One run of a schedule, now. kick: the Automation's, for a run that saves its results to a folder."""
    previous = getattr(i18n._local, "lang", None)  # the request's own language, or None (not the default)
    i18n.set_request(item.get("lang"))
    try:
        ref = item["template"]
        text = item.get("workflow_yaml")
        if text is None:
            text, ref = _workflow(ref, engine.home)
        _check_inputs(engine, text, item.get("values") or {})
        run_id = engine.start(text, item.get("values") or {}, {}, template=ref, launch=False,
                              privacy=item.get("privacy") or "", every_step=item.get("every_step") or "", unattended=True)
    finally:
        i18n.set_request(previous)
    engine.store.update_run(run_id, schedule=item["id"], output_dir=item.get("output_dir"))
    engine.launch(run_id)
    if item.get("output_dir") and kick:
        kick()
    return run_id


def run_now(engine, schedule_id: str, kick=None) -> str:
    item = next((s for s in load(engine.home) if s["id"] == schedule_id), None)
    if item is None:
        raise RunError([t("schedule_not_found", id=schedule_id)])
    run_id = start(engine, item, kick)
    _change(engine.home, schedule_id, lambda s: s.update(last_at=time.time(), last_run=run_id, last_error=None))
    return run_id


# --- the thread of the web server ----------------------------------------------------------------------------

class Scheduler:
    def __init__(self, engine, kick=None, notify_fn=None, maintenance=None):
        self.engine = engine
        self.kick = kick
        self.notify = notify_fn or notify
        self.wake = threading.Event()
        self.stopping = threading.Event()
        self.maintenance = maintenance
        self.next_maintenance = 0.0
        self.thread: threading.Thread | None = None

    def begin(self) -> None:
        self.thread = threading.Thread(target=self._loop, name="mehteran-scheduler", daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.stopping.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=2)

    def _loop(self) -> None:
        while not self.stopping.is_set():
            try:
                self.tick()
                if self.maintenance and time.monotonic() >= self.next_maintenance:
                    self.next_maintenance = time.monotonic() + 86400
                    self.maintenance()
            except Exception as e:  # noqa: BLE001 - the thread must not die; shown in the terminal (or the log)
                print(f"[mehteran scheduler] {type(e).__name__}: {e}", flush=True)
            self.wake.wait(TICK)
            self.wake.clear()

    def tick(self, now: float | None = None) -> list[str]:
        """Starts the schedules whose time has come and sends the notifications. Returns the started run ids."""
        now = time.time() if now is None else now
        started = []
        for item in load(self.engine.home):
            if not item.get("enabled") or (item.get("next_at") or 0) > now:
                continue
            result: dict = {"last_at": now, "next_at": next_time(item["rule"], now)}
            last = self.engine.store.run(item["last_run"]) if item.get("last_run") else None
            if last and last["status"] in ("queued", "running"):
                result["last_error"] = t("schedule_skipped_busy")
            else:
                try:
                    result.update(last_run=start(self.engine, item, self.kick), last_error=None)
                    started.append(result["last_run"])
                except (RunError, templates.TemplateError, schema.WorkflowError) as e:
                    messages = e.messages() if isinstance(e, schema.WorkflowError) else e.messages
                    result["last_error"] = str(messages[0]) if messages else str(e)
                    self.notify("Mehteran", t("notify_not_started", name=item["name"], error=result["last_error"]))
            try:
                _change(self.engine.home, item["id"], lambda s, r=result: s.update(r))
            except RunError:
                pass  # deleted meanwhile
        self._notifications()
        return started

    def _notifications(self) -> None:
        store = self.engine.store
        marks = ",".join("?" * len(NOTIFY))
        names = None
        for row in store._rows(f"SELECT id, status, schedule, notified FROM runs WHERE schedule IS NOT NULL "
                               f"AND status IN ({marks}) AND (notified IS NULL OR notified != status)", tuple(NOTIFY)):
            names = names if names is not None else {s["id"]: s["name"] for s in load(self.engine.home)}
            store.update_run(row["id"], notified=row["status"])
            self.notify("Mehteran", t(NOTIFY[row["status"]], name=names.get(row["schedule"]) or row["id"]))


def notify(title: str, text: str) -> None:
    """A desktop notification (macOS: Notification Center, Linux: notify-send). Nothing elsewhere or on error.
    The texts go as arguments, never inside a script."""
    text, title = text[:300], title[:80]
    try:
        if sys.platform == "darwin":
            subprocess.run(["osascript", "-e", "on run argv", "-e",
                            "display notification (item 1 of argv) with title (item 2 of argv)", "-e", "end run",
                            text, title], timeout=10, capture_output=True)
        elif sys.platform.startswith("linux") and shutil.which("notify-send"):
            subprocess.run(["notify-send", "--app-name=Mehteran", "--", title, text], timeout=10, capture_output=True)
    except (OSError, subprocess.SubprocessError):
        pass

