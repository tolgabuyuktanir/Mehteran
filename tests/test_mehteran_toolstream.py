"""The output of a command-line AI tool in the node's live log while the tool runs (mehteran/toolstream.py, the
on_output of mehteran/providers/base.py run). Fake AI tools and a temporary MEHTERAN_HOME; no real model, no network."""

import json
import sys
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, adapter_cfg, ai, workflow  # noqa: E402

from mehteran import providers, toolstream  # noqa: E402
from mehteran.engine import Engine  # noqa: E402
from mehteran.providers import base  # noqa: E402


class LiveOutputInTheEngineTests(HomeCase):
    def check_live(self, provider: str):
        engine = Engine(self.home, adapter_cfg(), retry_delay=0)
        run_id = engine.start(workflow(ai("ask", "TASK:ask STREAM=3:0.8", provider=provider), []))
        self.wait_for(lambda: "stream line 1 of 3" in engine.node_log(run_id, "ask")["text"])
        self.assertEqual(self.calls(), [], "the tool has not ended yet")
        self.assertNotIn("Fake answer", engine.node_log(run_id, "ask")["text"])
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        text = engine.node_log(run_id, "ask")["text"]
        self.assertIn("stream line 3 of 3", text)
        self.assertEqual(text.count("Fake answer from model default for ask."), 1, text)
        self.assertNotIn('"type"', text, "stream-json events are shown as their text")
        return engine, run_id

    def test_plain_output_codex(self):
        self.check_live("codex")

    def test_stream_json_claude_and_its_usage_report(self):
        engine, run_id = self.check_live("claude")
        usage = json.loads((self.home / "configurations" / "usage.json").read_text(encoding="utf-8"))
        self.assertEqual(usage["claude"]["source"], "claude-rate-limit-event")
        self.assertEqual(usage["claude"]["status"], "allowed")


class OnOutputTests(HomeCase):
    def call(self, name: str, prompt: str, timeout: float = 60, on_output=None) -> str:
        cfg = adapter_cfg()
        return base.run(providers.ADAPTERS[name], cfg["providers"][name], "", "", prompt, timeout, on_output)[0]

    def test_the_answer_is_the_same_with_and_without_on_output(self):
        prompt = "TASK:same STREAM=2:0.4 çeviri «بسم الله»"
        plain = self.call("codex", prompt)
        seen = []
        streamed = self.call("codex", prompt, on_output=lambda line: seen.append((time.time(), line)))
        self.assertEqual(streamed, plain)
        self.assertEqual("".join(line for _, line in seen).strip(), plain)
        ended = self.calls()[-1][2]
        self.assertLess(seen[0][0], ended, "the first line arrived while the tool still ran")
        self.assertEqual(self.call("claude", prompt), plain, "the same answer from stream-json")

    def test_a_broken_callback_does_not_stop_the_call_and_the_timeout_holds(self):
        def broken(line):
            raise RuntimeError("log full")

        self.assertIn("Fake answer", self.call("claude", "TASK:cb STREAM=1:0", on_output=broken))
        started = time.time()
        with self.assertRaises(base.CallError) as caught:
            self.call("claude", "TASK:slow STREAM=1:0 SLEEP=20", timeout=1, on_output=lambda line: None)
        self.assertLess(time.time() - started, 10)
        self.assertIn("1", str(caught.exception))

    def test_a_usage_limit_is_detected(self):
        with self.assertRaises(base.UsageLimit) as plain:
            self.call("codex", f"TASK:q QUOTA=1:{self.tmp / 'q'}")
        self.assertGreater(plain.exception.until, time.time())
        with self.assertRaises(base.UsageLimit) as event:  # Claude Code: the rejected rate_limit_event
            self.call("claude", f"TASK:q QUOTA=1:{self.tmp / 'q2'}")
        self.assertAlmostEqual(event.exception.until, time.time() + 90, delta=5)


def lines(*events) -> list[str]:
    return [json.dumps(e) + "\n" for e in events]


