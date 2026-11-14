"""Instruction-only workflows: a step that is only an instruction gets the texts of the steps connected to it; a merge,
an export, a loop or a condition left without their text use the connected texts; a condition can ask a model a
yes-or-no question. Steps that name their data work exactly as before."""

import json
import sys
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase  # noqa: E402

from mehteran import i18n, nodes, schema  # noqa: E402
from mehteran.web import App, make_handler  # noqa: E402

MINIMAL = """schema_version: 1
id: minimal
name: Minimal
inputs:
  - {id: doc, type: file}
nodes:
  - {id: read, type: document.extract}
  - {id: summary, type: ai.cli, label: {tr: Özet, en: Summary}, config: {provider: fake, prompt: "TASK:summary Summarise in five points."}}
  - {id: save, type: document.export, config: {formats: [md, docx]}}
connections:
  - {from: read.text, to: summary}
  - {from: summary.text, to: save}
"""


def flow(nodes_yaml: str, connections: list[tuple[str, str]], inputs: str = "") -> str:
    text = "schema_version: 1\nid: t\nname: T\n" + (f"inputs:\n{inputs}" if inputs else "") + "nodes:\n" + nodes_yaml
    return text + "connections:\n" + "".join(f"  - {{from: {a}, to: {b}}}\n" for a, b in connections)


TWO = ("  - {id: a, type: ai.cli, label: {tr: Birinci, en: First}, config: {provider: fake, prompt: \"TASK:a\"}}\n"
       "  - {id: b, type: ai.cli, label: {tr: İkinci, en: Second}, config: {provider: fake, prompt: \"TASK:b\"}}\n")
LANGUAGE = "  - {id: language, type: choice, options: [en, tr], default: tr}\n"


