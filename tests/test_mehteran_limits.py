"""Mehteran without its first-slice limits: drafts, several files, CSV/TSV/Excel input, conditions, loops, waiting
for a usage limit, tables in reports, comments kept by the visual editor, and the node-type list.

Fake AI tool and a temporary MEHTERAN_HOME (tests/mehteran_support.py); no real model, no network."""

import io
import json
import re
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, ai, fake_config_toml, workflow  # noqa: E402

from mehteran import cli, nodes, schema, tables, templates, yamlio  # noqa: E402
from mehteran.engine import RunError  # noqa: E402
from mehteran.web import App, make_handler  # noqa: E402


def xlsx(path: Path, sheets: dict, hidden: tuple = (), date_cells: tuple = ()) -> Path:
    """A minimal .xlsx: {sheet name: rows}. Strings go to sharedStrings, numbers stay numbers; date_cells
    ((sheet, "B2"), ...) get a date style."""
    strings: list[str] = []
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    rel_ns = 'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    with zipfile.ZipFile(path, "w") as z:
        book, rels = [], []
        for n, (name, rows) in enumerate(sheets.items(), 1):
            state = ' state="hidden"' if name in hidden else ""
            book.append(f'<sheet name="{name}" sheetId="{n}" r:id="rId{n}"{state}/>')
            rels.append(f'<Relationship Id="rId{n}" Type="x" Target="worksheets/sheet{n}.xml"/>')
            xml_rows = []
            for r, row in enumerate(rows, 1):
                cells = []
                for c, value in enumerate(row):
                    ref = f"{chr(65 + c)}{r}"
                    style = ' s="1"' if (name, ref) in date_cells else ""
                    if isinstance(value, (int, float)):
                        cells.append(f'<c r="{ref}"{style}><v>{value}</v></c>')
                    elif value.startswith("inline:"):
                        cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{value[7:]}</t></is></c>')
                    else:
                        strings.append(value)
                        cells.append(f'<c r="{ref}" t="s"><v>{len(strings) - 1}</v></c>')
                xml_rows.append(f'<row r="{r}">{"".join(cells)}</row>')
            z.writestr(f"xl/worksheets/sheet{n}.xml", f'<worksheet {ns}><sheetData>{"".join(xml_rows)}</sheetData></worksheet>')
        z.writestr("xl/workbook.xml", f'<workbook {ns} {rel_ns}><sheets>{"".join(book)}</sheets></workbook>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{"".join(rels)}</Relationships>')
        z.writestr("xl/sharedStrings.xml", f'<sst {ns}>{"".join(f"<si><t>{s}</t></si>" for s in strings)}</sst>')
        z.writestr("xl/styles.xml", f'<styleSheet {ns}><cellXfs><xf numFmtId="0"/><xf numFmtId="14"/></cellXfs></styleSheet>')
    return path


