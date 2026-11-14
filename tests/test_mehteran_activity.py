"""Usage counts, switching the model of a waiting step, fallback models, live node logs and the activity list.
Fake AI tool and a temporary MEHTERAN_HOME; no real model, no network."""

import json
import os
import sys
import threading
import time
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, ai, workflow  # noqa: E402
from test_mehteran_limits import BOOK, LOOP  # noqa: E402

from mehteran import livelog, schema, usage  # noqa: E402
from mehteran.engine import RunError  # noqa: E402
from mehteran.web import App, make_handler  # noqa: E402


class LiveLogTests(HomeCase):
    def test_a_node_log_grows_while_it_works_and_is_read_in_pieces(self):
        engine = self.engine()
        engine.heartbeat = 0.2
        run_id = engine.start(workflow(ai("ask", "TASK:ask SLEEP=1 ANSWER=Done_with_Bearer_abcdefghijk12345"), []))
        self.wait_for(lambda: "calling fake" in engine.node_log(run_id, "ask")["text"])
        first = engine.node_log(run_id, "ask")
        self.assertFalse(first["done"])
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        rest = engine.node_log(run_id, "ask", first["offset"])
        text = first["text"] + rest["text"]
        for line in ("ask: attempt 1 started (fake)", "calling fake (prompt", "still working", "Done with Bearer [hidden]",
                     "ok: answer:", "done ("):
            self.assertIn(line, text)
        self.assertNotIn("abcdefghijk12345", text)
        self.assertTrue(rest["done"])
        self.assertEqual(engine.node_log(run_id, "ask", rest["offset"])["text"], "")
        with self.assertRaises(RunError):
            engine.node_log(run_id, "ghost")

    def test_redaction_size_limit_and_utf8_pieces(self):
        path = self.tmp / "log.txt"
        livelog.append(path, "key sk-ant-abcdefghijklmnopqrstuv and AIzaSyA1234567890abcdefghijklmn ok ")
        self.assertEqual(path.read_text(), "key [hidden] and [hidden] ok ")
        livelog.append(path, "ğüş")
        text, offset = livelog.read(path, len(path.read_bytes()) - 5)  # inside a two-byte letter
        self.assertTrue(text.endswith("üş") or text.endswith("ş"))
        with mock.patch.object(livelog, "LIMIT", 100):
            livelog.append(path, "x" * 500)
            self.assertLessEqual(path.stat().st_size, 100)
            self.assertIn("log cut", path.read_text())
            livelog.append(path, "more")
            self.assertNotIn("more", path.read_text())