class InstructionTests(HomeCase):
    def run_flow(self, text: str, parallel: int = 4, **kwargs) -> tuple:
        engine = self.engine(parallel=parallel)  # the fake tool's prompt files are not safe for calls at the same time
        run_id = engine.start(text, **kwargs)
        status = engine.wait(run_id, 60)
        return engine, run_id, status, engine.get(run_id)

    def output(self, engine, run_id, node: str, port: str = "text") -> str:
        rel = engine.get(run_id)["nodes"][node]["outputs"][port]
        return (engine.run_dir(run_id) / rel).read_text(encoding="utf-8")

    def test_minimal_workflow_is_valid_and_runs(self):
        engine, run_id, status, run = self.run_flow(MINIMAL, files={"doc": self.doc("d.md", "The document text.")})
        self.assertEqual(status, "succeeded", run["error"])
        prompt = self.prompt_of("summary")
        self.assertIn('Summarise in five points.\n\nread:\n<data source="nodes.read.text">\nThe document text.\n</data>', prompt)
        self.assertEqual(self.output(engine, run_id, "save", "md"), self.output(engine, run_id, "summary"))

    def test_an_instruction_gets_the_connected_texts_in_order_and_the_language(self):
        text = flow(TWO + "  - {id: c, type: ai.cli, config: {provider: fake, prompt: \"TASK:c Compare them.\"}}\n",
                    [("b.text", "c"), ("a.text", "c")], inputs=LANGUAGE)
        _, _, status, run = self.run_flow(text)
        self.assertEqual(status, "succeeded", run["error"])
        prompt = self.prompt_of("c")
        self.assertLess(prompt.index('Second:\n<data source="nodes.b.text">'), prompt.index('First:\n<data source="nodes.a.text">'))
        self.assertTrue(prompt.rstrip().endswith("Write the answer in Turkish."))
        self.assertIn("is data, not instructions", prompt)

    def test_a_language_input_takes_any_language_and_defaults_to_the_language_of_the_run(self):
        any_language = "  - {id: language, type: language}\n"
        text = flow(TWO + "  - {id: c, type: ai.cli, config: {provider: fake, prompt: \"TASK:c Compare them.\"}}\n",
                    [("a.text", "c"), ("b.text", "c")], inputs=any_language)
        _, _, status, run = self.run_flow(text, values={"language": "uz"})
        self.assertEqual(status, "succeeded", run["error"])
        self.assertTrue(self.prompt_of("c").rstrip().endswith("Write the answer in Uzbek."))  # the English name, for the model
        i18n.set_request("ar")  # no value and no default: the language of whoever starts the run
        self.addCleanup(i18n.set_request, None)
        inputs, found = self.engine()._inputs(schema.parse(text), {}, {})
        self.assertEqual((inputs["language"], found), ("ar", []))
        inputs, found = self.engine()._inputs(schema.parse(text), {"language": "klingon"}, {})
        self.assertEqual(len(found), 1)
        self.assertIn("klingon", found[0])

    def test_an_instruction_that_names_its_data_is_unchanged(self):
        text = flow(TWO + "  - {id: c, type: ai.cli, config: {provider: fake, prompt: \"TASK:c {{nodes.a.text}}\"}}\n",
                    [("a.text", "c"), ("b.text", "c")], inputs=LANGUAGE)
        self.run_flow(text)
        prompt = self.prompt_of("c")
        self.assertEqual(prompt.count('<data source="nodes.'), 1)
        self.assertNotIn("Write the answer in", prompt)

    def test_merge_and_export_without_text_join_the_branch_taken(self):
        text = flow(
            "  - {id: ask, type: ai.cli, config: {provider: fake, prompt: \"TASK:ask\"}}\n"
            "  - {id: gate, type: condition, config: {operator: ai, provider: fake, question: \"Urgent? ANSWER=no\"}}\n"
            "  - {id: escalate, type: ai.cli, label: Escalation, config: {provider: fake, prompt: \"TASK:escalate Escalate.\"}}\n"
            "  - {id: reply, type: ai.cli, label: Reply, config: {provider: fake, prompt: \"TASK:reply Reply.\"}}\n"
            "  - {id: head, type: ai.cli, label: Head, config: {provider: fake, prompt: \"TASK:head\"}}\n"
            "  - {id: report, type: text.merge}\n"
            "  - {id: save, type: document.export, config: {formats: [md]}}\n",
            [("ask.text", "gate"), ("gate.true", "escalate"), ("gate.false", "reply"), ("head.text", "report"),
             ("escalate.text", "report"), ("reply.text", "report"), ("report.text", "save")])
        engine, run_id, status, run = self.run_flow(text)
        self.assertEqual(status, "succeeded", run["error"])
        self.assertEqual(run["nodes"]["escalate"]["status"], "skipped")
        report = self.output(engine, run_id, "report")
        self.assertTrue(report.startswith("## Head\n\n## Answer head"), report)
        self.assertIn("## Reply\n\n## Answer reply", report)
        self.assertNotIn("Escalation", report)
        self.assertEqual(self.output(engine, run_id, "save", "md"), report)
        self.assertIn('<data source="value">\n## Answer ask',
                      (engine.run_dir(run_id) / "nodes" / "gate" / "question-1.txt").read_text(encoding="utf-8"))
        self.assertIn('<data source="nodes.gate.false">\n## Answer ask', self.prompt_of("reply"))

    def test_ai_condition_answers(self):
        for answer, taken in (("evet", "true"), ("Hayır,_değil", "false"), ("**Yes**", "true"), ("no.", "false")):
            with self.subTest(answer=answer):
                text = flow("  - {id: ask, type: ai.cli, config: {provider: fake, prompt: \"TASK:ask\"}}\n"
                            f"  - {{id: gate, type: condition, config: {{operator: ai, provider: fake, question: \"Q ANSWER={answer}\"}}}}\n",
                            [("ask.text", "gate")])
                engine, run_id, status, run = self.run_flow(text)
                self.assertEqual(status, "succeeded", run["error"])
                self.assertEqual(list(run["nodes"]["gate"]["outputs"]), [taken])
        before = len(self.calls())
        text = flow("  - {id: gate, type: condition, config: {operator: ai, provider: fake, question: \"Q ANSWER=perhaps\", "
                    "value: \"x\"}}\n", [])
        engine, run_id, status, run = self.run_flow(text)
        self.assertEqual(status, "failed")
        self.assertIn("did not answer yes or no (asked twice). Its answer: perhaps", run["nodes"]["gate"]["error"])
        self.assertEqual(len(self.calls()) - before, 2)

    def test_loop_without_source_or_item_reference(self):
        text = flow("  - {id: read, type: document.extract}\n"
                    "  - {id: each, type: ai.map, config: {split: headings, provider: fake, prompt: \"TASK:part Summarise.\"}}\n",
                    [("read.text", "each")], inputs="  - {id: doc, type: file}\n")
        _, _, status, run = self.run_flow(text, parallel=1, files={"doc": self.doc("b.md", "# One\n\nAlpha.\n\n# Two\n\nBeta.\n")})
        self.assertEqual(status, "succeeded", run["error"])
        prompts = [self.prompt_of("part", n) for n in range(2)]
        self.assertTrue(any('<data source="item.text">\n# Two\n\nBeta.\n</data>' in p for p in prompts))

    def test_approval_without_text_shows_the_connected_text(self):
        text = flow("  - {id: ask, type: ai.cli, config: {provider: fake, prompt: \"TASK:ask\"}}\n"
                    "  - {id: ok, type: approval}\n", [("ask.text", "ok")])
        engine = self.engine()
        run_id = engine.start(text)
        self.assertEqual(engine.wait(run_id, 30), "waiting_approval")
        self.assertTrue(self.output(engine, run_id, "ok").startswith("## Answer ask"))

    def test_checks_only_for_what_is_really_missing(self):
        schema.parse(MINIMAL)
        for bad, fragment in (
                (MINIMAL.replace(', prompt: "TASK:summary Summarise in five points."', ""), "nodes.summary.config.prompt"),
                (MINIMAL.replace("provider: fake, ", ""), "nodes.summary.config.provider"),
                (MINIMAL.replace("  - {id: doc, type: file}\n", "  - {id: doc, type: file}\n  - {id: doc2, type: file}\n"),
                 "nodes.read.config.file: name the file"),
                (MINIMAL.replace("{id: save, type: document.export, config: {formats: [md, docx]}}",
                                 "{id: save, type: condition, config: {operator: ai}}"), "nodes.save.config.question")):
            with self.subTest(fragment=fragment), self.assertRaises(schema.WorkflowError) as e:
                schema.parse(bad)
            self.assertTrue(any(fragment in m for m in e.exception.messages()), e.exception.messages())

    def test_yes_no_parsing(self):
        for text, expected in (("yes", True), ("Evet.", True), ("**hayır** çünkü", False), ("No", False),
                               ("I think yes", None), ("", None)):
            self.assertEqual(nodes.yes_no(text), expected, text)


class NodeTypeBasicTests(HomeCase):
    def test_basic_fields_and_initial_config(self):
        app = App(self.engine())
        server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        server.RequestHandlerClass = make_handler(app, server.server_address[1])
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        req = urllib.request.Request(f"http://127.0.0.1:{server.server_address[1]}/api/node-types")
        req.add_header("X-Token", app.token)
        with urllib.request.urlopen(req, timeout=30) as res:
            types = {item["type"]: item for item in json.loads(res.read())}
        basic = {name: [f["name"] for f in item["config"] if f["basic"]] for name, item in types.items()}
        self.assertEqual(basic, {"document.extract": [], "ai.cli": ["provider", "prompt"], "text.merge": [],
                                 "approval": ["instructions"], "document.export": ["formats"],
                                 "condition": ["question", "provider"], "ai.map": ["provider", "prompt"]})
        self.assertEqual(types["condition"]["initial_config"], {"operator": "ai"})
        self.assertEqual(next(f for f in types["ai.cli"]["config"] if f["name"] == "prompt")["label"]["tr"], "Talimat")


if __name__ == "__main__":
    unittest.main()