class TableReadingTests(HomeCase):
    def test_csv_with_commas_or_semicolons_and_tsv(self):
        text = tables.read(self.doc("a.csv", "name,amount\nAda,10\n\"Lovelace, A\",2|3\n"))
        self.assertEqual(text.splitlines()[:2], ["| name | amount |", "|---|---|"])
        self.assertIn("| Lovelace, A | 2\\|3 |", text)
        self.assertIn("| Ada | 10 |", tables.read(self.doc("b.csv", "name;amount\nAda;10\nBob;7\n")))
        self.assertIn("| Ada | 10 |", tables.read(self.doc("c.tsv", "name\tamount\nAda\t10\n")))
        latin = self.tmp / "d.csv"
        latin.write_bytes("şehir,nüfus\nİzmir,4\n".encode("cp1254"))
        self.assertIn("| İzmir | 4 |", tables.read(latin))

    def test_big_tables_are_cut_with_a_note(self):
        rows = "\n".join(f"{i},{i * 2}" for i in range(tables.MAX_ROWS + 25))
        text = tables.read(self.doc("big.csv", "a,b\n" + rows))
        self.assertEqual(text.count("\n| "), tables.MAX_ROWS)
        self.assertIn(f"only the first {tables.MAX_ROWS} of {tables.MAX_ROWS + 25} rows", text)
        wide = tables.read(self.doc("wide.csv", ",".join(f"c{i}" for i in range(tables.MAX_COLS + 5)) + "\n"))
        self.assertIn(f"first {tables.MAX_COLS} of {tables.MAX_COLS + 5} columns", wide)
        with self.assertRaises(tables.TableError):
            tables.read(self.doc("empty.csv", "\n\n"))

    def test_xlsx_sheets_strings_numbers_dates(self):
        path = xlsx(self.tmp / "book.xlsx", {
            "Sales": [["Region", "Total", "Day"], ["North", 1250, 45292], ["inline:South", 3.5, 45293]],
            "Secret": [["x"]], "Empty": [], "Notes": [["Note"], ["A | B"]]},
            hidden=("Secret",), date_cells=(("Sales", "C2"), ("Sales", "C3")))
        text = tables.read(path)
        self.assertIn("## Sales\n\n| Region | Total | Day |", text)
        self.assertIn("| North | 1250 | 2024-01-01 |", text)
        self.assertIn("| South | 3.5 | 2024-01-02 |", text)
        self.assertIn("## Notes", text)
        self.assertIn("A \\| B", text)
        self.assertNotIn("Secret", text)
        self.assertNotIn("Empty", text)
        broken = self.tmp / "broken.xlsx"
        broken.write_bytes(b"not a zip")
        with self.assertRaises(tables.TableError):
            tables.read(broken)

    def test_xlsx_with_entities_is_refused(self):
        good = xlsx(self.tmp / "good.xlsx", {"S": [["a"]]})
        path = self.tmp / "evil.xlsx"
        with zipfile.ZipFile(good) as source, zipfile.ZipFile(path, "w") as z:
            for name in source.namelist():
                z.writestr(name, '<!DOCTYPE x [<!ENTITY a "aaaa">]><worksheet/>' if name.endswith("sheet1.xml")
                           else source.read(name))
        with self.assertRaises(tables.TableError):
            tables.read(path)


class ExportTableTests(HomeCase):
    MD = "# Report\n\nIntro text.\n\n| Item | Cost |\n|:---|---:|\n| **Rent** | 1,000 |\n| A \\| B | 5 |\n\nAfter.\n"

    def test_html_and_docx_have_real_tables(self):
        page = tables.to_html(self.MD, "R", "en")
        self.assertIn('<table class="md">', page)
        self.assertIn("<th>Item</th>", page)
        self.assertIn('<td style="text-align: right">1,000</td>', page)
        self.assertIn("<strong>Rent</strong>", page)
        self.assertIn("<td>A | B</td>", page)
        self.assertNotIn("MTBL", page)
        self.assertIn("<p>After.</p>", page)
        with zipfile.ZipFile(io.BytesIO(tables.to_docx(self.MD, "R", "en"))) as z:
            document = z.read("word/document.xml").decode()
        self.assertEqual(document.count("<w:tbl>"), 1)
        self.assertEqual(document.count("<w:tr>"), 3)
        self.assertNotIn("MTBL", document)
        self.assertIn("After.", document)

    def test_no_table_in_code_blocks_or_without_separator(self):
        md = "```\n| a | b |\n|---|---|\n```\n\nx | y\n\n---\n"
        self.assertEqual(tables.extract(md)[1], {})

    def test_export_node_writes_tables(self):
        text = workflow("  - {id: save, type: document.export, config: {source: " + json.dumps(self.MD)
                        + ", formats: [md, docx, html]}}\n", [])
        engine = self.engine()
        run_id = engine.start(text)
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        out = engine.get(run_id)["nodes"]["save"]["outputs"]
        self.assertIn("<table", (engine.run_dir(run_id) / out["html"]).read_text(encoding="utf-8"))
        self.assertIn("| Item | Cost |", (engine.run_dir(run_id) / out["md"]).read_text(encoding="utf-8"))