class SwitchTests(HomeCase):
    def waiting(self, engine, text):
        run_id = engine.start(text)
        self.wait_for(lambda: engine.get(run_id)["nodes"]["ask"]["status"] == "waiting_quota")
        return run_id

    def test_switch_a_waiting_step_to_another_model(self):
        engine = self.engine(quota_delay=120)
        run_id = self.waiting(engine, workflow(ai("ask", f"TASK:ask QUOTA=1:{self.tmp / 'q'}"), []))
        activity = engine.activity()
        self.assertEqual(activity[0]["id"], run_id)
        self.assertTrue(activity[0]["waiting_quota"])
        self.assertIn("Usage limit", activity[0]["nodes"][0]["waiting_reason"])
        with self.assertRaises(RunError):
            engine.switch(run_id, "ask", "nonexistent/model")
        started = time.time()
        engine.switch(run_id, "ask", "claude")
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        self.assertLess(time.time() - started, 15, "the wait ended at once")
        run = engine.get(run_id)
        self.assertEqual(run["providers"]["ask"], "claude")
        switched = [e for e in engine.store.events(run_id) if e["kind"] == "provider_switched"]
        self.assertEqual((switched[0]["key"], switched[0]["text"]), ("event_switched", "Model switched: fake → claude"))
        outcomes = [(c["provider"], c["outcome"]) for c in engine.store.calls(0)]
        self.assertEqual(outcomes, [("fake", "quota"), ("claude", "ok")])
        with self.assertRaises(RunError):
            engine.switch(run_id, "ask", "fake")  # succeeded: nothing to switch

    def test_switch_a_failed_step_retries_it(self):
        engine = self.engine()
        run_id = engine.start(workflow(ai("ask", f"TASK:ask FAIL=1:{self.tmp / 'f'}", retries=0), []))
        self.assertEqual(engine.wait(run_id, 30), "failed")
        engine.switch(run_id, "ask", "chatgpt")
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        self.assertEqual(engine.get(run_id)["providers"]["ask"], "chatgpt")

    def test_loop_keeps_its_finished_parts_after_a_switch(self):
        engine = self.engine(quota_delay=120, parallel=1)
        # One part (the last section) meets the limit. A limit stops the parts not yet started; which parts finished
        # before it depends on the order the parts got their turn. Each part must succeed exactly once: a finished
        # part is kept, not asked again, and the part that met the limit runs again on the new model.
        book = BOOK.replace("Gamma.", f"Gamma. QUOTA=1:{self.tmp / 'q'}")
        run_id = engine.start(LOOP.replace("MARK", ""), files={"book": self.doc("book.md", book)})
        self.wait_for(lambda: engine.get(run_id)["nodes"]["each"]["status"] == "waiting_quota")
        engine.switch(run_id, "each", "claude")
        self.assertEqual(engine.wait(run_id, 60), "succeeded", engine.get(run_id)["error"])
        ok = [(c["provider"], c["outcome"]) for c in engine.store.calls(0) if c["outcome"] == "ok"]
        self.assertEqual(len(ok), 4, "each of the 4 parts succeeded once: no finished part was asked again")
        self.assertIn(("claude", "ok"), ok, "the part that met the limit ran on the new model")
        text = (self.home / "executions" / run_id / engine.get(run_id)["nodes"]["each"]["outputs"]["text"]).read_text(encoding="utf-8")
        self.assertEqual([f"Answer part{i}" in text for i in range(1, 5)], [True] * 4, "the loop's text has every part")

    def test_fallback_provider(self):
        engine = self.engine(quota_delay=120)
        text = workflow(ai("ask", f"TASK:ask QUOTA=1:{self.tmp / 'q'}") .replace("type: ai.cli", "type: ai.cli, fallback_provider: chatgpt"), [])
        run_id = engine.start(text)
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        self.assertEqual(engine.get(run_id)["providers"]["ask"], "chatgpt")
        switched = [e for e in engine.store.events(run_id) if e["kind"] == "provider_switched"]
        self.assertEqual(switched[0]["key"], "event_switched_auto")
        with self.assertRaises(RunError):
            engine.start(text.replace("fallback_provider: chatgpt", "fallback_provider: unknown"))
        for bad, fragment in (("fallback_provider: \"no good\"", "is not a valid provider"),
                              ("fallback_provider: \"{{inputs.x}}\"", "must be a name")):
            with self.assertRaises(schema.WorkflowError) as e:
                schema.parse(text.replace("fallback_provider: chatgpt", bad))
            self.assertTrue(any(fragment in m for m in e.exception.messages()), e.exception.messages())
        with self.assertRaises(schema.WorkflowError) as e:
            schema.parse("schema_version: 1\nid: x\nname: X\nnodes:\n  - {id: m, type: text.merge, fallback_provider: fake}\n")
        self.assertTrue(any("only steps that use a model" in m for m in e.exception.messages()))


class UsageTests(HomeCase):
    def test_counts_per_provider_model_and_window(self):
        engine = self.engine(quota_delay=0.2)
        for prompt in ("TASK:one", f"TASK:two QUOTA=1:{self.tmp / 'q'}"):
            run_id = engine.start(workflow(ai("ask", prompt, provider="fake/small"), []))
            self.assertEqual(engine.wait(run_id, 30), "succeeded")
        cfg = engine.provider_cfg
        data = usage.summary(engine.store, self.home, cfg, self.tmp / "code")
        fake = next(p for p in data["providers"] if p["provider"] == "fake")
        self.assertEqual((fake["calls"], fake["ok"], fake["quota"]), (3, 2, 1))
        self.assertEqual(fake["windows"]["5h"]["calls"], 3)
        self.assertEqual(fake["windows"]["today"]["ok"], 2)
        self.assertEqual(fake["models"]["small"]["calls"], 3)
        self.assertIsNotNone(fake["last_quota"]["until"])
        self.assertIsNone(fake["tool_reported"], "the fake tool reports nothing")
        claude = next(p for p in data["providers"] if p["provider"] == "claude")
        self.assertEqual(claude["calls"], 0)

    def test_codex_session_log_and_claude_events(self):
        sessions = self.tmp / "codex" / "sessions" / "2026" / "11" / "11"
        sessions.mkdir(parents=True)
        event = {"timestamp": "2026-11-11T12:33:25Z", "type": "event_msg", "payload": {"type": "token_count", "rate_limits": {
            "primary": {"used_percent": 43.0, "window_minutes": 300, "resets_at": 4102444800},
            "secondary": {"used_percent": 11.0, "window_minutes": 10080, "resets_at": 1}, "plan_type": "plus"}}}
        (sessions / "rollout-x.jsonl").write_text('{"type":"other"}\n' + json.dumps(event) + "\n", encoding="utf-8")
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(self.tmp / "codex")}):
            found = usage.codex_limits()
        self.assertEqual((found["plan"], found["windows"][0]["used_percent"], found["windows"][0]["window_minutes"]),
                         ("plus", 43.0, 300))
        self.assertEqual([w["expired"] for w in found["windows"]], [False, True])
        with mock.patch.dict(os.environ, {"CODEX_HOME": str(self.tmp / "none")}):
            self.assertIsNone(usage.codex_limits())
        line = json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "resetsAt": 1794622800,
                           "rateLimitType": "five_hour", "unifiedWindows": {"five_hour": {"utilization": 0.43,
                           "resetsAt": 1794622800, "status": "allowed"}}}})
        parsed = usage.parse_claude_events('{"type":"system"}\n' + line)
        self.assertEqual(parsed["windows"], [{"name": "five_hour", "utilization": 0.43, "resets_at": 1794622800, "status": "allowed"}])
        self.assertIsNone(usage.parse_claude_events('{"type":"result"}'))
        self.assertEqual(usage.tool_of({"command": ["/x/codex", "exec"]}), "codex")
        self.assertEqual(usage.tool_of({"api": "ollama"}), "ollama")


