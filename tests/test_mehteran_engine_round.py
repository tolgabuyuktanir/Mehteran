"""Engine round: empty inputs, Ollama context guard, keep-awake, loop stop on a usage limit, resume at start,
loop headings in the run's language, error summary. Fake tools only."""

import sys
import time
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_mehteran_local as local  # noqa: E402
from mehteran_support import HomeCase, ai, workflow  # noqa: E402

from mehteran import engine as engine_module, ollama  # noqa: E402
from mehteran.engine import Engine, error_summary  # noqa: E402
from mehteran.ollama import OllamaError  # noqa: E402

EXPORT = "  - {id: save, type: document.export, config: {formats: [md]}}\n"
BOOK = "# One\n\nAlpha.\n\n# Two\n\nBeta.\n\n# Three\n\nGamma.\n\n# Four\n\nDelta.\n"


class EmptyInputTests(HomeCase):
    def run_flow(self, text, values=None):
        engine = self.engine()
        run_id = engine.start(text, values or {})
        engine.wait(run_id, 30)
        return engine.get(run_id)

    def test_export_with_an_empty_source_fails_clearly(self):
        # The reviewer's case: three nodes, none connected. Nothing may be written.
        text = workflow(ai("a", "TASK:a") + EXPORT + "  - {id: b, type: text.merge, config: {template: x}}\n", [])
        run = self.run_flow(text)
        self.assertEqual(run["status"], "failed")
        self.assertEqual(run["nodes"]["save"]["status"], "failed")
        self.assertIn("text to save is empty", run["nodes"]["save"]["error"])
        self.assertEqual(list((self.home / "executions").glob("*/nodes/save/*.md")), [])

    def test_export_of_a_connected_empty_text_fails(self):
        text = workflow("  - {id: e, type: text.merge, config: {template: \"  \"}}\n" + EXPORT, [("e.text", "save")])
        self.assertEqual(self.run_flow(text)["nodes"]["save"]["status"], "failed")

    def test_ai_step_with_only_empty_input_fails_but_an_instruction_only_step_runs(self):
        empty = "  - {id: e, type: text.merge, config: {template: \"  \"}}\n"
        run = self.run_flow(workflow(empty + ai("a", "TASK:a Summarise."), [("e.text", "a")]))
        self.assertEqual(run["nodes"]["a"]["status"], "failed")
        self.assertIn("input of this step is empty", run["nodes"]["a"]["error"])
        self.assertEqual(self.tags(), [])  # the model was not called
        run = self.run_flow(workflow(ai("a", "TASK:a Write a haiku."), []))
        self.assertEqual(run["status"], "succeeded")


class OllamaGuardTests(local.LocalCase):
    def test_context_grows_with_the_prompt_up_to_the_model_maximum(self):
        with mock.patch.object(ollama, "memory", return_value=64 * ollama.GB):
            ollama.chat("qwen2.5:0.5b", "word " * 6000, "sys", 30)  # 30000 chars: more than 8192 tokens with room
            small = ollama.chat("qwen2.5:0.5b", "hi", "sys", 30)
        chats = [r for r in self.fake.requests if r["path"] == "/api/chat"]
        self.assertGreater(chats[0]["options"]["num_ctx"], 8192)
        self.assertLessEqual(chats[0]["options"]["num_ctx"], 32768)
        self.assertEqual(chats[1]["options"]["num_ctx"], 8192)
        self.assertTrue(small)

    def test_ram_caps_the_context(self):
        with mock.patch.object(ollama, "memory", return_value=4 * ollama.GB):
            ollama.chat("qwen2.5:0.5b", "word " * 1500, "sys", 30)
        chat = next(r for r in self.fake.requests if r["path"] == "/api/chat")
        self.assertEqual(chat["options"]["num_ctx"], 4096)

    def test_a_document_that_fills_the_context_fails_instead_of_being_cut(self):
        self.fake.context_length = 8192
        with mock.patch.object(ollama, "memory", return_value=64 * ollama.GB):
            with self.assertRaises(OllamaError) as e:
                ollama.chat("qwen2.5:0.5b", "word " * 20000, "sys", 30)
        self.assertIn("too long for this model", str(e.exception))
        self.assertIn("loop step", str(e.exception))


class KeepAwakeTests(HomeCase):
    def test_runs_keep_the_computer_awake_once(self):
        engine = self.engine()
        engine.awake = True
        with mock.patch.object(Engine, "_awake_started", False), mock.patch.object(engine_module.system, "keep_awake") as awake:
            for _ in range(2):
                run_id = engine.start(workflow(ai("a", "TASK:a"), []))
                engine.wait(run_id, 30)
        self.assertEqual(awake.call_count, 1)