MULTI = workflow(
    "  - {id: extract, type: document.extract, config: {file: \"{{inputs.docs}}\"}}\n"
    + ai("compare", "TASK:compare {{nodes.extract.text}}"),
    [("extract.text", "compare")],
    inputs="  - {id: docs, type: file, multiple: true, formats: [md, txt, csv, xlsx]}\n")


class SeveralFilesTests(HomeCase):
    def test_several_files_are_labelled_by_name(self):
        engine = self.engine()
        run_id = engine.start(MULTI, files={"docs": [self.doc("one.md", "First text."), self.doc("two.csv", "a,b\n1,2\n"),
                                                     xlsx(self.tmp / "three.xlsx", {"S": [["k"], ["v"]]})]})
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        run = engine.get(run_id)
        self.assertEqual(len(run["inputs"]["docs"]), 3)
        text = (engine.run_dir(run_id) / run["nodes"]["extract"]["outputs"]["text"]).read_text(encoding="utf-8")
        self.assertIn('<document name="one.md" index="1">\nFirst text.\n</document>', text)
        self.assertIn('<document name="two.csv" index="2">\n| a | b |', text)
        self.assertIn('<document name="three.xlsx" index="3">\n## S', text)
        self.assertIn('<data source="nodes.extract.text">\n<document name="one.md"', self.prompt_of("compare"))

    def test_limits_on_files(self):
        engine = self.engine()
        with self.assertRaises(RunError) as e:
            engine.start(MULTI, files={"docs": [self.doc(f"f{i}.md", "x") for i in range(schema.MAX_FILES + 1)]})
        self.assertIn(f"at most {schema.MAX_FILES} files", e.exception.messages[0])
        single = MULTI.replace(", multiple: true", "")
        with self.assertRaises(RunError) as e:
            engine.start(single, files={"docs": [self.doc("a.md", "x"), self.doc("b.md", "y")]})
        self.assertIn("takes one file", e.exception.messages[0])
        with self.assertRaises(RunError):
            engine.start(MULTI, files={"docs": [self.doc("a.pdf", "x")]})
        self.assertEqual(engine.list(), [])

    def test_multiple_needs_a_file_input_and_a_bool(self):
        bad = MULTI.replace("{id: docs, type: file, multiple: true", "{id: docs, type: text, multiple: yes")
        with self.assertRaises(schema.WorkflowError) as e:
            schema.parse(bad)
        self.assertIn("inputs.docs.multiple: this key is only for inputs of type 'file'.", e.exception.messages())

    def test_cli_takes_an_input_several_times(self):
        flow = self.tmp / "flow.yaml"
        flow.write_text(MULTI.replace("provider: fake", "provider: claude"), encoding="utf-8")
        a, b = self.doc("a.md", "Alpha."), self.doc("b.md", "Beta.")
        with mock.patch.dict("os.environ", {"MEHTERAN_CONFIG": str(fake_config_toml(self.tmp / "c.toml"))}), \
                redirect_stdout(io.StringIO()) as out:
            code = cli.main(["--lang", "en", "run", str(flow), "--input", f"docs={a}", "--input", f"docs={b}"])
        self.assertEqual(code, 0, out.getvalue())
        self.assertIn('<document name="b.md" index="2">', self.prompt_of("compare"))


