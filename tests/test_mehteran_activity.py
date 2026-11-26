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
        run_id = self.waiting(engine, workflow(ai("ask", f"TASK:ask QUOTA=1:{(self.tmp / 'q').as_posix()}"), []))
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
        run_id = engine.start(workflow(ai("ask", f"TASK:ask FAIL=1:{(self.tmp / 'f').as_posix()}", retries=0), []))
        self.assertEqual(engine.wait(run_id, 30), "failed")
        engine.switch(run_id, "ask", "chatgpt")
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        self.assertEqual(engine.get(run_id)["providers"]["ask"], "chatgpt")

    def test_loop_keeps_its_finished_parts_after_a_switch(self):
        engine = self.engine(quota_delay=120, parallel=1)
        # One part (the last section) meets the limit. A limit stops the parts not yet started; which parts finished
        # before it depends on the order the parts got their turn. Each part must succeed exactly once: a finished
        # part is kept, not asked again, and the part that met the limit runs again on the new model.
        book = BOOK.replace("Gamma.", f"Gamma. QUOTA=1:{(self.tmp / 'q').as_posix()}")
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
        text = workflow(ai("ask", f"TASK:ask QUOTA=1:{(self.tmp / 'q').as_posix()}") .replace("type: ai.cli", "type: ai.cli, fallback_provider: chatgpt"), [])
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
        for prompt in ("TASK:one", f"TASK:two QUOTA=1:{(self.tmp / 'q').as_posix()}"):
            run_id = engine.start(workflow(ai("ask", prompt, provider="fake/small"), []))
            self.assertEqual(engine.wait(run_id, 30), "succeeded")
        cfg = engine.provider_cfg
        data = usage.summary(engine.store, self.home, cfg)
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
        # Mehteran's own adapters have no command: the adapter names the tool and its program
        self.assertEqual((usage.tool_of({"adapter": "claude"}), usage.program_of({"adapter": "claude"})), ("claude", "claude"))
        self.assertEqual(usage.tool_of({"adapter": "codex"}), "codex")
        self.assertIsNone(usage.tool_of({"adapter": "openai-local", "api": "openai"}))

    def test_claude_usage_command_report(self):
        """Claude Code's "/usage" answer (no model call) becomes the windows of the remaining-usage display."""
        now = time.mktime((2026, 11, 23, 16, 0, 0, 0, 0, -1))
        text = ("You are currently using your subscription to power your Claude Code usage\n\n"
                "Current session: 2% used · resets Nov 23 at 8:59pm (Europe/Istanbul)\n"
                "Current week (all models): 72% used · resets Nov 24 at 9am (Europe/Istanbul)\n"
                "Current week (Fable): 59.5% used\n\nLast 24h · 763 requests\n  87%  Start fresh when you switch tasks\n")
        found = usage.parse_claude_usage(text, now)
        self.assertEqual(found["source"], "claude-usage-command")
        self.assertEqual([(w["name"], w["utilization"]) for w in found["windows"]],
                         [("five_hour", 0.02), ("seven_day", 0.72), ("seven_day_model", 0.595)])
        self.assertEqual(found["windows"][0]["resets_at"], time.mktime((2026, 11, 23, 20, 59, 0, 0, 0, -1)))
        self.assertEqual(found["windows"][1]["resets_at"], time.mktime((2026, 11, 24, 9, 0, 0, 0, 0, -1)))
        self.assertEqual((found["windows"][2]["model"], found["windows"][2]["resets_at"]), ("Fable", None))
        self.assertIsNone(usage.parse_claude_usage("Unknown command: /usage", now))
        # a time without a date is the next such time; a date that passed long ago is next year's
        self.assertEqual(usage._reset_time("3pm (UTC)", now), time.mktime((2026, 11, 24, 15, 0, 0, 0, 0, -1)))
        self.assertEqual(usage._reset_time("Jan 2 at 1:05am", now), time.mktime((2027, 1, 2, 1, 5, 0, 0, 0, -1)))

    def test_stale_report_is_asked_again_once(self):
        """An old report starts one background "/usage"; a fresh one, or a recent attempt, starts none."""
        cfg = {"providers": {"claude": {"command": ["claude", "-p"]}, "fake": {"command": ["python3", "x.py"]}}}
        asked = threading.Event()
        usage._refresh.update(running=False, tried=0.0)
        with mock.patch("mehteran.usage.claude_usage", side_effect=lambda *a, **k: asked.set()) as call:
            self.assertTrue(usage.refresh_stale(self.home, cfg))
            self.assertTrue(asked.wait(5))
            self.assertFalse(usage.refresh_stale(self.home, cfg), "one attempt per STALE_SECONDS")
            usage._refresh.update(running=False, tried=0.0)
            usage.remember(self.home, "claude", {"observed_at": time.time(), "windows": []})
            self.assertFalse(usage.refresh_stale(self.home, cfg), "a fresh report is kept")
            usage._refresh.update(running=False, tried=0.0)
            self.assertFalse(usage.refresh_stale(self.home, {"providers": {"fake": cfg["providers"]["fake"]}}))
            self.assertEqual(call.call_count, 1)


class QuotaLogTests(HomeCase):
    def test_the_reason_is_in_the_log_when_a_step_shows_it_waits(self):
        # A page (or a test) that sees "waiting_quota" reads the log at once; the reason must already be there.
        # The write of the log line is slowed down so that the old order (status first) fails every time.
        engine = self.engine(quota_delay=1)
        append = livelog.append

        def slow(path, text, *args, **kwargs):
            if "Usage limit" in str(text):
                time.sleep(1)
            return append(path, text, *args, **kwargs)

        with mock.patch.object(livelog, "append", slow):
            run_id = engine.start(workflow(ai("ask", f"TASK:ask QUOTA=1:{(self.tmp / 'q').as_posix()}"), []))
            self.wait_for(lambda: engine.get(run_id)["nodes"]["ask"]["status"] == "waiting_quota")
            self.assertIn("Usage limit", engine.node_log(run_id, "ask")["text"])
            self.assertEqual(engine.wait(run_id, 30), "succeeded")


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

        run_id = engine.start(workflow(ai("ask", f"TASK:ask QUOTA=1:{(self.tmp / 'q').as_posix()}"), []))
        self.wait_for(lambda: engine.get(run_id)["nodes"]["ask"]["status"] == "waiting_quota")
        status, data = call("GET", "/api/activity")
        self.assertEqual((status, data["runs"][0]["nodes"][0]["status"]), (200, "waiting_quota"))
        self.assertNotIn("translation", data)
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
