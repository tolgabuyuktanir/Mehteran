"""Every built-in Mehteran template: valid, well described, honest about what a model can do, and runs end to end.

The runs use the fake AI tool (tests/mehteran_fake_llm.py) and a temporary MEHTERAN_HOME; no real model is called.
"""

import re
import sys
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase  # noqa: E402

from mehteran import nodes, paths, schema, templates, urlfetch  # noqa: E402

CATEGORIES = {"research", "documents", "legal", "business", "data", "writing", "education", "web", "exams", "developers"}
EXPORT_FORMATS = {"md", "docx", "html"}  # the main result; another export may add a PDF or an e-mail draft
EXTRA_FORMATS = {"pdf", "eml", "md"}
SAMPLE_FEED = (b'<?xml version="1.0"?><rss version="2.0"><channel><title>Sample feed</title><item><title>A model'
               b' was released</title><link>https://example.com/a</link><pubDate>Fri, 14 Nov 2025 09:30:00 +0000'
               b'</pubDate><description>The lab released a model.</description></item></channel></rss>')


def fake_fetch(url, abort=None):
    """No network in the tests: every address (a feed of a news template) gives the same small RSS feed."""
    return url, "application/rss+xml", "utf-8", SAMPLE_FEED
# A model step gets only its prompt: no template may claim or ask for a web search or browsing.
NO_WEB = re.compile(r"\bweb\b|\binternet\b|\bbrows(e|er|ing)\b|\bonline\b|search engine|\bgoogle\b", re.I)
SAMPLE_TEXT = "# Sample\n\nThe parties agree to deliver 10 units by 1 March 2025 for 100 EUR.\n\nA,B\n1,2\n"


def builtin_ids() -> list[str]:
    return sorted(p.stem for p in paths.BUILTIN_TEMPLATES.glob("*.yaml"))


def localized_ok(value) -> bool:
    return isinstance(value, dict) and all(isinstance(value.get(k), str) and value[k].strip() for k in ("tr", "en"))