def triage(operator: str = "contains", match: str = "urgent", extra: str = "") -> str:
    return workflow(
        ai("classify", "TASK:classify") +
        f"  - {{id: gate, type: condition, config: {{value: \"{{{{nodes.classify.text}}}}\", operator: {operator}, "
        f"match: \"{match}\"{extra}}}}}\n" +
        ai("urgent", "TASK:urgent {{nodes.gate.true}}") +
        ai("calm", "TASK:calm {{nodes.gate.false}}") +
        ai("after_urgent", "TASK:after {{nodes.urgent.text}}") +
        "  - {id: report, type: text.merge, config: {template: \"U={{nodes.after_urgent.text}} C={{nodes.calm.text}}\"}}\n"
        "  - {id: save, type: document.export, config: {source: \"{{nodes.report.text}}\", formats: [md]}}\n",
        [("classify.text", "gate"), ("gate.true", "urgent"), ("gate.false", "calm"), ("urgent.text", "after_urgent"),
         ("after_urgent.text", "report"), ("calm.text", "report"), ("report.text", "save")])


class ConditionTests(HomeCase):
    def run_flow(self, text: str) -> dict:
        engine = self.engine()
        run_id = engine.start(text)
        status = engine.wait(run_id, 30)
        run = engine.get(run_id)
        run["status_seen"] = status
        run["engine"] = engine
        return run

    def test_only_the_branch_taken_runs_and_the_join_gets_its_text(self):
        # The fake answer contains "Fake answer", so "contains: answer" is true, "contains: urgent" false.
        run = self.run_flow(triage(match="answer"))
        self.assertEqual(run["status_seen"], "succeeded", run["error"])
        states = {n: i["status"] for n, i in run["nodes"].items()}
        self.assertEqual(states, {"classify": "succeeded", "gate": "succeeded", "urgent": "succeeded", "calm": "skipped",
                                  "after_urgent": "succeeded", "report": "succeeded", "save": "succeeded"})
        self.assertEqual(set(run["nodes"]["gate"]["outputs"]), {"true"})
        report = (run["engine"].run_dir(run["id"]) / run["nodes"]["report"]["outputs"]["text"]).read_text(encoding="utf-8")
        self.assertTrue(report.startswith("U=## Answer after"))
        self.assertTrue(report.endswith(" C="), report)
        self.assertNotIn("calm", self.tags())

    def test_false_branch_skips_a_chain(self):
        run = self.run_flow(triage(match="urgent"))
        self.assertEqual(run["status_seen"], "succeeded", run["error"])
        states = {n: i["status"] for n, i in run["nodes"].items()}
        self.assertEqual((states["urgent"], states["after_urgent"], states["calm"], states["report"]),
                         ("skipped", "skipped", "succeeded", "succeeded"))
        self.assertEqual(sorted(self.tags()), ["calm", "classify"])

    def test_yes_regex_equals_and_empty(self):
        for operator, value, match, expected in (
                ("is_yes", "**Yes.** It is urgent.", "", True), ("is_yes", "Evet", "", True),
                ("is_yes", "No, not really", "", False),
                ("regex", "Invoice 2024-03", r"\d{4}-\d\d", True), ("equals", " Fast ", "fast", True),
                ("equals", "fast", "Fast", False), ("not_contains", "abc", "x", True), ("empty", " \n", "", True)):
            with self.subTest(operator=operator, value=value):
                self.assertEqual(nodes.condition_result(operator, value, match, operator == "equals" and match == "Fast"),
                                 expected)

    def test_a_failure_still_skips_everything_after_it_and_the_run_fails(self):
        text = triage(match="answer").replace("TASK:urgent", f"TASK:urgent FAIL=9:{(self.tmp / 'n').as_posix()}")
        text = text.replace("{id: urgent, type: ai.cli", "{id: urgent, type: ai.cli, retries: 0")
        run = self.run_flow(text)
        self.assertEqual(run["status_seen"], "failed")
        states = {n: i["status"] for n, i in run["nodes"].items()}
        self.assertEqual((states["urgent"], states["after_urgent"], states["report"], states["save"]),
                         ("failed", "skipped", "skipped", "skipped"))

    def test_the_checks(self):
        with self.assertRaises(schema.WorkflowError) as e:
            schema.parse(triage().replace("{from: gate.true, to: urgent}", "{from: gate, to: urgent}"))
        self.assertTrue(any("must name its branch" in m for m in e.exception.messages()))
        with self.assertRaises(schema.WorkflowError) as e:
            schema.parse(triage(match=""))
        self.assertIn("nodes.gate.config.match: this condition needs a text to compare with (match).", e.exception.messages())
        with self.assertRaises(schema.WorkflowError) as e:
            schema.parse(triage(operator="regex", match="(unclosed"))
        self.assertTrue(any("invalid regular expression" in m for m in e.exception.messages()))
        with self.assertRaises(schema.WorkflowError) as e:
            schema.parse(triage(operator="sometimes"))
        self.assertTrue(any("nodes.gate.config.operator: must be one of: ai, contains" in m for m in e.exception.messages()))
        schema.parse(triage(operator="is_yes", match=""))


