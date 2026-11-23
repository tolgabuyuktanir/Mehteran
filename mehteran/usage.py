"""Usage of the AI tools: Mehteran's own count of its model calls, what the tools themselves report, and the usage
limits that the translation app met.

- Own counts: every model call of a run is a row of the calls table (store.py): provider, model, start, seconds,
  outcome (ok, failed, quota, aborted) and, for a usage limit, until when. Counted per provider and model, today,
  in the last 5 hours and in the last 7 days.
- What the tools report (only what they write themselves; no credentials file is read; None when unknown):
  - Codex writes its rate limits (used percent of the 5-hour and the weekly window, reset times, plan) into its session
    logs, ~/.codex/sessions/**/rollout-*.jsonl ($CODEX_HOME). The newest entry is shown with the time it was written.
    Mehteran's own Codex calls are --ephemeral (the translation app's command) and write no session log, so the value
    is from the last interactive Codex use.
  - Claude Code answers "/usage" in print mode without a model call (claude_usage: the used percent of the session
    window, of the week, and of the week of one model, with the reset times). Mehteran asks again in the background
    when its last answer is older than STALE_SECONDS (refresh_stale), so the remaining usage is always on screen.
    Claude Code also reports a "rate_limit_event" in its stream-json output: every call of a run updates the value.
    A Claude Code that does not answer "/usage" is asked with one very short model call, only when the user asks
    (probe_claude). Kept in configurations/usage.json.
  - Gemini CLI and Antigravity CLI report token counts per answer, but no limits: None.
- The translation app's usage limits: <code folder>/.jobs/quota.json (read only), and the last limit met by a model
  test on the Setup tab: <data>/configurations/quota.json.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import threading
import time
from pathlib import Path

from . import paths

WINDOWS = {"today": None, "5h": 5 * 3600, "7d": 7 * 86400}
STALE_SECONDS = 300  # a tool's own report older than this is asked again (only where asking costs nothing)
TOOL_OF = {"claude": "claude", "codex": "codex", "gemini": "gemini", "agy": "antigravity"}


def _read_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _count() -> dict:
    return {"calls": 0, "ok": 0, "failed": 0, "quota": 0, "aborted": 0, "seconds": 0.0}


def _add(bucket: dict, row: dict) -> None:
    bucket["calls"] += 1
    bucket[row["outcome"]] = bucket.get(row["outcome"], 0) + 1
    bucket["seconds"] = round(bucket["seconds"] + row["seconds"], 1)


def tool_of(spec: dict) -> str | None:
    """Which CLI a provider runs: claude, codex, gemini, antigravity, ollama, or None. A provider of Mehteran's own
    adapters names its adapter; one of config.toml has a command."""
    if spec.get("api") == "ollama":
        return "ollama"
    if spec.get("adapter"):
        from . import providers
        adapter = providers.ADAPTERS.get(spec["adapter"])
        return getattr(adapter, "tool", None) if adapter else None
    command = spec.get("command") or []
    return TOOL_OF.get(Path(str(command[0])).stem.lower()) if command else None


def program_of(spec: dict) -> str:
    """The program of a provider's CLI: the first word of its command, or its adapter's program."""
    if spec.get("command"):
        return str(spec["command"][0])
    from . import providers
    adapter = providers.ADAPTERS.get(spec.get("adapter") or "")
    return getattr(adapter, "program", "") or ""


def summary(store, home: Path, cfg: dict, root: Path) -> dict:
    """{generated, providers: [...]} for GET /api/usage."""
    now = time.time()
    midnight = time.mktime(time.localtime(now)[:3] + (0, 0, 0, 0, 0, -1))
    starts = {"today": midnight, "5h": now - WINDOWS["5h"], "7d": now - WINDOWS["7d"]}
    rows = store.calls(0)
    translation = _read_json(root / ".jobs" / "quota.json")
    setup = _read_json(home / "configurations" / "quota.json")
    probed = _read_json(home / "configurations" / "usage.json")
    names = list(dict.fromkeys([*cfg["providers"], *(r["provider"] for r in rows)]))
    out = []
    for name in names:
        spec = cfg["providers"].get(name) or {}
        mine = [r for r in rows if r["provider"] == name]
        entry = {"provider": name, "tool": tool_of(spec), "configured": name in cfg["providers"], **_count(),
                 "last_call": max((r["started"] for r in mine), default=None),
                 "windows": {w: _count() for w in starts}, "models": {}}
        for row in mine:
            _add(entry, row)
            _add(entry["models"].setdefault(row["model"] or "", _count()), row)
            for window, start in starts.items():
                if row["started"] >= start:
                    _add(entry["windows"][window], row)
        quota = [r for r in mine if r["outcome"] == "quota"]
        last = quota[-1] if quota else None
        entry["last_quota"] = {"at": last["started"], "until": last["until"], "message": last["message"]} if last else None
        entry["resets_at"] = last["until"] if last and last["until"] and last["until"] > now else None
        entry["tool_reported"] = tool_reported(entry["tool"], probed)
        entry["translation_quota"] = translation.get(name) or None
        entry["setup_quota"] = setup.get(name) or None
        out.append(entry)
    return {"generated": now, "providers": out, "refreshing": _refresh["running"]}


def tool_reported(tool: str | None, probed: dict) -> dict | None:
    if tool == "codex":
        return codex_limits()
    if tool == "claude":
        return probed.get("claude") or None
    return None


# --- Codex: its session logs ---------------------------------------------------------

def _codex_home() -> Path:
    return Path(os.environ["CODEX_HOME"]) if os.environ.get("CODEX_HOME") else Path.home() / ".codex"


def codex_limits(max_files: int = 5) -> dict | None:
    """The newest rate-limit entry of Codex's session logs, or None. Reads only the end of the newest files."""
    folder = _codex_home() / "sessions"
    try:
        files = sorted(folder.rglob("rollout-*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)[:max_files]
    except OSError:
        return None
    for path in files:
        try:
            with open(path, "rb") as f:
                f.seek(max(0, path.stat().st_size - 512 * 1024))
                lines = f.read().decode("utf-8", "replace").splitlines()
        except OSError:
            continue
        for line in reversed(lines):
            if '"rate_limits"' not in line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            limits = _find(event, "rate_limits")
            if not isinstance(limits, dict):
                continue
            windows = []
            for key in ("primary", "secondary"):
                window = limits.get(key)
                if isinstance(window, dict) and window.get("used_percent") is not None:
                    resets = window.get("resets_at")
                    windows.append({"name": key, "used_percent": window.get("used_percent"),
                                    "window_minutes": window.get("window_minutes"), "resets_at": resets,
                                    # the window has reset since: the percent is no longer current
                                    "expired": isinstance(resets, (int, float)) and resets < time.time()})
            return {"source": "codex-session-log", "observed_at": event.get("timestamp") or path.stat().st_mtime,
                    "plan": limits.get("plan_type"), "limit_reached": limits.get("rate_limit_reached_type"),
                    "windows": windows}
    return None


def _find(data, key: str):
    if isinstance(data, dict):
        if key in data:
            return data[key]
        for value in data.values():
            found = _find(value, key)
            if found is not None:
                return found
    elif isinstance(data, list):
        for value in data:
            found = _find(value, key)
            if found is not None:
                return found
    return None


# --- Claude Code: "/usage" (no model call), kept fresh in the background -------------------------

# "Current session: 2% used · resets Nov 23 at 8:59pm (Europe/Istanbul)", "Current week (all models): 72% used · ..."
_USAGE_LINE = re.compile(r"^Current (session|week)(?: \(([^)]*)\))?:\s*(\d+(?:\.\d+)?)% used(?:\s*·\s*resets\s+(.+))?$",
                         re.I | re.M)


def _reset_time(text: str, now: float) -> float | None:
    """"Nov 23 at 8:59pm (Europe/Istanbul)" or "8:59pm (...)" as a timestamp (the tool prints local time), or None."""
    text = re.sub(r"\s*\([^)]*\)\s*$", "", text.strip())
    today = time.localtime(now)
    for fmt, dated in (("%b %d at %I:%M%p", True), ("%b %d at %I%p", True), ("%I:%M%p", False), ("%I%p", False)):
        try:  # with the year: a day and month alone cannot name 29 February
            got = time.strptime(f"{today.tm_year} {text}", "%Y " + fmt)
        except ValueError:
            continue
        month, day = (got.tm_mon, got.tm_mday) if dated else (today.tm_mon, today.tm_mday)
        try:
            stamp = time.mktime((today.tm_year, month, day, got.tm_hour, got.tm_min, 0, 0, 0, -1))
        except (OverflowError, ValueError):
            return None
        if not dated and stamp < now:
            stamp += 86400
        elif dated and stamp < now - 180 * 86400:  # a date of next year
            stamp = time.mktime((today.tm_year + 1, month, day, got.tm_hour, got.tm_min, 0, 0, 0, -1))
        return stamp
    return None


def parse_claude_usage(text: str, now: float | None = None) -> dict | None:
    """The windows of Claude Code's "/usage" answer, or None when the text has none."""
    now = time.time() if now is None else now
    windows = []
    for kind, scope, percent, resets in _USAGE_LINE.findall(text or ""):
        window = {"utilization": round(float(percent) / 100, 4), "resets_at": _reset_time(resets, now) if resets else None}
        if kind.lower() == "session":
            window["name"] = "five_hour"
        elif not scope or scope.lower() == "all models":
            window["name"] = "seven_day"
        else:
            window.update(name="seven_day_model", model=scope)
        windows.append(window)
    return {"source": "claude-usage-command", "observed_at": now, "windows": windows} if windows else None


def claude_usage(home: Path, program: str = "claude", timeout: int = 60) -> dict | None:
    """Asks Claude Code "/usage" in print mode: it answers from the account, without a model call. None when this
    Claude Code does not know the command or is not signed in with a subscription."""
    from pipeline import system

    from . import providers
    allowed = providers.read_settings(home)["providers"].get("claude", {}).get("api_key", False)
    argv = system.resolve([program, "-p", "--safe-mode", "--tools", "", "--no-session-persistence", "--strict-mcp-config",
                           "--output-format", "json"])
    with tempfile.TemporaryDirectory(prefix="mehteran-usage-") as tmp:
        proc = subprocess.run(argv, input="/usage", capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, cwd=tmp,
                              env=providers.guarded_env(providers.ADAPTERS["claude"].keys, allowed), **system.hidden_window())
    try:
        answer = json.loads(proc.stdout)
    except ValueError:
        return None
    # a model call here means that this Claude Code took "/usage" for a question: its answer is not a report
    if not isinstance(answer, dict) or answer.get("num_turns") or not isinstance(answer.get("result"), str):
        return None
    found = parse_claude_usage(answer["result"])
    if found:
        remember(home, "claude", found)
    return found


_refresh = {"running": False, "tried": 0.0}
_refresh_lock = threading.Lock()


def refresh_stale(home: Path, cfg: dict, before=None) -> bool:
    """Starts a background "/usage" of Claude Code when its last report is older than STALE_SECONDS. At most one at a
    time, and one attempt per STALE_SECONDS (a Claude Code that cannot answer is not asked again and again)."""
    program = next((program_of(spec) for spec in cfg["providers"].values() if tool_of(spec) == "claude"), None)
    if not program:
        return False
    now = time.time()
    seen = (_read_json(home / "configurations" / "usage.json").get("claude") or {}).get("observed_at")
    with _refresh_lock:
        fresh = isinstance(seen, (int, float)) and now - seen < STALE_SECONDS
        if _refresh["running"] or fresh or now - _refresh["tried"] < STALE_SECONDS:
            return False
        _refresh.update(running=True, tried=now)

    def work():
        try:
            if before:
                before()
            claude_usage(home, program)
        except (OSError, subprocess.SubprocessError, KeyError):
            pass
        finally:
            _refresh["running"] = False

    threading.Thread(target=work, name="mehteran-usage", daemon=True).start()
    return True


# --- Claude Code: one short call, only when asked ---------------------------------------------

def parse_claude_events(text: str) -> dict | None:
    """The rate_limit_event of Claude Code's stream-json output, or None."""
    for line in text.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        info = event.get("rate_limit_info") if isinstance(event, dict) and event.get("type") == "rate_limit_event" else None
        if isinstance(info, dict):
            windows = [{"name": name, "utilization": w.get("utilization"), "resets_at": w.get("resetsAt"),
                        "status": w.get("status")}
                       for name, w in (info.get("unifiedWindows") or {}).items() if isinstance(w, dict)]
            return {"source": "claude-rate-limit-event", "observed_at": time.time(), "status": info.get("status"),
                    "limit_type": info.get("rateLimitType"), "resets_at": info.get("resetsAt"), "windows": windows}
    return None


def probe_claude(home: Path, program: str = "claude", timeout: int = 120) -> dict | None:
    """Asks Claude Code for one word with its smallest model in stream-json mode and keeps its rate_limit_event.
    The environment has no API key unless the user allowed it (the billing guard of mehteran/providers)."""
    from pipeline import system

    from . import providers
    allowed = providers.read_settings(home)["providers"].get("claude", {}).get("api_key", False)
    argv = system.resolve([program, "-p", "--model", "haiku", "--tools", "", "--no-session-persistence",
                           "--output-format", "stream-json", "--verbose"])
    with tempfile.TemporaryDirectory(prefix="mehteran-probe-") as tmp:
        proc = subprocess.run(argv, input="Reply with exactly: OK", capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, cwd=tmp,
                              env=providers.guarded_env(providers.ADAPTERS["claude"].keys, allowed), **system.hidden_window())
    found = parse_claude_events(proc.stdout)
    if found:
        remember(home, "claude", found)
    return found


def remember(home: Path, tool: str, found: dict) -> None:
    """Keeps what a tool reported about its usage in <data>/configurations/usage.json (probe_claude, and every
    Claude Code call of a run: mehteran/worker.py)."""
    path = home / "configurations" / "usage.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = _read_json(path)
    data[tool] = found
    tmp_path = path.with_name(f"{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    paths.replace(tmp_path, path)


# --- the translation app's running books ------------------------------------------------

def translation_activity(root: Path) -> list[dict]:
    """Books of the translation app that are being translated now (their run.json; read only)."""
    try:
        from pipeline.web import _book_pid
    except ImportError:
        return []
    out, now = [], time.time()
    for book_dir in sorted(p for p in (root / "books").glob("*") if p.is_dir()):
        info = _read_json(book_dir / "work" / "run.json")
        if info.get("state") not in ("running", "waiting_quota") or not _book_pid(book_dir):
            continue
        started = info.get("started")
        out.append({"book": book_dir.name, "state": info.get("state"), "stage": info.get("stage"), "started": started,
                    "elapsed": round(now - started, 1) if isinstance(started, (int, float)) else None,
                    "quota": info.get("quota") or {}})
    return out


# The translation app's run states (pipeline/runstatus.py, pipeline/cli.py) as Mehteran's run statuses.
_BOOK_STATUS = {"running": "running", "waiting_quota": "running", "finished": "succeeded", "stopped": "cancelled",
                "failed": "failed"}


def translation_runs(root: Path) -> list[dict]:
    """The last run of each book of the translation app (its run.json; read only), newest first: shown in the
    Runs tab next to the workflow runs. A run that says "running" while no process holds the book was interrupted."""
    try:
        from pipeline.web import _book_pid
    except ImportError:
        return []
    out = []
    for book_dir in sorted(p for p in (root / "books").glob("*") if p.is_dir()):
        info = _read_json(book_dir / "work" / "run.json")
        state = info.get("state")
        if state not in _BOOK_STATUS:
            continue
        active = state in ("running", "waiting_quota") and bool(_book_pid(book_dir))
        status = _BOOK_STATUS[state] if active or state not in ("running", "waiting_quota") else "interrupted"
        started = info.get("started") if isinstance(info.get("started"), (int, float)) else None
        out.append({"book": book_dir.name, "status": status, "active": active, "waiting_quota": active and state == "waiting_quota",
                    "stage": info.get("stage"), "started": started,
                    "finished": info.get("finished") if isinstance(info.get("finished"), (int, float)) else None,
                    "error": info.get("error") if isinstance(info.get("error"), str) else None})
    return sorted(out, key=lambda r: r["started"] or 0, reverse=True)
