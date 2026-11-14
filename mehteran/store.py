"""The state of every run and of each of its nodes, in SQLite (databases/mehteran.sqlite3, WAL mode).

Each call opens its own connection, so that threads and processes (the web interface and a command-line run) can
share the file. Statuses:
  run:  queued, running, waiting_approval, succeeded, failed, cancelled, interrupted
  node: pending, running, waiting_quota, waiting_approval, succeeded, failed, rejected, skipped, cancelled, interrupted
  (waiting_quota: the node's tool reported a usage limit; the node waits in its thread and tries again)

Messages that Mehteran writes itself (i18n.t) are stored with their key and values (error_key/error_params,
events.key/params), and read back in the language of the request; a row without a key (older runs, the output of a
tool) shows its stored text.
"""

from __future__ import annotations

import json
import sqlite3
import time
from contextlib import closing
from pathlib import Path

from . import i18n

FINISHED_RUN = {"succeeded", "failed", "cancelled", "interrupted"}
BLOCKING_NODE = {"failed", "rejected", "skipped", "cancelled", "interrupted"}  # these can be retried
ACTIVE_NODE = {"running", "waiting_quota"}  # a thread of the driving process works on these

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL, workflow_name TEXT NOT NULL, template TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL, created REAL NOT NULL, started REAL, finished REAL, error TEXT,
  inputs TEXT NOT NULL, providers TEXT NOT NULL, provider_cfg TEXT NOT NULL, workflow_yaml TEXT NOT NULL,
  lang TEXT NOT NULL DEFAULT 'en', cancel_requested INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS nodes (
  run_id TEXT NOT NULL, node_id TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
  started REAL, finished REAL, error TEXT, outputs TEXT NOT NULL DEFAULT '{}', comment TEXT,
  PRIMARY KEY (run_id, node_id));
CREATE TABLE IF NOT EXISTS events (
  run_id TEXT NOT NULL, time REAL NOT NULL, node_id TEXT, kind TEXT NOT NULL, message TEXT);
CREATE INDEX IF NOT EXISTS events_run ON events (run_id, time);
CREATE TABLE IF NOT EXISTS calls (
  run_id TEXT NOT NULL, node_id TEXT NOT NULL, provider TEXT NOT NULL, model TEXT NOT NULL DEFAULT '',
  started REAL NOT NULL, seconds REAL NOT NULL, outcome TEXT NOT NULL, until REAL, message TEXT);