LOOP = workflow(
    "  - {id: extract, type: document.extract, config: {file: \"{{inputs.book}}\"}}\n"
    "  - id: each\n    type: ai.map\n    retries: 0\n    config:\n      source: \"{{nodes.extract.text}}\"\n"
    "      split: headings\n      provider: fake\n"
    "      prompt: \"TASK:part{{item.index}} of {{item.count}} MARK {{item.title}} {{item.text}}\"\n"
    "  - {id: save, type: document.export, config: {source: \"{{nodes.each.text}}\", formats: [md]}}\n",
    [("extract.text", "each"), ("each.text", "save")],
    inputs="  - {id: book, type: file}\n")
BOOK = "Preface line.\n\n# One\n\nAlpha.\n\n## Sub\n\nMore.\n\n# Two\n\nBeta.\n\n# Three\n\nGamma.\n"


class LoopTests(HomeCase):
    def test_split_modes(self):
        self.assertEqual([t for t, _ in nodes.split_parts(BOOK, "headings", 0)], ["", "One", "Two", "Three"])
        self.assertIn("## Sub", nodes.split_parts(BOOK, "headings", 0)[1][1])
        self.assertEqual(len(nodes.split_parts(BOOK, "paragraphs", 0)), 9)
        chunks = nodes.split_parts("\n\n".join(["word " * 100] * 10), "chunks", 1200)
        self.assertTrue(2 <= len(chunks) <= 6 and all(len(c) <= 1300 for _, c in chunks), [len(c) for _, c in chunks])
        files = '<document name="a &amp; b.md" index="1">\nA\n</document>\n\n<document name="c.md" index="2">\nC\n</document>'
        self.assertEqual(nodes.split_parts(files, "files", 0), [("a & b.md", "A"), ("c.md", "C")])
        self.assertEqual(nodes.split_parts("plain", "files", 0), [("", "plain")])
        self.assertEqual(nodes.split_parts("  ", "chunks", 100), [])

    def test_one_call_per_part_joined_in_order(self):
        engine = self.engine()
        run_id = engine.start(LOOP, files={"book": self.doc("book.md", BOOK)})
        self.assertEqual(engine.wait(run_id, 60), "succeeded", engine.get(run_id)["error"])
        self.assertEqual(sorted(self.tags()), ["part1", "part2", "part3", "part4"])
        prompt = self.prompt_of("part3")
        self.assertIn("of 4 MARK <data source=\"item.title\">\nTwo\n</data>", prompt)
        self.assertIn("<data source=\"item.text\">\n# Two\n\nBeta.\n</data>", prompt)
        run = engine.get(run_id)
        text = (engine.run_dir(run_id) / run["nodes"]["each"]["outputs"]["text"]).read_text(encoding="utf-8")
        self.assertEqual(re.findall(r"^## .*$", text, re.M)[::2], ["## Part 1", "## One", "## Two", "## Three"])
        self.assertTrue(any(e["kind"] == "progress" and "4/4" in e["message"] for e in engine.store.events(run_id)))

    def test_a_failed_part_is_asked_again_alone(self):
        flag = self.tmp / "fail"
        engine = self.engine(parallel=1)  # the fake's failure counter is not safe for calls at the same time
        run_id = engine.start(LOOP.replace("MARK", f"FAIL=1:{flag}"), files={"book": self.doc("book.md", BOOK)})
        self.assertEqual(engine.wait(run_id, 60), "failed")
        self.assertIn("1 of 4 parts failed", engine.get(run_id)["nodes"]["each"]["error"])
        self.assertEqual(len(self.calls()), 3)
        engine.resume(run_id)
        self.assertEqual(engine.wait(run_id, 60), "succeeded")
        self.assertEqual(sorted(self.tags()), ["part1", "part2", "part3", "part4"], "each part was answered once")

    def test_cancel_during_a_loop_then_resume_keeps_finished_parts(self):
        engine = self.engine(parallel=1)
        once = self.tmp / "slow"
        run_id = engine.start(LOOP.replace("MARK", f"SLEEPONCE=30:{once}"), files={"book": self.doc("book.md", BOOK)})
        self.wait_for(lambda: once.exists())
        time.sleep(0.3)
        engine.cancel(run_id)
        self.assertEqual(engine.wait(run_id, 30), "cancelled")
        done_before = len(self.calls())
        engine.resume(run_id)
        self.assertEqual(engine.wait(run_id, 60), "succeeded")
        self.assertEqual(len(self.calls()), 4)
        self.assertEqual(len(set(self.tags())), 4, "no finished part was asked twice")
        self.assertLess(done_before, 4)

    def test_limits_and_checks(self):
        engine = self.engine()
        run_id = engine.start(LOOP.replace("split: headings", "split: paragraphs\n      max_items: 3"),
                              files={"book": self.doc("book.md", BOOK)})
        self.assertEqual(engine.wait(run_id, 30), "failed")
        self.assertIn("split into 9 parts; at most 3", engine.get(run_id)["nodes"]["each"]["error"])
        with self.assertRaises(schema.WorkflowError) as e:
            schema.parse(LOOP.replace("max_items: 3", "").replace("split: headings", f"split: headings\n      max_items: {nodes.MAP_LIMIT + 1}"))
        self.assertTrue(any("max_items" in m for m in e.exception.messages()))
        with self.assertRaises(schema.WorkflowError) as e:
            schema.parse(LOOP.replace('source: "{{nodes.each.text}}"', 'source: "{{item.text}}"'))
        self.assertTrue(any("can only be used in the prompt of a loop" in m for m in e.exception.messages()))