class BuiltinTemplateTests(HomeCase):
    def load(self, template_id: str) -> schema.Workflow:
        return schema.parse(templates.read("builtin", template_id, self.home))

    def test_there_are_many_builtins_with_unique_ids(self):
        ids = builtin_ids()
        self.assertGreaterEqual(len(ids), 27)
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(sorted(templates.ids("builtin", self.home)), ids)

    def test_each_builtin_is_valid_and_well_described(self):
        listed = {item["ref"]: item for item in templates.listing(self.home)}
        for template_id in builtin_ids():
            with self.subTest(template=template_id):
                self.assertTrue(listed[f"builtin:{template_id}"]["valid"], listed[f"builtin:{template_id}"]["problems"])
                wf = self.load(template_id)
                self.assertEqual(wf.id, template_id)
                self.assertTrue(localized_ok(wf.data["name"]), "name needs tr and en")
                self.assertTrue(localized_ok(wf.data.get("description")), "description needs tr and en")
                self.assertIn(wf.data.get("category"), CATEGORIES)
                self.assertTrue(str(wf.data.get("version") or "").strip())
                self.assertTrue(3 <= len(wf.nodes) <= 10, len(wf.nodes))
                for input_id, spec in wf.inputs.items():
                    self.assertTrue(localized_ok(spec.get("label")), f"input {input_id} needs a tr and en label")
                language = wf.inputs.get("language")
                self.assertIsNotNone(language, "a report language input")
                self.assertEqual(language["type"], "language")  # every language of the registry; no options
                self.assertTrue(any(s["type"] == "provider" for s in wf.inputs.values()))
                exports = [set(n["config"]["formats"]) for n in wf.nodes.values() if n["type"] == "document.export"]
                self.assertIn(EXPORT_FORMATS, exports)
                for formats in exports:
                    self.assertTrue(formats == EXPORT_FORMATS or formats <= EXTRA_FORMATS, formats)

    def test_start_here_group_is_small_and_general(self):
        core = [i for i in builtin_ids() if self.load(i).data.get("tier") == "core"]
        self.assertTrue(15 <= len(core) <= 25, len(core))
        for template_id in core:
            self.assertNotIn(self.load(template_id).data["category"], {"exams"}, template_id)

    def test_prompts_do_not_mention_web_access(self):
        for template_id in builtin_ids():
            wf = self.load(template_id)
            for node_id, node in wf.nodes.items():
                if node["type"] in ("ai.cli", "ai.map"):
                    with self.subTest(template=template_id, node=node_id):
                        self.assertIsNone(NO_WEB.search(node["config"]["prompt"]))

    def test_legal_templates_say_they_are_not_legal_advice(self):
        for template_id in builtin_ids():
            wf = self.load(template_id)
            if wf.data["category"] != "legal":
                continue
            with self.subTest(template=template_id):
                prompts = " ".join(n["config"]["prompt"] for n in wf.nodes.values() if n["type"] == "ai.cli")
                self.assertIn("not legal advice", re.sub(r"[\s>]+", " ", prompts))

    def test_each_builtin_runs_end_to_end(self):
        engine = self.engine()
        # No network and no browser: feeds give a sample feed; a browser agent step runs on the fake tool.
        with mock.patch.object(urlfetch, "fetch", fake_fetch), mock.patch.object(nodes, "agent_supported", lambda spec: True):
            for template_id in builtin_ids():
                with self.subTest(template=template_id):
                    self.run_builtin(engine, template_id)

    def run_builtin(self, engine, template_id: str) -> None:
        text = templates.read("builtin", template_id, self.home)
        wf = schema.parse(text)
        values, files = {}, {}
        for input_id, spec in wf.inputs.items():
            if spec["type"] == "file":
                formats = spec.get("formats", list(schema.FILE_FORMATS))
                ext = next(f for f in ("md", "txt", "csv") if f in formats)
                files[input_id] = self.doc(f"{template_id}-{input_id}.{ext}", SAMPLE_TEXT)
            elif spec["type"] == "text" and spec.get("required", True) and not str(spec.get("default") or "").strip():
                values[input_id] = f"Sample value for {input_id}"
        before = len(self.calls())
        run_id = engine.start(text, values, files, template=f"builtin:{template_id}")
        status = engine.wait(run_id, 120)
        approvals = 0
        while status == "waiting_approval":
            for node_id, info in engine.get(run_id)["nodes"].items():
                if info["status"] == "waiting_approval":
                    engine.decide(run_id, node_id, True, "Approved in the test.")
                    approvals += 1
            status = engine.wait(run_id, 120)
        run = engine.get(run_id)
        self.assertEqual(status, "succeeded", run["error"])
        self.assertEqual(approvals, sum(n["type"] == "approval" for n in wf.nodes.values()))
        run_dir = engine.run_dir(run_id)
        # One call per AI step that ran (a condition may skip a branch), one per part of a loop.
        expected = sum(n["type"] in ("ai.cli", "ai.agent") and run["nodes"][i]["status"] == "succeeded" for i, n in wf.nodes.items())
        expected += sum(len(list((run_dir / "nodes" / i / "parts").glob("*.md"))) for i, n in wf.nodes.items()
                        if n["type"] == "ai.map")
        self.assertEqual(len(self.calls()) - before, expected)
        for node_id, node in wf.nodes.items():
            if node["type"] != "document.export" or run["nodes"][node_id]["status"] == "skipped":
                continue  # a PDF that was not asked for
            outputs = run["nodes"][node_id]["outputs"]
            self.assertEqual(set(outputs), set(node["config"]["formats"]))
            if "md" in outputs:
                self.assertIn("## Answer", (run_dir / outputs["md"]).read_text(encoding="utf-8"))
            if "docx" in outputs:
                with zipfile.ZipFile(run_dir / outputs["docx"]) as z:
                    self.assertIn("word/document.xml", z.namelist())
            if "html" in outputs:
                self.assertIn("<html", (run_dir / outputs["html"]).read_text(encoding="utf-8"))
            if "eml" in outputs:
                self.assertIn(b"X-Unsent: 1", (run_dir / outputs["eml"]).read_bytes())


if __name__ == "__main__":
    unittest.main()
