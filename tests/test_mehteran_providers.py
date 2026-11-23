"""Mehteran's own AI tool adapters (mehteran/providers/): the billing guard, the settings file, the hardened flags,
`auto` and the model order, usage limits known across runs, calls at once, privacy: local and "sent to".
Fake tools and a temporary MEHTERAN_HOME; no real model, no network, and the real tools are never asked."""

import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import FAKE, HomeCase, adapter_cfg, ai, fake_cfg, workflow  # noqa: E402

from mehteran import estimate, providers, schema, settings  # noqa: E402
from mehteran.engine import Engine, RunError  # noqa: E402
from mehteran.nodes import Ctx  # noqa: E402
from mehteran.providers import base  # noqa: E402

READY = {"installed": True, "signed_in": True, "info": ""}


def states(**over) -> dict:
    """Every tool installed and signed in, each with its own billing; over: {name: {changes}}."""
    out = {name: {**READY, "billing": a.billing} for name, a in providers.ADAPTERS.items()}
    out["ollama"]["models"] = ["qwen3:8b", "gpt-oss:120b-cloud"]
    for name, change in over.items():
        out[name] = {**out[name], **change}
    return out


EMPTY = {"order": [], "providers": {}}


class SettingsTests(HomeCase):
    def test_round_trip_keeps_known_keys_only(self):
        conf = self.home / "configurations"
        conf.mkdir(parents=True)
        (conf / "providers.toml").write_text(
            'order = ["claude/opus@high", "chatgpt", "nope", "rm -rf"]\n'
            '[providers.claude]\napi_key = true\nconcurrency = 99\ncommand = ["rm"]\n'
            '[providers.chatgpt]\nconcurrency = 1\n'
            '[providers.ollama]\nmodel = "qwen3:8b"\noptions = {num_ctx = 16384, evil = "x"}\n', encoding="utf-8")
        user = providers.read_settings(self.home)
        self.assertEqual(user["order"], ["claude/opus@high", "codex"], "chatgpt is codex; unknown entries are dropped")
        self.assertEqual(user["providers"]["claude"], {"api_key": True, "concurrency": providers.MAX_CONCURRENCY})
        self.assertEqual(user["providers"]["codex"], {"concurrency": 1})
        self.assertEqual(user["providers"]["ollama"], {"model": "qwen3:8b", "options": {"num_ctx": 16384}})
        again = providers.write_settings(self.home, user)
        self.assertEqual(again, user)
        self.assertNotIn("command", (conf / "providers.toml").read_text(encoding="utf-8"))

    def test_provider_config_has_the_adapters_and_keeps_custom_providers(self):
        toml = self.tmp / "config.toml"
        toml.write_text('[providers.claude]\ncommand = ["claude", "-p"]\n[providers.chatgpt]\ncommand = ["codex"]\n'
                        '[providers.mine]\ncommand = ["my-llm"]\n', encoding="utf-8")
        with mock.patch.object(settings, "config_path", lambda: toml):
            cfg = settings.provider_config()
        self.assertEqual(cfg["providers"]["claude"]["adapter"], "claude", "the translation app's command is not used")
        self.assertNotIn("chatgpt", cfg["providers"])
        self.assertEqual(cfg["providers"]["codex"]["adapter"], "codex")
        self.assertEqual(cfg["providers"]["mine"]["command"], ["my-llm"], "a provider the user added still works")

    def test_old_names(self):
        self.assertEqual(providers.canonical("chatgpt/gpt-5@high"), "codex/gpt-5@high")
        self.assertEqual(providers.canonical("chatgpt", {"chatgpt": {}}), "chatgpt", "configured under its own name")
        self.assertEqual(providers.canonical("claude/opus"), "claude/opus")