class QuotaTests(HomeCase):
    def test_a_usage_limit_waits_and_tries_again(self):
        engine = self.engine(quota_delay=0.5)
        text = workflow(ai("ask", f"TASK:ask QUOTA=2:{(self.tmp / 'q').as_posix()}", retries=0), [])
        run_id = engine.start(text)
        self.wait_for(lambda: engine.get(run_id)["nodes"]["ask"]["status"] == "waiting_quota")
        self.assertEqual(engine.get(run_id)["status"], "running")
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        run = engine.get(run_id)
        kinds = [e["kind"] for e in engine.store.events(run_id)]
        self.assertEqual(kinds.count("quota_wait"), 2)
        self.assertIn("usage limit", next(e["message"] for e in engine.store.events(run_id) if e["kind"] == "quota_wait").lower())
        self.assertEqual(self.tags(), ["ask"])

    def test_cancel_while_waiting_for_the_limit(self):
        engine = self.engine(quota_delay=60)
        run_id = engine.start(workflow(ai("ask", f"TASK:ask QUOTA=1:{(self.tmp / 'q').as_posix()}"), []))
        self.wait_for(lambda: engine.get(run_id)["nodes"]["ask"]["status"] == "waiting_quota")
        started = time.time()
        engine.cancel(run_id)
        self.assertEqual(engine.wait(run_id, 10), "cancelled")
        self.assertLess(time.time() - started, 5)
        self.assertEqual(engine.get(run_id)["nodes"]["ask"]["status"], "cancelled")
        engine.resume(run_id)  # the limit has passed (the fake reports it once)
        self.assertEqual(engine.wait(run_id, 30), "succeeded")

    def test_gives_up_after_quota_max_hours(self):
        engine = self.engine(quota_delay=3600 * 2)  # longer than quota_max_hours (1) of the fake settings
        run_id = engine.start(workflow(ai("ask", f"TASK:ask QUOTA=1:{(self.tmp / 'q').as_posix()}"), []))
        self.assertEqual(engine.wait(run_id, 30), "failed")
        self.assertIn("longer than 1 hours", engine.get(run_id)["nodes"]["ask"]["error"])

    def test_loop_parts_wait_for_the_limit_too(self):
        engine = self.engine(quota_delay=0.3, parallel=1)  # the fake's counter file is not safe for parallel calls
        run_id = engine.start(LOOP.replace("MARK", f"QUOTA=1:{(self.tmp / 'q').as_posix()}"), files={"book": self.doc("book.md", BOOK)})
        self.assertEqual(engine.wait(run_id, 60), "succeeded", engine.get(run_id)["error"])
        self.assertEqual(len(set(self.tags())), 4)


