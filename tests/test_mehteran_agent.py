"""Browser agent steps (ai.agent, mehteran/browser.py) and the X share step (share.x).

No browser starts and no model is called: the Claude Code adapter runs the fake Claude Code (mehteran_fake_claude.py),
and the browser's MCP configuration is replaced where a test needs one.
"""

import json
import os
import sys
import time
import unittest
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, adapter_cfg, ai, workflow  # noqa: E402

from mehteran import browser, i18n, nodes, schema  # noqa: E402
from mehteran.engine import Engine, RunError  # noqa: E402
from mehteran.providers import ADAPTERS, base  # noqa: E402

AGENT = "  - {id: look, type: ai.agent, config: {provider: claude, sites: 'example.com', prompt: 'TASK:look Read it.'%s}}\n"


def tool_use(name: str, **data) -> str:
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": f"mcp__browser__{name}", "input": data}]}})


def tool_result(text: str) -> str:
    return json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "content": [{"type": "text", "text": text}]}]}})


class BrowserRulesTests(unittest.TestCase):
    def test_sites_become_host_names(self):
        self.assertEqual(browser.site_hosts("x.com\nhttps://www.Reddit.com/r/x\n# off\nnews.ycombinator.com, example.org\n\n"),
                         ["x.com", "reddit.com", "news.ycombinator.com", "example.org"])

    def test_only_the_sites_and_their_subdomains_are_allowed(self):
        hosts = ["example.com"]
        for url in ("https://example.com/a", "http://www.example.com", "https://docs.example.com/x", "about:blank"):
            self.assertTrue(browser.host_allowed(url, hosts), url)
        for url in ("https://example.org", "https://notexample.com", "https://example.com.evil.org/", "file:///etc/passwd",
                    "javascript:alert(1)", "chrome://settings"):
            self.assertFalse(browser.host_allowed(url, hosts), url)

    def test_an_address_that_a_browser_reads_differently_is_refused(self):
        # Python's urlsplit takes the part after "@" as the host; a browser reads "\" as "/" and drops tabs, so these
        # go to evil.org in Chrome. Refused: a backslash, white space or a control character, a user part ("@").
        hosts = ["example.com"]
        for url in ("https://evil.org\\@example.com/", "https://evil.org\t\\@example.com/", "https://evil.org/@example.com",
                    "https://user@example.com/", "https://exa mple.com/", "https://example.com\x00.evil.org/",
                    "https://ex%61mple.com/"):
            self.assertFalse(browser.host_allowed(url, hosts), repr(url))
        self.assertTrue(browser.host_allowed("https://example.com./path", hosts))  # the root dot is the same host

    def test_the_guard_stops_on_another_site_and_logs_each_action(self):
        check = browser.guard(["example.com"])
        self.assertEqual(check(tool_use("browser_navigate", url="https://example.com/x")),
                         (None, "browser_navigate https://example.com/x"))
        stop, _ = check(tool_use("browser_navigate", url="https://evil.org/"))
        self.assertIn("evil.org", stop)
        stop, _ = check(tool_result("### Page\n- Page URL: https://evil.org/after-a-click\n- Page Title: x"))
        self.assertIn("evil.org", stop)  # a click on a link that left the sites
        self.assertEqual(check(tool_result("### Page\n- Page URL: https://www.example.com/\n")), (None, None))
        self.assertEqual(check("not json"), (None, None))

    def test_read_steps_cannot_type_and_no_step_runs_code_or_uploads(self):
        read, act = browser.allowed_tools("read"), browser.allowed_tools("act")
        self.assertIn("mcp__browser__browser_navigate", read)
        self.assertNotIn("mcp__browser__browser_type", read)
        self.assertIn("mcp__browser__browser_type", act)
        for tool in ("browser_evaluate", "browser_run_code_unsafe", "browser_file_upload", "browser_drop"):
            self.assertNotIn(f"mcp__browser__{tool}", act)

    def test_the_browser_waits_for_heavy_pages_and_skips_ads(self):
        # Playwright MCP waits 5 s per action by default: hotel and listing pages were not ready in time.
        with mock.patch.object(browser, "node", lambda: (Path("node"), None)), \
                mock.patch.object(browser, "chrome", lambda: Path("chrome")), \
                mock.patch.object(Path, "is_file", lambda self: True), mock.patch.object(Path, "mkdir", lambda *a, **k: None):
            args = browser.mcp_config(Path("home"), Path("out"), ["example.com"], False)["mcpServers"]["browser"]["args"]
        self.assertEqual(args[args.index("--timeout-action") + 1], "20000")
        self.assertEqual(args[args.index("--timeout-navigation") + 1], "90000")
        self.assertIn("https://*.doubleclick.net", args[args.index("--blocked-origins") + 1].split(";"))
        self.assertNotIn("--allowed-origins", args)  # not a security boundary; guard() stops the step instead

    def test_the_sign_in_browser_takes_only_a_web_address_and_never_a_flag(self):
        # An address that starts with "-" would be read by Chrome as a switch (--remote-debugging-port=...).
        launched = []
        with mock.patch.object(browser, "chrome", lambda: Path("chrome")), \
                mock.patch.object(Path, "mkdir", lambda *a, **k: None), \
                mock.patch.object(browser.subprocess, "Popen", lambda argv, **k: launched.append(argv)):
            for bad in ("--remote-debugging-port=9222", "file:///etc/passwd", "javascript:alert(1)", "chrome://settings"):
                with self.assertRaises(browser.ToolError, msg=bad):
                    browser.open_signin(Path("home"), bad)
            self.assertEqual(launched, [])
            browser.open_signin(Path("home"), "https://x.com/login")
            browser.open_signin(Path("home"))
        self.assertEqual(launched[0][-2:], ["--", "https://x.com/login"])
        self.assertEqual(launched[1][-2:], ["--", "about:blank"])

    def test_an_agent_step_keeps_its_longer_timeout(self):
        # A browser agent reads many pages: the 1200 s of a model call cut it off before it could write its report.
        from mehteran.engine import step_timeout
        agent, cli = nodes.REGISTRY["ai.agent"], nodes.REGISTRY["ai.cli"]
        self.assertEqual(step_timeout({"config": {"provider": "auto"}}, agent, {"timeout": 1200}), 1800)
        self.assertEqual(step_timeout({"config": {"provider": "auto"}}, agent, {"timeout": 3000}), 3000)
        self.assertEqual(step_timeout({"config": {"provider": "auto"}}, cli, {"timeout": 900}), 900)  # the user's own
        self.assertEqual(step_timeout({"config": {"provider": "auto"}, "timeout": 60}, agent, {}), 60)

    def test_the_lock_file_pins_the_version_with_integrity_sums(self):
        lock = json.loads((browser.LOCK_DIR / "package-lock.json").read_text(encoding="utf-8"))
        self.assertEqual(lock["packages"]["node_modules/@playwright/mcp"]["version"], browser.VERSION)
        self.assertTrue(all(spec.get("integrity", "").startswith("sha512-")
                            for name, spec in lock["packages"].items() if name))

    def test_claude_code_runs_an_agent_step_with_only_the_browser(self):
        argv = ADAPTERS["claude"].agent_argv("haiku", "", Path("out"), Path("mcp.json"), ["mcp__browser__browser_navigate"])
        for flag in ("--restricted", "--strict-mcp-config", "--no-session-persistence"):
            self.assertIn(flag, argv)
        self.assertEqual(argv[argv.index("--mcp-config") + 1], "mcp.json")
        self.assertEqual(argv[argv.index("--tools") + 1], "")
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "dontAsk")
        self.assertEqual(argv[argv.index("--allowedTools") + 1], "mcp__browser__browser_navigate")
        self.assertFalse({"--dangerously-skip-permissions", "--allow-dangerously-skip-permissions", "--safe-mode"} & set(argv))
        self.assertIsNone(ADAPTERS["codex"].agent_argv("", "", Path("o"), Path("m"), []))

    def test_a_guard_kills_the_tool_at_once(self):
        script = "import time\nprint('one', flush=True)\nprint('STOP', flush=True)\ntime.sleep(30)\nprint('never')"
        started = time.monotonic()
        with self.assertRaises(base.Stopped) as caught:
            base._stream([sys.executable, "-c", script], "", 60, Path.cwd(), dict(os.environ), None,
                         lambda line: "left the sites" if "STOP" in line else None)
        self.assertEqual(str(caught.exception), "left the sites")
        self.assertLess(time.monotonic() - started, 15)


