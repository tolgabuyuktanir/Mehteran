"""The evaluation set's rules and runner (mehteran/evals.py), with the fake AI tool: no real model is called."""

import json
import shutil
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, fake_cfg  # noqa: E402

from mehteran import evals, schema, templates  # noqa: E402


class RuleTests(unittest.TestCase):
    def test_checks(self):
        text = "Kooperatif 1.240 ton zeytin işledi ve bu yüzde 18 fazladır. Bu bir özettir."
        self.assertEqual(evals.check(text, {"language": "tr", "any_of": [["1.240", "1240"], ["YÜZDE 18"]]}), [])
        failed = evals.check(text, {"language": "en", "any_of": [["4,2 milyon"]], "not_contains": ["zeytin"],
                                    "not_regex": [r"\d+ ton"], "min_chars": 500})
        self.assertEqual(len(failed), 5, failed)
        self.assertEqual(evals.language_of("The meeting agreed to delay the launch and the owner is not stated."), "en")
        self.assertEqual(evals.fold("İŞLEDİ Işık"), "isledi isik")

    def test_compare(self):
        before = {"results": [{"id": "a", "passed": False, "failed": ["missing: x"]}, {"id": "b", "passed": True, "failed": []}]}
        after = {"results": [{"id": "a", "passed": True, "failed": []}, {"id": "b", "passed": True, "failed": []},
                             {"id": "c", "passed": False, "failed": ["run failed"]}]}
        lines = evals.compare(before, after)
        self.assertTrue(lines[0].startswith("↑ a"))
        self.assertTrue(lines[1].startswith("+ c"))
        self.assertEqual(evals.compare(after, after), ["no change"])


class CaseFileTests(HomeCase):
    def test_every_case_names_a_builtin_template_its_inputs_and_existing_files(self):
        cases = json.loads(evals.CASES.read_text(encoding="utf-8"))["cases"]
        self.assertGreaterEqual(len(cases), 5)
        self.assertEqual(len({c["id"] for c in cases}), len(cases))
        for case in cases:
            wf = schema.parse(templates.read("builtin", case["template"], self.home))
            for group in ("files", "texts", "values"):
                for key, rel in (case.get(group) or {}).items():
                    self.assertIn(key, wf.inputs, (case["id"], key))
                    if group != "values":
                        for one in rel if isinstance(rel, list) else [rel]:
                            self.assertTrue((evals.CASES.parent / one).is_file(), (case["id"], one))
            self.assertTrue(case["checks"], case["id"])
            self.assertEqual(set(case["checks"]) - {"language", "any_of", "not_contains", "not_regex", "min_chars", "max_chars"},
                             set(), case["id"])

    def test_a_case_runs_with_the_fake_tool_and_is_checked(self):
        """The runner with one case on the fake tool: it runs, approves, reads the export and checks it."""
        case = {"id": "fake", "template": "meeting-minutes-actions", "files": {"notes": "docs/project-sync-notes.md"},
                "values": {"language": "en"}, "checks": {"min_chars": 1}}
        cases = self.tmp / "evals" / "cases.json"  # next to the real docs/ folder, as evals/cases.json is
        cases.parent.mkdir()
        shutil.copytree(evals.CASES.parent / "docs", cases.parent / "docs")  # a copy: Windows may refuse a link
        cases.write_text(json.dumps({"cases": [case]}), encoding="utf-8")
        with mock.patch.object(evals, "CASES", cases):
            report = evals.run("fake", out=self.tmp / "reports", say=lambda *_: None, timeout=120, provider_cfg=fake_cfg())
        self.assertEqual(report["cases"], 1)
        found = report["results"][0]
        self.assertEqual(found["status"], "succeeded", found)
        self.assertTrue(found["result"])
        self.assertTrue(Path(report["path"]).is_file())


if __name__ == "__main__":
    unittest.main()
