"""Mehteran templates: the two namespaces, customize, import/export, and the built-in templates end to end."""

import hashlib
import shutil
import sys
import unittest
import zipfile
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase  # noqa: E402
from test_mehteran_common import make_docx  # noqa: E402

from mehteran import paths, schema, templates  # noqa: E402
from mehteran.templates import TemplateError  # noqa: E402

BUILTINS = ("academic-paper-review", "document-comparison")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class TemplateTests(HomeCase):
    def test_used_builtin_resolves_after_removal(self):
        ident = "academic-paper-review"
        text = templates.read("builtin", ident, self.home)
        templates.remember_builtin("builtin:" + ident, text, self.home)
        with mock.patch.object(paths, "BUILTIN_TEMPLATES", self.tmp / "updated-builtins"):
            self.assertEqual(templates.resolve("builtin:" + ident, self.home), ("builtin", ident))
            self.assertEqual(templates.read("builtin", ident, self.home), text)
            self.assertIn(ident, templates.ids("builtin", self.home))

    def test_older_run_recovers_removed_builtin(self):
        from mehteran_support import ai, workflow
        engine = self.engine()
        text = workflow(ai("check", "TASK:check"), []).replace("id: test-flow", "id: removed")
        run_id = engine.start(text, launch=False)
        engine.store.update_run(run_id, template="builtin:removed")
        templates.recover_used_builtins(engine)
        self.assertEqual(templates.read("builtin", "removed", self.home), text)

    def test_builtins_are_listed_valid_and_read_only(self):
        items = {item["ref"]: item for item in templates.listing(paths.home())}
        for template_id in BUILTINS:
            item = items[f"builtin:{template_id}"]
            self.assertTrue(item["valid"], item["problems"])
            self.assertEqual(item["source"], "builtin")
        before = sha(paths.BUILTIN_TEMPLATES / "academic-paper-review.yaml")
        text = templates.read("builtin", "academic-paper-review", self.home)
        with self.assertRaises(TemplateError) as e:
            templates.save("academic-paper-review", text, self.home)
        self.assertEqual(e.exception.code, 403)
        with self.assertRaises(TemplateError):
            templates.delete("builtin", "academic-paper-review", self.home)
        self.assertEqual(sha(paths.BUILTIN_TEMPLATES / "academic-paper-review.yaml"), before)

    def test_customize_keeps_a_version_with_special_characters_as_text(self):
        text = templates.read("builtin", "document-comparison", self.home).replace('version: "1.2"', "version: 'a\\g<0>\\9'")
        templates.import_text(templates.with_id(text, "odd"), self.home)
        templates.customize("user", "odd", "odd2", self.home)
        self.assertIn("based_on: user:odd@a\\g<0>\\9\n", templates.read("user", "odd2", self.home))

    def test_merged_template_ids_still_work_as_aliases(self):
        for old, new in templates.ALIASES.items():
            with self.subTest(old=old):
                self.assertIn(new, templates.ids("builtin", self.home))
                self.assertNotIn(old, templates.ids("builtin", self.home))
                self.assertEqual(templates.resolve(old, self.home), ("builtin", new))
                self.assertEqual(templates.resolve(f"builtin:{old}", self.home), ("builtin", new))
                self.assertEqual(templates.canonical_ref(f"builtin:{old}"), f"builtin:{new}")
        item = next(i for i in templates.listing(self.home) if i["id"] == "document-summary")
        self.assertEqual(item["aliases"], ["chapter-summaries", "multi-length-summary"])

    def test_pasted_text_runs_without_the_optional_file(self):
        engine = self.engine()
        text = templates.read("builtin", "email-reply-draft", self.home)
        run_id = engine.start(text, {"thread": "Can you send the offer by Friday?", "language": "en", "model": "fake"}, {})
        self.assertEqual(engine.wait(run_id, 60), "succeeded", engine.get(run_id)["error"])

    def test_customize_makes_an_independent_copy(self):
        templates.customize("builtin", "academic-paper-review", "my-review", self.home)
        copy = self.home / "templates" / "my-review.yaml"
        wf = schema.parse(copy.read_text(encoding="utf-8"))
        self.assertEqual(wf.id, "my-review")
        self.assertEqual(wf.data["based_on"], "builtin:academic-paper-review@1.1")
        self.assertIn("# Built-in template", copy.read_text(encoding="utf-8"))  # comments and layout are kept

        # A later update of the built-in template does not touch the copy.
        fake_builtins = self.tmp / "builtins"
        shutil.copytree(paths.BUILTIN_TEMPLATES, fake_builtins)
        updated = fake_builtins / "academic-paper-review.yaml"
        updated.write_text(updated.read_text(encoding="utf-8").replace('version: "1.1"', 'version: "2.0"'), encoding="utf-8")
        mine_before = sha(copy)
        with mock.patch.object(paths, "BUILTIN_TEMPLATES", fake_builtins):
            items = {i["ref"]: i for i in templates.listing(self.home)}
            self.assertEqual(items["builtin:academic-paper-review"]["version"], "2.0")
            self.assertEqual(items["user:my-review"]["version"], "1.1")
        self.assertEqual(sha(copy), mine_before)

        # Editing the copy keeps its id; an invalid edit is refused with all problems.
        text = copy.read_text(encoding="utf-8").replace('version: "1.1"', 'version: "1.2"')
        templates.save("my-review", text, self.home)
        with self.assertRaises(TemplateError) as e:
            templates.save("my-review", text.replace("id: my-review", "id: other") + "junk: 1\n", self.home)
        self.assertTrue(any("junk" in m for m in e.exception.messages))
        with self.assertRaises(TemplateError) as e:
            templates.save("my-review", text.replace("id: my-review", "id: other"), self.home)
        self.assertIn("must match", e.exception.messages[0])
        templates.delete("user", "my-review", self.home)
        self.assertFalse(copy.exists())

    def test_ids_cannot_collide_across_namespaces(self):
        with self.assertRaises(TemplateError) as e:
            templates.customize("builtin", "document-comparison", "academic-paper-review", self.home)
        self.assertEqual(e.exception.code, 409)
        templates.customize("builtin", "document-comparison", "mine", self.home)
        with self.assertRaises(TemplateError):
            templates.customize("builtin", "document-comparison", "mine", self.home)
        with self.assertRaises(TemplateError):
            templates.customize("builtin", "document-comparison", "../evil", self.home)
        # Should a later built-in take the same id, a bare id is ambiguous and the prefix decides.
        fake_builtins = self.tmp / "builtins"
        shutil.copytree(paths.BUILTIN_TEMPLATES, fake_builtins)
        shutil.copyfile(self.home / "templates" / "mine.yaml", fake_builtins / "mine.yaml")
        with mock.patch.object(paths, "BUILTIN_TEMPLATES", fake_builtins):
            with self.assertRaises(TemplateError):
                templates.resolve("mine", self.home)
            self.assertEqual(templates.resolve("user:mine", self.home), ("user", "mine"))

    def test_import_and_export(self):
        text = templates.read("builtin", "document-comparison", self.home)  # export = the file text
        with self.assertRaises(TemplateError):
            templates.import_text(text, self.home)  # its id is a built-in id
        new_id = templates.import_text(templates.with_id(text, "compare-two"), self.home)
        self.assertEqual(new_id, "compare-two")
        self.assertEqual(templates.resolve("compare-two", self.home), ("user", "compare-two"))
        with self.assertRaises(TemplateError) as e:
            templates.import_text("schema_version: 1\nid: x\nname: x\nnodes: [{id: a, type: nope}]\n", self.home)
        self.assertIn("unknown node type", e.exception.messages[0])

    def test_academic_paper_review_runs_end_to_end(self):
        paper = self.tmp / "paper.docx"
        make_docx(paper)
        engine = self.engine()
        text = templates.read("builtin", "academic-paper-review", self.home)
        run_id = engine.start(text, {"language": "tr", "focus": "TASK:ignored", "model": "fake/large", "editor_model": "fake"},
                              {"paper": paper}, template="builtin:academic-paper-review")
        self.assertEqual(engine.wait(run_id, 60), "succeeded", engine.get(run_id)["error"])
        run = engine.get(run_id)
        self.assertEqual(run["providers"], {"methodology": "fake/large", "citations": "fake/large", "clarity": "fake/large",
                                            "synthesis": "fake"})
        self.assertEqual(len(self.calls()), 4)
        run_dir = engine.run_dir(run_id)
        outputs = run["nodes"]["export"]["outputs"]
        self.assertEqual(set(outputs), {"md", "docx", "html"})
        report = (run_dir / outputs["md"]).read_text(encoding="utf-8")
        self.assertEqual(report.count("## Answer"), 4)
        with zipfile.ZipFile(run_dir / outputs["docx"]) as z:
            self.assertIn("word/document.xml", z.namelist())
        self.assertIn("<html", (run_dir / outputs["html"]).read_text(encoding="utf-8"))
        # The paper's text reached the reviewers, inside a data block, with the chosen output language.
        prompts = "".join(p.read_text(encoding="utf-8") for p in self.prompts.iterdir())
        self.assertIn("Namaz dinin direğidir.", prompts)
        self.assertIn('with the code "tr"', prompts)

    def test_document_comparison_runs_end_to_end(self):
        first = self.doc("v1.md", "# Contract\n\nNotice period: 30 days.\n\nPrice: 100 EUR.")
        second = self.doc("v2.txt", "# Contract\n\nNotice period: 7 days.\n\nPrice: 100 EUR.")
        engine = self.engine()
        text = templates.read("builtin", "document-comparison", self.home)
        run_id = engine.start(text, {"mode": "pair", "language": "en", "model": "fake", "writer_model": "claude"},
                          {"documents": [first, second]})
        self.assertEqual(engine.wait(run_id, 60), "succeeded", engine.get(run_id)["error"])
        run = engine.get(run_id)
        self.assertEqual(len(self.calls()), 2)
        compare = next(p for p in self.prompts.iterdir() if "Notice period: 30 days" in p.read_text(encoding="utf-8"))
        prompt = compare.read_text(encoding="utf-8")
        self.assertIn("Notice period: 7 days", prompt)
        self.assertIn("v1.md", prompt)
        report = (engine.run_dir(run_id) / run["nodes"]["export"]["outputs"]["md"]).read_text(encoding="utf-8")
        self.assertEqual(report.count("## Answer"), 2)
        self.assertTrue((engine.run_dir(run_id) / "nodes" / "export" / "comparison-report.docx").is_file())


if __name__ == "__main__":
    unittest.main()