CREATE INDEX IF NOT EXISTS calls_time ON calls (started);
"""
# Columns added later; a database made before them gets them on open (old rows: NULL, their text is shown).
ADDED = {"runs": ("error_key", "error_params", *"label note batch output_dir output_state main_input".split()),
         "nodes": ("error_key", "error_params"), "events": ("key", "params")}
# The history's own columns of a run (history.py): label and note (the user's name for it), batch (the batch id of a
# run started "once per file"), output_dir and output_state (save the results to a folder after success), main_input
# (the first file name or the start of the first text input, computed once).
HISTORY_COLUMNS = ("label", "note", "batch", "output_dir", "output_state", "main_input")


def _keyed(fields: dict) -> dict:
    """The fields with error_key/error_params for an error message of ours (None for any other text)."""
    if "error" in fields:
        error = fields["error"]
        keyed = isinstance(error, i18n.Msg) and bool(error.key)
        fields["error_key"] = error.key if keyed else None
        fields["error_params"] = json.dumps(error.params, ensure_ascii=False) if keyed else None
    return fields


def _localized(row: dict, field: str, key: str, params: str) -> dict:
    """The row with field in the current language and the key and values parsed."""
    try:
        values = json.loads(row.get(params) or "null")
    except ValueError:
        values = None
    row[key], row[params] = row.get(key), values
    if row.get(key):
        row[field] = i18n.render(row[key], values, row.get(field) or "")
    return row


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(SCHEMA)
            for table, columns in ADDED.items():
                have = {row[1] for row in db.execute(f"PRAGMA table_info({table})")}
                for column in columns:
                    if column not in have:
                        db.execute(f"ALTER TABLE {table} ADD COLUMN {column} TEXT")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=30, isolation_level=None)  # autocommit; BEGIN where needed
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout=30000")
        return db

    def _do(self, sql: str, args=()) -> None:
        with closing(self._connect()) as db:
            db.execute(sql, args)

    def _rows(self, sql: str, args=()) -> list[dict]:
        with closing(self._connect()) as db:
            return [dict(row) for row in db.execute(sql, args)]

    # --- runs ---
    def create_run(self, run: dict, node_ids: list[str]) -> None:
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("INSERT INTO runs (id, workflow_id, workflow_name, template, status, created, inputs, providers, "
                       "provider_cfg, workflow_yaml, lang) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                       (run["id"], run["workflow_id"], run["workflow_name"], run["template"], "queued", time.time(),
                        json.dumps(run["inputs"], ensure_ascii=False), json.dumps(run["providers"]),
                        json.dumps(run["provider_cfg"], ensure_ascii=False), run["workflow_yaml"], run["lang"]))
            db.executemany("INSERT INTO nodes (run_id, node_id, status) VALUES (?,?,?)",
                           [(run["id"], node_id, "pending") for node_id in node_ids])
            db.execute("COMMIT")

    def run(self, run_id: str) -> dict | None:
        rows = self._rows("SELECT * FROM runs WHERE id=?", (run_id,))
        if not rows:
            return None
        run = _localized(rows[0], "error", "error_key", "error_params")
        for key in ("inputs", "providers", "provider_cfg"):
            run[key] = json.loads(run[key])
        return run

    def runs(self, limit: int = 200) -> list[dict]:
        return [_localized(row, "error", "error_key", "error_params") for row in
                self._rows("SELECT id, workflow_id, workflow_name, template, status, created, started, finished, error, "
                           "error_key, error_params, " + ", ".join(HISTORY_COLUMNS) +
                           " FROM runs ORDER BY created DESC LIMIT ?", (limit,))]

    # --- the history (history.py) ---
    def delete_run(self, run_id: str) -> None:
        """The run's rows (its nodes and events too). Its model calls stay: they are the usage history."""
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            for table in ("nodes", "events"):
                db.execute(f"DELETE FROM {table} WHERE run_id=?", (run_id,))
            db.execute("DELETE FROM runs WHERE id=?", (run_id,))
            db.execute("COMMIT")

    def update_run(self, run_id: str, **fields) -> None:
        fields = _keyed(fields)
        names = ", ".join(f"{key}=?" for key in fields)
        self._do(f"UPDATE runs SET {names} WHERE id=?", (*fields.values(), run_id))

    def cancel_requested(self, run_id: str) -> bool:
        rows = self._rows("SELECT cancel_requested FROM runs WHERE id=?", (run_id,))
        return bool(rows and rows[0]["cancel_requested"])

    # --- nodes ---
    def nodes(self, run_id: str) -> dict[str, dict]:
        out = {}
        for row in self._rows("SELECT * FROM nodes WHERE run_id=? ORDER BY rowid", (run_id,)):  # workflow order
            row["outputs"] = json.loads(row["outputs"] or "{}")
            out[row["node_id"]] = _localized(row, "error", "error_key", "error_params")
        return out

    def states(self, run_id: str) -> dict[str, str]:
        return {row["node_id"]: row["status"] for row in self._rows("SELECT node_id, status FROM nodes WHERE run_id=?", (run_id,))}

    def update_node(self, run_id: str, node_id: str, **fields) -> None:
        fields = _keyed(fields)
        if "outputs" in fields:
            fields["outputs"] = json.dumps(fields["outputs"], ensure_ascii=False)
        names = ", ".join(f"{key}=?" for key in fields)
        self._do(f"UPDATE nodes SET {names} WHERE run_id=? AND node_id=?", (*fields.values(), run_id, node_id))

    def change_node(self, run_id: str, node_id: str, expected: str, **fields) -> bool:
        """update_node, but only while the node still has the expected status. False: another request was first."""
        fields = _keyed(fields)
        if "outputs" in fields:
            fields["outputs"] = json.dumps(fields["outputs"], ensure_ascii=False)
        names = ", ".join(f"{key}=?" for key in fields)
        with closing(self._connect()) as db:
            return db.execute(f"UPDATE nodes SET {names} WHERE run_id=? AND node_id=? AND status=?",
                              (*fields.values(), run_id, node_id, expected)).rowcount == 1

    def begin_attempt(self, run_id: str, node_id: str) -> int:
        with closing(self._connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("UPDATE nodes SET status='running', attempts=attempts+1, started=?, finished=NULL, error=NULL, "
                       "error_key=NULL, error_params=NULL WHERE run_id=? AND node_id=?", (time.time(), run_id, node_id))
            attempts = db.execute("SELECT attempts FROM nodes WHERE run_id=? AND node_id=?", (run_id, node_id)).fetchone()[0]
            db.execute("COMMIT")
        return attempts

    def reset_nodes(self, run_id: str, node_ids: list[str]) -> None:
        with closing(self._connect()) as db:
            db.executemany("UPDATE nodes SET status='pending', error=NULL, error_key=NULL, error_params=NULL, finished=NULL "
                           "WHERE run_id=? AND node_id=?",
                           [(run_id, node_id) for node_id in node_ids])

    # --- model calls (usage) ---
    def record_call(self, run_id: str, node_id: str, name: str, started: float, outcome: str,
                    until: float | None = None, message: str = "") -> None:
        """One model call: name "provider/model@effort"; outcome ok, failed, quota or aborted."""
        provider, _, model = name.partition("@")[0].partition("/")
        self._do("INSERT INTO calls (run_id, node_id, provider, model, started, seconds, outcome, until, message) "
                 "VALUES (?,?,?,?,?,?,?,?,?)", (run_id, node_id, provider, model, started, max(0.0, time.time() - started),
                                               outcome, until, str(message)[:500]))

    def calls(self, since: float) -> list[dict]:
        return self._rows("SELECT * FROM calls WHERE started >= ? ORDER BY started", (since,))

    # --- events ---
    def event(self, run_id: str, node_id: str | None, kind: str, message: str = "") -> None:
        keyed = isinstance(message, i18n.Msg) and bool(message.key)
        self._do("INSERT INTO events (run_id, time, node_id, kind, message, key, params) VALUES (?,?,?,?,?,?,?)",
                 (run_id, time.time(), node_id, kind, str(message)[:2000], message.key if keyed else None,
                  json.dumps(message.params, ensure_ascii=False) if keyed else None))

    def events(self, run_id: str, limit: int = 300) -> list[dict]:
        """{time, node_id, kind, message, text, key, params}: message and text in the current language (the stored
        text for a row without a key); key and params let a page render the message itself."""
        rows = self._rows("SELECT time, node_id, kind, message, key, params FROM events WHERE run_id=? "
                          "ORDER BY time DESC LIMIT ?", (run_id, limit))[::-1]
        for row in rows:
            _localized(row, "message", "key", "params")
            row["text"] = row["message"]
        return rows