class EventTextTests(unittest.TestCase):
    def test_claude_code_stream_json_becomes_text(self):
        events = lines(
            {"type": "system", "subtype": "init", "tools": ["Read"], "model": "claude"},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello "},
                                                          {"type": "tool_use", "name": "Read", "input": {}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "content": "file text"}]}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "world."}]}},
            {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"}},
            {"type": "result", "subtype": "success", "is_error": False, "result": "Hello world."})
        converter = toolstream.EventText()
        self.assertEqual("".join(converter.feed(line) for line in events), "Hello \n· tool: Read\nworld.")

    def test_partial_messages_are_shown_once(self):
        events = lines(
            {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hel"}}},
            {"type": "stream_event", "event": {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "lo"}}},
            {"type": "stream_event", "event": {"type": "content_block_start",
                                               "content_block": {"type": "tool_use", "name": "Grep"}}},
            {"type": "stream_event", "event": {"type": "content_block_delta",
                                               "delta": {"type": "input_json_delta", "partial_json": "{\"a\""}}},
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "Hello"},
                                                          {"type": "tool_use", "name": "Grep"}]}},
            {"type": "result", "subtype": "error_max_turns", "is_error": True, "result": "Claude AI usage limit reached"})
        converter = toolstream.EventText()
        self.assertEqual("".join(converter.feed(line) for line in events),
                         "Hello\n· tool: Grep\n\n· Claude AI usage limit reached\n")

    def test_antigravity_events_and_plain_lines(self):
        events = lines(
            {"event": "init", "init": {"cwd": "/tmp", "tools": []}},
            {"event": "step_update", "step_update": {"step_type": "agent_response", "text_delta": "Hal"}},
            {"event": "step_update", "step_update": {"step_type": "agent_response", "text_delta": "lo"}},
            {"event": "result", "result": {"status": "SUCCESS", "response": "Hallo"}})
        converter = toolstream.EventText()
        self.assertEqual("".join(converter.feed(line) for line in events), "Hallo")
        failed = lines({"event": "result", "result": {"status": "ERROR", "error": "no access"}})
        self.assertEqual(toolstream.EventText().feed(failed[0]), "\n· no access\n")
        self.assertEqual(toolstream.EventText().feed("not json\n"), "not json\n")

    def test_stream_json_is_read_from_the_command(self):
        self.assertTrue(toolstream.uses_stream_json(["claude", "-p", "--output-format", "stream-json", "--verbose"]))
        self.assertFalse(toolstream.uses_stream_json(["claude", "-p", "--output-format", "text"]))
        self.assertFalse(toolstream.uses_stream_json(["codex", "exec", "-o", "{output}"]))


class LiveOutputTests(HomeCase):
    def test_a_secret_split_across_pieces_is_still_masked(self):
        log = self.tmp / "log.txt"
        out = toolstream.LiveOutput(log, ["agy", "--output-format", "stream-json"])
        text = "word " * 50 + "key sk-ant-abcdefghij" + "klmnopqrstuv and Bearer abcd" + "efgh12345678 end"
        for piece in (text[i:i + 7] for i in range(0, len(text), 7)):
            out.feed(json.dumps({"event": "step_update", "step_update": {"text_delta": piece}}) + "\n")
        self.assertTrue(log.exists(), "a long line is written before it ends")
        self.assertEqual(out.close(), text)
        written = log.read_text(encoding="utf-8")
        self.assertNotIn("abcdefghijklmnop", written)
        self.assertNotIn("efgh12345678", written)
        self.assertIn("[hidden]", written)
        self.assertTrue(written.endswith(" end\n"))

    def test_parts_of_a_loop_write_whole_lines_with_their_label(self):
        log = self.tmp / "log.txt"
        out = toolstream.LiveOutput(log, ["codex", "exec"], prefix="part 2: ")
        out.feed("first line\n")
        out.feed("x" * 300)
        self.assertEqual(log.read_text(encoding="utf-8"), "part 2: first line\n")
        out.feed("y\n")
        out.close()
        self.assertEqual(log.read_text(encoding="utf-8"), "part 2: first line\npart 2: " + "x" * 300 + "y\n")

    def test_same_text(self):
        self.assertTrue(toolstream.same_text("stream line\n## Answer\n\nText.\n", "## Answer\n\nText."))
        self.assertFalse(toolstream.same_text("Hallo", "Hallo world"))
        self.assertFalse(toolstream.same_text("", ""))


if __name__ == "__main__":
    unittest.main()
