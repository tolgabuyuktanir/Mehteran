"""Stored run messages (events, node and run errors) are shown in the language of each request, not in the language
of the moment they were written; old rows without a key keep their text."""

import json
import sqlite3
import sys
import threading
import urllib.request
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, ai, workflow  # noqa: E402

from mehteran import i18n  # noqa: E402
from mehteran.store import Store  # noqa: E402
from mehteran.web import App, make_handler  # noqa: E402


class MessageTests(HomeCase):
    def failed_run(self):
        """A run started in Turkish whose node times out after one retry."""
        i18n.set_default("tr")
        engine = self.engine()
        run_id = engine.start(workflow(ai("slow", "TASK:slow SLEEP=5", retries=1, timeout=1), []))
        self.assertEqual(engine.wait(run_id, 60), "failed")
        return engine, run_id

    def test_errors_and_events_follow_the_reader(self):
        engine, run_id = self.failed_run()
        node = engine.get(run_id)["nodes"]["slow"]
        self.assertEqual(node["error"], "1 saniyede bitmedi (süre sınırı).")
        self.assertEqual((node["error_key"], node["error_params"]), ("node_timeout", {"seconds": 1}))
        i18n.set_request("en")
        self.addCleanup(i18n.set_request, None)
        run = engine.get(run_id)
        self.assertEqual(run["nodes"]["slow"]["error"], "Did not finish in 1 seconds (timeout).")
        self.assertEqual(run["error"], "slow: Did not finish in 1 seconds (timeout).")
        events = engine.store.events(run_id)
        failed = [e for e in events if e["kind"] == "attempt_failed"]
        self.assertEqual(failed[0]["text"], "attempt 1: Did not finish in 1 seconds (timeout).")
        self.assertEqual(failed[0]["message"], failed[0]["text"])
        self.assertEqual(failed[0]["key"], "event_attempt_failed")
        self.assertEqual(failed[0]["params"]["error"], {"$key": "node_timeout", "params": {"seconds": 1}})
        self.assertEqual(engine.list()[0]["error"], run["error"])
        i18n.set_request("tr")
        self.assertEqual(engine.store.events(run_id)[-1]["text"], "slow: 1 saniyede bitmedi (süre sınırı).")

    def test_old_rows_without_keys_keep_their_text(self):
        db_path = self.tmp / "old.sqlite3"
        with closing(sqlite3.connect(db_path)) as db:  # the tables as the first slice made them
            db.executescript(
                "CREATE TABLE runs (id TEXT PRIMARY KEY, workflow_id TEXT NOT NULL, workflow_name TEXT NOT NULL, template TEXT "
                "NOT NULL DEFAULT '', status TEXT NOT NULL, created REAL NOT NULL, started REAL, finished REAL, error TEXT, "
                "inputs TEXT NOT NULL, providers TEXT NOT NULL, provider_cfg TEXT NOT NULL, workflow_yaml TEXT NOT NULL, "
                "lang TEXT NOT NULL DEFAULT 'en', cancel_requested INTEGER NOT NULL DEFAULT 0);"
                "CREATE TABLE nodes (run_id TEXT NOT NULL, node_id TEXT NOT NULL, status TEXT NOT NULL, attempts INTEGER NOT NULL "
                "DEFAULT 0, started REAL, finished REAL, error TEXT, outputs TEXT NOT NULL DEFAULT '{}', comment TEXT, "
                "PRIMARY KEY (run_id, node_id));"
                "CREATE TABLE events (run_id TEXT NOT NULL, time REAL NOT NULL, node_id TEXT, kind TEXT NOT NULL, message TEXT);"
                "INSERT INTO runs VALUES ('r', 'w', 'W', '', 'failed', 1, 1, 2, 'a: eski hata', '{}', '{}', '{}', 'x', 'tr', 0);"
                "INSERT INTO nodes VALUES ('r', 'a', 'failed', 1, 1, 2, 'eski hata', '{}', NULL);"
                "INSERT INTO events VALUES ('r', 1, 'a', 'attempt_failed', 'attempt 1: eski hata');")
            db.commit()
        store = Store(db_path)
        self.assertEqual(store.run("r")["error"], "a: eski hata")
        self.assertEqual(store.nodes("r")["a"]["error"], "eski hata")
        event = store.events("r")[0]
        self.assertEqual((event["text"], event["key"], event["params"]), ("attempt 1: eski hata", None, None))
        store.update_node("r", "a", error=i18n.t("cancelled"))
        self.assertEqual(store.nodes("r")["a"]["error_key"], "cancelled")
        store.update_node("r", "a", error="tool said no")
        self.assertEqual((store.nodes("r")["a"]["error"], store.nodes("r")["a"]["error_key"]), ("tool said no", None))

    def test_run_api_renders_in_the_request_language(self):
        engine, run_id = self.failed_run()
        app = App(engine)
        server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        port = server.server_address[1]
        server.RequestHandlerClass = make_handler(app, port)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def get(lang):
            req = urllib.request.Request(f"http://127.0.0.1:{port}/api/runs/{run_id}")
            req.add_header("X-Token", app.token)
            req.add_header("X-Lang", lang)
            with urllib.request.urlopen(req, timeout=30) as res:
                return json.loads(res.read())
        en, tr = get("en"), get("tr")
        self.assertEqual(en["nodes"]["slow"]["error"], "Did not finish in 1 seconds (timeout).")
        self.assertEqual(tr["nodes"]["slow"]["error"], "1 saniyede bitmedi (süre sınırı).")
        self.assertEqual([e["text"] for e in en["events"] if e["kind"] == "succeeded"], [])
        self.assertIn("attempt 2:", [e["text"] for e in en["events"] if e["kind"] == "attempt_failed"][1])
        self.assertIn("2. deneme:", [e["text"] for e in tr["events"] if e["kind"] == "attempt_failed"][1])


if __name__ == "__main__":
    import unittest
    unittest.main()