class CommentTests(unittest.TestCase):
    def test_trailing_and_end_comments_and_flow_entries(self):
        old = ("# head\nschema_version: 1\nid: x  # the id\nname: X\nnodes:\n  # first\n  - {id: a, type: text.merge, "
               "config: {template: hi}}\n  - {id: b, type: text.merge, config: {template: yo}}  # second\n# end\n")
        data = yamlio.load(old)
        data["nodes"].reverse()
        new = schema.dump(data)
        text, lost = yamlio.keep_comments(old, new)
        self.assertEqual(lost, 0)
        self.assertTrue(text.startswith("# head\n"))
        self.assertIn("# the id\nid: x", text)
        self.assertLess(text.index("# second"), text.index("id: b"))
        self.assertLess(text.index("id: b"), text.index("# first"))
        self.assertLess(text.index("# first"), text.index("id: a"))
        self.assertTrue(text.endswith("# end\n"))
        self.assertEqual(yamlio.load(text), data)

    def test_hash_in_a_prompt_is_not_a_comment(self):
        old = "schema_version: 1\nid: x\nname: X\nnodes:\n  - id: a\n    type: text.merge\n    config:\n      template: |\n        # Heading\n        text\n"
        self.assertEqual(yamlio.keep_comments(old, schema.dump(yamlio.load(old))), (schema.dump(yamlio.load(old)), 0))


class DraftAndNodeTypeApiTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.app = App(self.engine())
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        self.port = self.server.server_address[1]
        self.server.RequestHandlerClass = make_handler(self.app, self.port)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def json(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        req.add_header("X-Token", self.app.token)
        req.add_header("X-Lang", "en")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())

    def test_drafts(self):
        model = {"schema_version": 1, "id": "half", "name": "Half done", "nodes": [{"id": "a", "type": "ai.cli"}]}
        status, data = self.json("POST", "/api/templates/new", body={"model": model})
        self.assertEqual(status, 400, "without draft: only a valid workflow is saved")
        status, data = self.json("POST", "/api/templates/new", body={"model": model, "draft": True})
        self.assertEqual(status, 200, data)
        self.assertEqual((data["id"], data["valid"], data["draft"]), ("half", False, True))
        listed = {t["ref"]: t for t in self.json("GET", "/api/templates")[1]}
        self.assertTrue(listed["user:half"]["draft"])
        self.assertEqual(listed["user:half"]["name"], "Half done")
        self.assertTrue(any("provider" in p for p in listed["user:half"]["problems"]))
        status, data = self.json("POST", "/api/runs", body={"template": "user:half"})
        self.assertEqual(status, 400, "a draft cannot run")
        # Still incomplete YAML text, also not readable: kept as a draft.
        status, data = self.json("PUT", "/api/templates/user/half/draft", body={"yaml": "id: half\nnodes: [\n"})
        self.assertEqual((status, data["draft"]), (200, True))
        self.assertEqual(self.json("PUT", "/api/templates/user/half/draft", body={"yaml": "id: other\n"})[0], 400)
        status, data = self.json("PUT", "/api/templates/user/half/draft",
                                 body={"yaml": "id: half\nname: x\nnote: sk-ant-" + "a" * 30 + "\n"})
        self.assertEqual(status, 400)
        self.assertIn("credentials", data["error"])
        status, data = self.json("PUT", "/api/templates/user/half/draft", body={"yaml": "id: half\napi_key: abc\nnodes: [\n"})
        self.assertEqual(status, 400)
        self.assertIn("line 2", data["error"])
        self.assertEqual(self.json("PUT", "/api/templates/user/document-comparison/draft", body={"yaml": "x"})[0], 403)
        # Completed from the editor: a draft save of a valid model makes it runnable.
        model["nodes"] = [{"id": "a", "type": "ai.cli", "config": {"provider": "fake", "prompt": "TASK:hello"}}]
        status, data = self.json("PUT", "/api/templates/user/half/draft", body={"model": model})
        self.assertEqual((status, data["valid"], data["draft"], data["saved"]), (200, True, False, True))
        status, data = self.json("POST", "/api/runs", body={"template": "user:half"})
        self.assertEqual(status, 200, data)
        self.assertEqual(self.app.engine.wait(data["id"], 30), "succeeded")

    def test_node_types(self):
        status, data = self.json("GET", "/api/node-types")
        self.assertEqual(status, 200)
        types = {item["type"]: item for item in data}
        self.assertEqual(set(types), set(nodes.REGISTRY))
        cond = types["condition"]
        self.assertEqual([o["name"] for o in cond["outputs"]], ["true", "false"])
        self.assertTrue(cond["branches"])
        operator = next(f for f in cond["config"] if f["name"] == "operator")
        self.assertEqual(operator["kind"], "choice")
        self.assertIn({"value": "is_yes", "label": {"tr": "cevap evet ise", "en": "the answer is yes"}}, operator["options"])
        loop = {f["name"]: f for f in types["ai.map"]["config"]}
        self.assertEqual((loop["max_items"]["min"], loop["max_items"]["max"]), (1, nodes.MAP_LIMIT))
        self.assertIn("item.text", loop["prompt"]["item_fields"])
        self.assertTrue(loop["prompt"]["help"]["en"])
        self.assertEqual(types["document.export"]["outputs_from"], "formats")
        self.assertTrue(types["text.merge"]["joins"])
        json.dumps(data)

    def test_run_with_several_uploads(self):
        template = MULTI.replace("id: test-flow", "id: multi")
        templates.import_text(template, self.home)
        uploads = []
        for name, text in (("a.md", "Alpha"), ("b.csv", "x,y\n1,2\n")):
            status, data = self.json("PUT", f"/api/uploads?file={name}", raw=text.encode())
            self.assertEqual(status, 200, data)
            uploads.append(data["upload"])
        status, data = self.json("POST", "/api/runs", body={"template": "user:multi", "files": {"docs": uploads}})
        self.assertEqual(status, 200, data)
        self.assertEqual(self.app.engine.wait(data["id"], 30), "succeeded")
        self.assertIn('<document name="b.csv" index="2">', self.prompt_of("compare"))
        status, _ = self.json("POST", "/api/runs", body={"template": "user:multi", "files": {"docs": [uploads[0]] * 2}})
        self.assertEqual(status, 400)

if __name__ == "__main__":
    unittest.main()
