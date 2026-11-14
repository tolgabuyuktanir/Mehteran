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
  - Claude Code reports a "rate_limit_event" (utilization of the 5-hour and the weekly window, reset times) in its
    stream-json output. The translation app's command uses text output, so Mehteran asks only when the user wants it
    (probe_claude: one very short call with the smallest model) and keeps the answer in configurations/usage.json.
  - Gemini CLI and Antigravity CLI report token counts per answer, but no limits: None.
- The translation app's usage limits: <code folder>/.jobs/quota.json (read only), and the last limit met by a model
  test on the Setup tab: <data>/configurations/quota.json.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import time
from pathlib import Path

WINDOWS = {"today": None, "5h": 5 * 3600, "7d": 7 * 86400}
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
    """Which CLI a provider runs: claude, codex, gemini, antigravity, ollama, or None."""
    if spec.get("api") == "ollama":
        return "ollama"
    command = spec.get("command") or []
    return TOOL_OF.get(Path(str(command[0])).stem.lower()) if command else None


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
    return {"generated": now, "providers": out}


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
    """Asks Claude Code for one word with its smallest model in stream-json mode and keeps its rate_limit_event."""
    from pipeline import system
    argv = system.resolve([program, "-p", "--model", "haiku", "--tools", "", "--no-session-persistence",
                           "--output-format", "stream-json", "--verbose"])
    with tempfile.TemporaryDirectory(prefix="mehteran-probe-") as tmp:
        proc = subprocess.run(argv, input="Reply with exactly: OK", capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=timeout, cwd=tmp, **system.hidden_window())
    found = parse_claude_events(proc.stdout)
    if found:
        path = home / "configurations" / "usage.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        data = _read_json(path)
        data["claude"] = found
        tmp_path = path.with_name(path.name + ".tmp")
        tmp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp_path, path)
    return found


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