class TranslationRunTests(HomeCase):
    """The Runs tab lists the last run of each book of the translation app (read from its run.json)."""

    def book(self, root, name, info):
        work = root / "books" / name / "work"
        work.mkdir(parents=True)
        (work / "run.json").write_text(json.dumps(info), encoding="utf-8")

    def test_states_become_run_statuses_newest_first(self):
        from mehteran import usage
        root = self.home / "tp"
        self.book(root, "old", {"state": "finished", "started": 100, "finished": 200})
        self.book(root, "stopped", {"state": "stopped", "started": 300})
        self.book(root, "broken", {"state": "failed", "started": 400, "error": "boom"})
        self.book(root, "ghost", {"state": "running", "started": 500, "stage": "translate"})  # nobody holds the book
        self.book(root, "odd", {"state": "something"})
        (root / "books" / "never").mkdir()
        runs = usage.translation_runs(root)
        self.assertEqual([(r["book"], r["status"], r["active"]) for r in runs],
                         [("ghost", "interrupted", False), ("broken", "failed", False), ("stopped", "cancelled", False),
                          ("old", "succeeded", False)])
        self.assertEqual(runs[1]["error"], "boom")
        self.assertEqual(usage.translation_runs(self.home / "nothing-here"), [])

    def test_a_held_book_is_running(self):
        from mehteran import usage
        root = self.home / "tp"
        self.book(root, "live", {"state": "waiting_quota", "started": 10})
        with mock.patch("pipeline.web._book_pid", return_value=4242):
            run, = usage.translation_runs(root)
        self.assertEqual((run["status"], run["active"], run["waiting_quota"]), ("running", True, True))


class ApiTests(HomeCase):
    def test_usage_activity_log_and_switch_routes(self):
        engine = self.engine(quota_delay=120)
        app = App(engine)
        server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        port = server.server_address[1]
        server.RequestHandlerClass = make_handler(app, port)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)

        def call(method, path, body=None):
            req = urllib.request.Request(f"http://127.0.0.1:{port}{path}", method=method,
                                         data=json.dumps(body).encode() if body is not None else None)
            req.add_header("X-Token", app.token)
            req.add_header("X-Lang", "tr")
            try:
                with urllib.request.urlopen(req, timeout=30) as res:
                    return res.status, json.loads(res.read())
            except urllib.error.HTTPError as e:
                with e:
                    return e.code, json.loads(e.read())

        run_id = engine.start(workflow(ai("ask", f"TASK:ask QUOTA=1:{self.tmp / 'q'}"), []))
        self.wait_for(lambda: engine.get(run_id)["nodes"]["ask"]["status"] == "waiting_quota")
        # The translation app's books of a temporary folder: a book that the user translates now is not this test's.
        with mock.patch("mehteran.web.ROOT", self.tmp / "tp"):
            status, data = call("GET", "/api/activity")
        self.assertEqual((status, data["runs"][0]["nodes"][0]["status"]), (200, "waiting_quota"))
        self.assertEqual(data["translation"], [])
        status, data = call("GET", f"/api/runs/{run_id}/log?node=ask&offset=0")
        self.assertEqual(status, 200)
        self.assertIn("Usage limit", data["text"])  # a log is written in the language of the run
        self.assertEqual(call("GET", f"/api/runs/{run_id}/log?node=Bad")[0], 400)
        self.assertEqual(call("POST", f"/api/runs/{run_id}/nodes/ask/switch", {"provider": "zzz"})[0], 400)
        self.assertEqual(call("POST", f"/api/runs/{run_id}/nodes/ask/switch", {"provider": "chatgpt"}), (200, {"ok": True}))
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        status, data = call("GET", "/api/usage")
        names = {p["provider"]: p for p in data["providers"]}
        self.assertEqual((names["fake"]["quota"], names["chatgpt"]["ok"]), (1, 1))
        self.assertEqual(call("POST", "/api/usage/probe/fake")[0], 400, "only Claude Code is asked")


if __name__ == "__main__":
    unittest.main()