class FlagTests(unittest.TestCase):
    def test_claude_is_hardened_and_never_bare(self):
        argv = providers.ADAPTERS["claude"].argv("opus", "high", Path("/tmp/o"))
        for flag in ("-p", "--safe-mode", "--no-session-persistence", "--strict-mcp-config"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertEqual(argv[argv.index("--output-format") + 1], "stream-json")
        self.assertEqual(argv[argv.index("--system-prompt") + 1], providers.SYSTEM_PROMPT)
        self.assertNotIn("--bare", argv)
        self.assertEqual(argv[-4:], ["--model", "opus", "--effort", "high"])

    def test_codex_is_read_only_ephemeral_without_the_user_config(self):
        argv = providers.ADAPTERS["codex"].argv("", "low", Path("/tmp/o"))
        self.assertEqual(argv[:2], ["codex", "exec"])
        self.assertEqual(argv[argv.index("--sandbox") + 1], "read-only")
        for flag in ("--ephemeral", "--ignore-user-config", "--skip-git-repo-check"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[-2:], ["-c", "model_reasoning_effort=low"])

    def test_billing_kinds(self):
        self.assertEqual({n: a.billing for n, a in providers.ADAPTERS.items()},
                         {"claude": "subscription", "codex": "subscription", "antigravity": "free", "ollama": "local",
                          "openai-local": "local", "gemini": "api_key"})

    def test_ollama_cloud_models_are_not_local(self):
        self.assertTrue(providers.destination("ollama", "qwen3:8b")["local"])
        for model in ("gpt-oss:120b-cloud", "glm-4.6:cloud"):
            self.assertEqual(providers.destination("ollama", model), {"vendor": "Ollama Cloud", "local": False})
        self.assertEqual(providers.destination("claude", "")["vendor"], "Anthropic")


class BillingGuardTests(HomeCase):
    KEYS = {k: "secret-value-123" for k in base.BILLED_KEYS}

    def test_the_environment_has_no_api_key_unless_allowed_for_that_tool(self):
        env = providers.guarded_env(providers.ADAPTERS["claude"].keys, False, {**self.KEYS, "PATH": "/bin"})
        self.assertEqual(env, {"PATH": "/bin"})
        env = providers.guarded_env(providers.ADAPTERS["claude"].keys, True, {**self.KEYS, "PATH": "/bin"})
        self.assertEqual(set(env), {"PATH", "ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN"}, "only Claude's own keys")

    def check_run(self, allowed: bool) -> str:
        cfg = adapter_cfg(claude={"api_key": allowed})
        engine = Engine(self.home, cfg, retry_delay=0)
        with mock.patch.dict(os.environ, self.KEYS):
            run_id = engine.start(workflow(ai("ask", "ENVCHECK", provider="claude"), []))
            self.assertEqual(engine.wait(run_id, 30), "succeeded", engine.get(run_id)["nodes"]["ask"]["error"])
        run = engine.get(run_id)
        return (engine.run_dir(run_id) / run["nodes"]["ask"]["outputs"]["text"]).read_text(encoding="utf-8")

    def test_a_run_gives_the_tool_no_key(self):
        self.assertEqual(self.check_run(False), "keys: none")

    def test_allowed_gives_only_the_tools_own_keys(self):
        self.assertEqual(self.check_run(True), "keys: ANTHROPIC_API_KEY,ANTHROPIC_AUTH_TOKEN")

    def test_claude_with_a_key_in_the_environment_is_shown_billed_only_when_passed(self):
        st = {**READY, "billing": "api_key", "key_source": "ANTHROPIC_API_KEY"}
        self.assertEqual(providers.effective_billing("claude", st, EMPTY), "subscription")
        allowed = {"order": [], "providers": {"claude": {"api_key": True}}}
        self.assertEqual(providers.effective_billing("claude", st, allowed), "api_key")
        st = {**READY, "billing": "api_key", "key_source": "apiKeyHelper"}
        self.assertEqual(providers.problem("claude", st, EMPTY), "provider_billed")


class AutoTests(HomeCase):
    def test_the_default_order_skips_billed_and_unusable_tools(self):
        found = providers.default_order(states(codex={"signed_in": False}), EMPTY)
        self.assertEqual(found, ["claude", "antigravity", "ollama/qwen3:8b"], "no gemini (billed), no codex")

    def test_kinds(self):
        st = states()
        self.assertEqual(providers.candidates("auto", st, EMPTY)[0], "claude")
        self.assertEqual(providers.candidates("auto:fast", st, EMPTY)[:2], ["claude/haiku", "codex@low"])
        self.assertEqual(providers.candidates("auto:strong", st, EMPTY)[:2], ["claude/opus", "codex@high"])
        self.assertEqual(providers.candidates("auto:local", st, EMPTY), ["ollama/qwen3:8b"])
        user = {"order": ["ollama/gpt-oss:120b-cloud", "codex/gpt-x"], "providers": {}}
        self.assertEqual(providers.candidates("auto", st, user), ["ollama/gpt-oss:120b-cloud", "codex/gpt-x"])
        self.assertEqual(providers.candidates("auto:local", st, user), [], "a cloud model is not local")
        self.assertEqual(providers.candidates("auto:fast", st, user), ["ollama/gpt-oss:120b-cloud", "codex/gpt-x"],
                         "a model named in the order is kept")

    def engine(self, order=None, **st):
        cfg = adapter_cfg()
        engine = Engine(self.home, cfg, retry_delay=0, quota_delay=0.2)
        engine.tool_states = lambda: states(antigravity={"installed": False}, **st)
        if order:
            providers.write_settings(self.home, {"order": order, "providers": {}})
        return engine

    def test_auto_is_resolved_and_frozen_when_the_run_starts(self):
        engine = self.engine(order=["codex", "claude"])
        wf = workflow(ai("a", "TASK:a", provider="'{{inputs.model}}'") + ai("b", "TASK:b", provider="auto:fast"), [],
                      inputs="  - {id: model, type: provider, default: auto}\n")
        run_id = engine.start(wf)
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        run = engine.store.run(run_id)
        self.assertEqual((run["providers"]["a"], run["providers"]["b"]), ("codex", "codex@low"))
        self.assertEqual(run["provider_cfg"]["auto"]["nodes"], {"a": "auto", "b": "auto:fast"})
        self.assertEqual(run["provider_cfg"]["auto"]["candidates"]["auto"], ["codex", "claude"])
        self.assertEqual(sorted(run["provider_cfg"]["providers"]), ["claude", "codex"], "the candidates are frozen too")

    def test_no_usable_tool_refuses_the_run(self):
        engine = self.engine(claude={"installed": False}, codex={"billing": "api_key"}, ollama={"models": []})
        with self.assertRaises(RunError) as caught:
            engine.start(workflow(ai("a", "TASK:a", provider="auto"), []))
        self.assertIn("No AI tool can be chosen automatically", str(caught.exception))

    def test_a_usage_limit_moves_an_auto_step_to_the_next_model(self):
        engine = self.engine(order=["claude", "codex"])
        run_id = engine.start(workflow(ai("a", f"TASK:a QUOTA=1:{self.tmp / 'q'}", provider="auto"), []))
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        self.assertEqual(engine.store.run(run_id)["providers"]["a"], "codex")
        self.assertEqual([(c["provider"], c["outcome"]) for c in engine.store.calls(0)], [("claude", "quota"), ("codex", "ok")])
        kinds = [e["kind"] for e in engine.store.events(run_id)]
        self.assertIn("provider_switched", kinds)
        self.assertNotIn("quota_wait", kinds, "no waiting while another model is free")

    def test_a_limit_from_another_run_is_known_without_a_call(self):
        engine = self.engine(order=["claude", "codex"])
        engine.store.record_call("old-run", "x", "claude", time.time(), "quota", time.time() + 3600, "limit")
        run_id = engine.start(workflow(ai("a", "TASK:a", provider="auto"), []))
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        self.assertEqual(engine.store.run(run_id)["providers"]["a"], "codex", "started on the free model")
        run_id = engine.start(workflow(ai("b", "TASK:b", provider="claude"), []))  # a fixed model waits for it
        self.wait_for(lambda: engine.get(run_id)["nodes"]["b"]["status"] == "waiting_quota")
        self.assertNotIn("b", self.tags(), "no call was made to a blocked provider")
        engine.cancel(run_id)
        engine.wait(run_id, 10)

    def test_all_blocked_waits_for_the_first_reset(self):
        engine = self.engine(order=["claude", "codex"])
        now = time.time()
        engine.store.record_call("old", "x", "claude", now, "quota", now + 7200, "limit")
        engine.store.record_call("old", "y", "codex", now, "quota", now + 600, "limit")
        run_id = engine.start(workflow(ai("a", "TASK:a", provider="auto"), []))
        self.wait_for(lambda: engine.get(run_id)["nodes"]["a"]["status"] == "waiting_quota")
        self.assertEqual(engine.store.run(run_id)["providers"]["a"], "codex", "the one that resets first")
        self.assertEqual(self.tags(), [])
        engine.cancel(run_id)
        engine.wait(run_id, 10)

    def test_a_successful_call_clears_a_known_limit(self):
        engine = self.engine()
        engine.store.record_call("old", "x", "claude", time.time() - 5, "quota", time.time() + 3600, "limit")
        engine.store.record_call("old", "x", "claude", time.time(), "ok")
        self.assertEqual(engine.known_limits(), {})


class ConcurrencyTests(HomeCase):
    def test_calls_at_once_are_capped_over_all_runs(self):
        engine = Engine(self.home, adapter_cfg(codex={"concurrency": 1}), retry_delay=0)
        runs = [engine.start(workflow(ai("a", f"TASK:r{n} SLEEP=0.6", provider="codex"), [])) for n in range(3)]
        for run_id in runs:
            self.assertEqual(engine.wait(run_id, 30), "succeeded")
        spans = sorted((s, e) for _, s, e in self.calls())
        self.assertEqual(len(spans), 3)
        for (_, end), (start, _) in zip(spans, spans[1:]):
            self.assertGreaterEqual(start, end - 0.05, "one call at a time")


class PrivacyTests(HomeCase):
    def test_a_local_run_cannot_switch_to_a_cloud_model(self):
        engine = self.engine()
        run_id = engine.start(workflow(ai("a", "TASK:a", provider="ollama/qwen3:8b"), []),
                              privacy="local", launch=False)
        engine.store.update_node(run_id, "a", status="waiting_quota")
        with self.assertRaisesRegex(RunError, "accepts only local models"):
            engine.switch(run_id, "a", "claude")
        self.assertEqual(engine.get(run_id)["providers"]["a"], "ollama/qwen3:8b")

    def engine(self):
        cfg = adapter_cfg()
        cfg["providers"]["ollama"] = providers.spec("ollama", EMPTY)
        engine = Engine(self.home, cfg, retry_delay=0)
        engine.tool_states = lambda: states()
        return engine

    def test_privacy_local_refuses_a_cloud_model_and_auto_becomes_local(self):
        engine = self.engine()
        with self.assertRaises(RunError) as caught:
            engine.start(workflow(ai("a", "TASK:a", provider="claude"), []), privacy="local")
        self.assertIn("accepts only local models", str(caught.exception))
        with self.assertRaises(RunError):
            engine.start(workflow(ai("a", "TASK:a", provider="ollama/gpt-oss:120b-cloud"), []), privacy="local")
        text = "privacy: local\n" + workflow(ai("a", "TASK:a", provider="auto"), []).replace("schema_version: 1\n", "")
        wf = schema.parse("schema_version: 1\n" + text)
        providers_, auto = engine._resolve_providers(wf, {}, problems := [], "local")
        self.assertEqual((providers_["a"], auto["nodes"]), ("ollama/qwen3:8b", {"a": "auto:local"}), problems)

    def test_bad_privacy_value(self):
        with self.assertRaises(schema.WorkflowError):
            schema.parse(workflow(ai("a", "x"), [], head="privacy: cloud\n"))

    def test_estimate_says_where_each_step_goes(self):
        cfg = adapter_cfg()
        cfg["providers"]["ollama"] = providers.spec("ollama", EMPTY)
        wf = schema.parse(workflow(ai("a", "x", provider="claude/opus") + ai("b", "y", provider="auto:local")
                                   + ai("c", "z", provider="chatgpt"), []))
        out = estimate.estimate(wf, {}, cfg, resolve=lambda kind: "ollama/qwen3:8b")
        steps = {s["node"]: s for s in out["steps"]}
        self.assertEqual((steps["a"]["sent_to"], steps["a"]["local"]), ("Anthropic", False))
        self.assertEqual((steps["b"]["model"], steps["b"]["auto"], steps["b"]["local"]), ("ollama/qwen3:8b", "auto:local", True))
        self.assertEqual((steps["c"]["model"], steps["c"]["sent_to"]), ("codex", "OpenAI"))
        local = estimate.estimate(wf, {}, cfg, resolve=lambda kind: "ollama/qwen3:8b", privacy="local")
        self.assertEqual(local["refused"], 2)


class EveryStepTests(HomeCase):
    """"Model for every step": a person with one AI tool runs a workflow that names other tools."""
    FLOW = workflow(ai("a", "TASK:a", provider="nothere/opus@high", fallback_provider="chatgpt")
                    + ai("b", "TASK:b {{nodes.a.text}}", provider="'{{inputs.model}}'"), [("a", "b")],
                    inputs="  - {id: model, type: provider, default: claude}\n")

    def test_every_step_replaces_the_models_and_fallbacks_of_the_workflow(self):
        engine = self.engine()
        with self.assertRaises(RunError) as caught:
            engine.start(self.FLOW)  # the workflow names a tool that is not there
        self.assertIn("--every-step", str(caught.exception))
        run_id = engine.start(self.FLOW, every_step="fake")
        self.assertEqual(engine.wait(run_id, 30), "succeeded", engine.get(run_id)["error"])
        run = engine.get(run_id)
        self.assertEqual(run["providers"], {"a": "fake", "a:fallback": "fake", "b": "fake"})
        self.assertEqual(run["inputs"]["model"], "fake")
        self.assertEqual(len(self.calls()), 2)

    def test_every_step_may_be_auto_and_is_checked(self):
        engine = self.engine()
        wf = schema.parse(self.FLOW)
        found, auto = engine._resolve_providers(wf, {"model": "auto"}, problems := [], "", "auto")
        self.assertEqual((found["a"], found["b"], problems), ("claude", "claude", []))
        self.assertEqual(auto["nodes"], {"a": "auto", "b": "auto"})
        for bad in ("nothere", "{{inputs.model}}", "a b"):
            with self.subTest(bad=bad), self.assertRaises(RunError):
                engine.start(self.FLOW, every_step=bad)

    def test_the_estimate_shows_the_one_model(self):
        out = estimate.estimate(schema.parse(self.FLOW), {}, fake_cfg(), every_step="fake")
        self.assertEqual({s["node"]: s["model"] for s in out["steps"]}, {"a": "fake", "b": "fake"})


class WebTests(HomeCase):
    def test_get_and_put(self):
        from mehteran.web import App
        cfg = adapter_cfg()
        app = App(Engine(self.home, cfg, retry_delay=0))
        with mock.patch.object(providers, "statuses", lambda names=None, fresh=False: states(antigravity={"installed": False})):
            got = app.providers_get(None, {})
            self.assertTrue(got["order_is_default"])
            self.assertEqual(got["auto"]["auto"]["name"], "claude")
            self.assertEqual({p["name"]: p["billing"] for p in got["providers"]}, {"claude": "subscription", "codex": "subscription"})
            got = app.providers_put(None, {"order": ["codex/gpt-x", "claude"], "providers": {"codex": {"concurrency": 3, "api_key": True}}})
            self.assertEqual(got["order"], ["codex/gpt-x", "claude"])
            self.assertEqual(got["auto"]["auto"]["name"], "codex/gpt-x")
            from mehteran.web import HTTPError
            with self.assertRaises(HTTPError):
                app.providers_put(None, {"order": ["rm -rf /"]})
        self.assertEqual(providers.read_settings(self.home)["providers"]["codex"], {"api_key": True, "concurrency": 3})

    def test_setup_asks_the_tools_once_per_auto_kind(self):
        # Regression: dict.setdefault(kind, self._auto_now(kind)) asked every tool for its state once per template
        # input (109 times): the Setup tab, the welcome panel and the "not ready" banner waited 20 seconds.
        from mehteran.web import App
        app = App(Engine(self.home, adapter_cfg(), retry_delay=0))
        with mock.patch.object(App, "_auto_now", autospec=True, return_value="claude") as auto_now:
            used = app._used()
        self.assertIn("claude", used)
        self.assertGreater(len(used["claude"]), 20)  # the built-in templates use `auto`
        self.assertLessEqual(auto_now.call_count, len(providers.AUTO))


class WorkerEnvTests(HomeCase):
    def test_a_custom_provider_gets_no_key_either(self):
        cfg = fake_cfg()
        ctx = Ctx(run_dir=self.home / "executions" / "r", node_dir=self.tmp, node_id="a", config={}, value=str,
                  wrapped=str, provider="fake", provider_cfg=cfg, abort=None, timeout=1, attempt=1)
        from mehteran import nodes
        with mock.patch.dict(os.environ, {"OPENAI_API_KEY": "x" * 30}):
            self.assertNotIn("OPENAI_API_KEY", nodes._guarded_env(ctx, providers))
        self.assertEqual(FAKE[1].endswith("mehteran_fake_llm.py"), True)


class FakeLocalServer:
    """An OpenAI-compatible server on 127.0.0.1: /v1/models, /v1/chat/completions (SSE), /v1/away (a redirect)."""

    def __init__(self):
        import threading
        from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
        self.requests = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                if self.path == "/v1/models":
                    self._send(200, json.dumps({"data": [{"id": "qwen-local"}, {"id": "llama-3"}]}).encode())
                else:
                    self.send_response(302)
                    self.send_header("Location", "http://example.com/")
                    self.end_headers()

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                outer.requests.append(body)
                if self.path != "/v1/chat/completions":
                    self.send_response(307)
                    self.send_header("Location", "http://example.com/steal")
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                for piece in ("Hello ", "from the ", "local server."):
                    self.wfile.write(f"data: {json.dumps({'choices': [{'delta': {'content': piece}}]})}\n\n".encode())
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")

            def _send(self, code, data):
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_port}/v1"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def stop(self):
        self.server.shutdown()
        self.server.server_close()


class LocalServerTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.fake = FakeLocalServer()
        self.addCleanup(self.fake.stop)
        self.adapter = providers.ADAPTERS["openai-local"]

    def test_only_a_loopback_address_with_a_port(self):
        loop = providers.loopback_url
        self.assertEqual(loop("http://127.0.0.1:1234/v1/"), "http://127.0.0.1:1234/v1")
        self.assertEqual(loop("http://localhost:8080/v1"), "http://localhost:8080/v1")
        self.assertEqual(loop("http://[::1]:8000/v1"), "http://[::1]:8000/v1")
        for bad in ("http://192.168.1.5:1234/v1", "http://example.com:80/v1", "http://127.0.0.1/v1", "file:///etc/passwd",
                    "http://user:pw@127.0.0.1:1/v1", "http://127.0.0.1.example.com:80/", ""):
            self.assertIsNone(loop(bad), bad)

    def test_models_and_a_streamed_answer_without_a_proxy(self):
        self.assertEqual(self.adapter.list_models(self.fake.url), ["qwen-local", "llama-3"])
        pieces = []
        with mock.patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:9", "HTTP_PROXY": "http://127.0.0.1:9"}):
            answer = self.adapter.chat(self.fake.url, "qwen-local", "Say hello", "SYS", 30, pieces.append)
        self.assertEqual(answer, "Hello from the local server.")
        self.assertEqual(pieces, ["Hello ", "from the ", "local server."])
        sent = self.fake.requests[-1]
        self.assertEqual((sent["model"], sent["stream"], sent["messages"][0]), ("qwen-local", True, {"role": "system", "content": "SYS"}))

    def test_a_redirect_is_not_followed(self):
        with self.assertRaises(base.CallError):
            self.adapter.chat(self.fake.url.replace("/v1", "/away"), "m", "secret text", "SYS", 10)
        self.assertEqual(self.adapter.list_models(self.fake.url.replace("/v1", "/away")), [])

    def test_a_run_step_on_the_local_server(self):
        providers.write_settings(self.home, {"order": [], "providers": {"openai-local": {"url": self.fake.url, "model": "qwen-local"}}})
        cfg = adapter_cfg()
        cfg["providers"]["openai-local"] = providers.spec("openai-local", providers.read_settings(self.home))
        engine = Engine(self.home, cfg, retry_delay=0)
        run_id = engine.start(workflow(ai("ask", "Summarise this", provider="openai-local"), []), privacy="local")
        self.assertEqual(engine.wait(run_id, 30), "succeeded", engine.get(run_id)["nodes"]["ask"]["error"])
        run = engine.get(run_id)
        self.assertEqual((engine.run_dir(run_id) / run["nodes"]["ask"]["outputs"]["text"]).read_text(encoding="utf-8"),
                         "Hello from the local server.")
        self.assertIn("from the", engine.node_log(run_id, "ask")["text"])

    def test_put_refuses_an_address_off_this_computer(self):
        from mehteran.web import App, HTTPError
        app = App(Engine(self.home, adapter_cfg(), retry_delay=0))
        with mock.patch.object(providers, "statuses", lambda names=None, fresh=False: states()):
            with self.assertRaises(HTTPError):
                app.providers_put(None, {"providers": {"openai-local": {"url": "http://10.0.0.2:1234/v1"}}})
            app.providers_put(None, {"providers": {"openai-local": {"url": self.fake.url, "model": "llama-3"}}})
        self.assertEqual(providers.read_settings(self.home)["providers"]["openai-local"], {"url": self.fake.url, "model": "llama-3"})


if __name__ == "__main__":
    unittest.main()