class AgentSchemaTests(unittest.TestCase):
    def test_a_step_that_types_needs_an_approval_before_it(self):
        with self.assertRaises(schema.WorkflowError) as caught:
            schema.parse(workflow(AGENT % ", mode: act", []))
        self.assertIn("nodes.look.config.mode", str(caught.exception.messages()))
        approved = workflow("  - {id: ok, type: approval}\n" + AGENT % ", mode: act", [("ok", "look")])
        schema.parse(approved)
        schema.parse(workflow(AGENT % "", []))  # read only: no approval needed
        with self.assertRaises(schema.WorkflowError):
            schema.parse(workflow("  - {id: look, type: ai.agent, config: {provider: claude, prompt: x}}\n", []))


class AgentRunTests(HomeCase):
    def adapter_engine(self) -> Engine:
        engine = Engine(self.home, adapter_cfg(), retry_delay=0)
        engine.awake = False
        engine.tool_states = lambda: {name: {"installed": True, "signed_in": True, "billing": "subscription"}
                                      for name in ADAPTERS}
        return engine

    def test_only_claude_code_runs_an_agent_step(self):
        engine = self.engine()
        with self.assertRaises(RunError) as caught:
            engine.start(workflow(AGENT.replace("provider: claude", "provider: fake") % "", []))
        self.assertIn("Claude Code", str(caught.exception))
        # "Model for every step" with another tool does not reach the browser agent: it keeps Claude Code
        self.assertEqual(engine.get(engine.start(workflow(AGENT % "", []), every_step="fake", launch=False))["providers"]["look"], "claude")
        # only models on this computer: one clear reason (a browser agent reads sites), not two
        with self.assertRaises(RunError) as caught:
            engine.start(workflow(AGENT % "", []), privacy="local")
        self.assertEqual(caught.exception.messages, [f"nodes.look: {i18n.t('agent_not_local')}"])
        run_id = engine.start(workflow(AGENT % "", []))  # "claude" of the test configuration is a plain command
        self.assertEqual(engine.wait(run_id, 30), "failed")
        self.assertIn("Claude Code", engine.get(run_id)["nodes"]["look"]["error"])

    def test_a_missing_browser_fails_the_step_with_what_to_install(self):
        engine = self.adapter_engine()
        with mock.patch.dict(os.environ, {"MEHTERAN_RUNTIME_ROOT": str(self.tmp / "runtime")}):
            run_id = engine.start(workflow(AGENT % "", []))
            self.assertEqual(engine.wait(run_id, 30), "failed")
        error = engine.get(run_id)["nodes"]["look"]["error"]
        self.assertTrue("Node.js" in error or "not installed" in error or "Chrome" in error, error)

    def test_the_call_gets_the_browser_and_only_its_tools(self):
        engine = self.adapter_engine()
        argv_log = self.tmp / "argv.jsonl"
        fake_config = lambda home, out, hosts, headless: {"mcpServers": {"browser": {"command": "node", "args": hosts}}}  # noqa: E731
        with mock.patch.object(browser, "mcp_config", fake_config), \
                mock.patch.dict(os.environ, {"MEHTERAN_FAKE_ARGV": str(argv_log)}):
            run_id = engine.start(workflow(AGENT % "", []))
            self.assertEqual(engine.wait(run_id, 30), "succeeded", engine.get(run_id)["error"])
        args = json.loads(argv_log.read_text(encoding="utf-8").splitlines()[-1])
        self.assertIn("--restricted", args)
        self.assertEqual(args[args.index("--allowedTools") + 1:args.index("--permission-mode")], browser.allowed_tools("read"))
        node_dir = engine.run_dir(run_id) / "nodes" / "look"
        self.assertEqual(json.loads((node_dir / "browser-mcp.json").read_text())["mcpServers"]["browser"]["args"], ["example.com"])
        prompt = (node_dir / "prompt.txt").read_text(encoding="utf-8")
        self.assertIn("Open only these sites and their subdomains: example.com", prompt)
        self.assertIn("Do not change anything on any site", prompt)


class ShareTests(HomeCase):
    FLOW = workflow(ai("post", "TASK:post Write.")
                    + "  - {id: share, type: share.x, config: {text: '{{nodes.post.text}}'}}\n", [("post", "share")])

    def test_the_link_opens_x_with_the_text_and_the_run_page_shows_it(self):
        engine = self.engine()
        run_id = engine.start(self.FLOW)
        self.assertEqual(engine.wait(run_id, 30), "succeeded", engine.get(run_id)["error"])
        node = engine.get(run_id)["nodes"]["share"]
        url = (engine.run_dir(run_id) / node["outputs"]["url"]).read_text(encoding="utf-8").strip()
        text = (engine.run_dir(run_id) / "nodes" / "post" / "text.md").read_text(encoding="utf-8").strip()
        self.assertTrue(url.startswith(nodes.X_INTENT))
        self.assertEqual(parse_qs(urlsplit(url).query)["text"], [text])
        from mehteran.web import App
        shares = App(engine).run_get([None, run_id], {})["shares"]
        self.assertEqual([(s["node"], s["url"], s["text"]) for s in shares], [("share", url, text)])


if __name__ == "__main__":
    unittest.main()