class LoopTests(HomeCase):
    LOOP = workflow(
        "  - id: each\n    type: ai.map\n    retries: 0\n    config:\n      source: \"{{inputs.text}}\"\n"
        "      split: headings\n      provider: fake\n      prompt: \"TASK:part{{item.index}} MARK {{item.text}}\"\n",
        [], inputs="  - {id: text, type: text}\n  - {id: language, type: language}\n")

    def test_a_usage_limit_in_one_part_starts_no_other_part(self):
        engine = self.engine(quota_delay=1.5, parallel=1)
        run_id = engine.start(self.LOOP.replace("MARK", f"QUOTA=1:{self.tmp / 'q'}"), {"text": BOOK, "language": "en"})
        self.wait_for(lambda: engine.get(run_id)["nodes"]["each"]["status"] == "waiting_quota")
        self.assertEqual(self.tags(), [])  # before the fix the other three parts were answered meanwhile
        self.assertEqual(engine.wait(run_id, 60), "succeeded", engine.get(run_id)["error"])
        self.assertEqual(len(set(self.tags())), 4)

    def test_part_headings_follow_the_language_of_the_run(self):
        from mehteran import i18n
        for language, heading in (("tr", "## Bölüm 1"), ("en", "## Part 1")):
            engine = self.engine()
            i18n.set_default("en")  # the interface language is not the run's language
            run_id = engine.start(self.LOOP.replace("headings", "paragraphs"), {"text": "a\n\nb", "language": language})
            self.assertEqual(engine.wait(run_id, 30), "succeeded", engine.get(run_id)["error"])
            out = engine.get(run_id)["nodes"]["each"]["outputs"]["text"]
            self.assertIn(heading, (engine.run_dir(run_id) / out).read_text(encoding="utf-8"))


class ResumeAtStartTests(HomeCase):
    def test_restart_preserves_a_pending_quota_deadline(self):
        first = self.engine()
        run_id = first.start(workflow(ai("a", "TASK:a"), []), launch=False)
        deadline = time.time() + 60
        first.store.update_run(run_id, status="running")
        first.store.update_node(run_id, "a", status="waiting_quota", quota_until=deadline)
        second = self.engine()
        self.assertEqual(second.resume_interrupted(), [run_id])
        try:
            self.wait_for(lambda: second.get(run_id)["nodes"]["a"]["status"] == "waiting_quota")
            # the column is TEXT: an older SQLite keeps 15 significant digits (about 10 µs here)
            self.assertAlmostEqual(float(second.get(run_id)["nodes"]["a"]["quota_until"]), deadline, delta=0.001)
            self.assertTrue(second.list()[0]["waiting_quota"])
            self.assertEqual(self.calls(), [])
        finally:
            second.cancel(run_id)
            second.wait(run_id, 10)

    def test_a_run_left_running_is_resumed_and_a_cancelled_one_is_not(self):
        first = self.engine()
        done = first.start(workflow(ai("a", "TASK:a"), []))
        self.assertEqual(first.wait(done, 30), "succeeded")
        cancelled = first.start(workflow(ai("a", "TASK:a"), []))
        first.wait(cancelled, 30)
        first.store.update_run(done, status="running", finished=None)  # the process ended while it ran
        first.store.update_node(done, "a", status="running", finished=None)
        first.store.update_run(cancelled, status="cancelled")
        second = self.engine()
        self.assertEqual(second.resume_interrupted(), [done])
        self.assertEqual(second.wait(done, 30), "succeeded")
        self.assertEqual(second.get(cancelled)["status"], "cancelled")

    def test_the_setting_is_off_until_it_is_written(self):
        self.assertFalse(engine_module.resume_on_start())
        folder = self.home / "configurations"
        folder.mkdir(parents=True)
        (folder / "engine.toml").write_text("resume_interrupted = true\n", encoding="utf-8")
        self.assertTrue(engine_module.resume_on_start())


class ErrorSummaryTests(unittest.TestCase):
    def test_the_last_meaningful_line_and_one_line_errors(self):
        trace = ("Traceback (most recent call last):\n  File \"x.py\", line 3, in <module>\n    boom()\n"
                 "ValueError: the file is not a PDF\n")
        self.assertEqual(error_summary(trace), "ValueError: the file is not a PDF")
        self.assertEqual(error_summary("one line"), "one line")
        self.assertEqual(error_summary(None), "")
        self.assertEqual(error_summary("a\nb", key="some_key"), "a\nb")

    def test_a_failed_step_carries_the_summary_and_the_full_text(self):
        case = HomeCase()
        case.setUp()
        try:
            engine = case.engine()
            run_id = engine.start(workflow(ai("a", f"TASK:a FAIL=3:{case.tmp / 'f'}", retries=0), []))
            engine.wait(run_id, 30)
            node = engine.get(run_id)["nodes"]["a"]
            self.assertEqual(node["error_summary"], node["error"].splitlines()[-1])
        finally:
            case.doCleanups()


if __name__ == "__main__":
    unittest.main()
