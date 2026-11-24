"""The run history and its automation (mehteran/history.py) and its web routes: the main input, names and notes,
deleting runs (refused while active, only inside the data folder), "delete runs older than", batches started a few at
a time, saving results to a folder (never overwriting, refusing system and program folders), the export formats eml,
json and csv, an AI step with "output: json", and sharing a workflow with its import preview.
"""

import email
import json
import os
import sys
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import ROOT, HomeCase, ai, workflow  # noqa: E402

from mehteran import history, nodes, paths, schema, sharing  # noqa: E402
from mehteran.engine import RunError  # noqa: E402
from mehteran.nodes import NodeError, export_document, json_problem, structured  # noqa: E402
from mehteran.web import App, make_handler  # noqa: E402

FILE_FLOW = workflow(
    "  - {id: read, type: document.extract}\n" + ai("sum", "TASK:sum Summarize."),
    [("read", "sum")], inputs="  - {id: doc, type: file, formats: [txt, md]}\n  - {id: note, type: text, required: false}\n",
    head="outputs:\n  - {id: summary, from: sum.text}\n")
TEXT_FLOW = workflow(ai("write", "TASK:write {{inputs.topic}}"), [], inputs="  - {id: topic, type: text}\n")


class Server(HomeCase):
    def setUp(self):
        super().setUp()
        self.app = App(self.engine())
        self.addCleanup(self.app.automation.stop)
        self.app.automation.interval = 0.05
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        self.port = self.server.server_address[1]
        self.server.RequestHandlerClass = make_handler(self.app, self.port)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        (self.home / "templates").mkdir(parents=True, exist_ok=True)

    def call(self, method, path, body=None, raw=None):
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        req.add_header("X-Token", self.app.token)
        req.add_header("X-Lang", "en")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, res.read()
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read()

    def json(self, *args, **kwargs):
        status, body = self.call(*args, **kwargs)
        return status, json.loads(body)

    def upload(self, name, text):
        status, data = self.json("PUT", f"/api/uploads?file={name}", raw=text.encode())
        self.assertEqual(status, 200, data)
        return data["upload"]

    def template(self, text, template_id="test-flow"):
        (self.home / "templates" / f"{template_id}.yaml").write_text(text, encoding="utf-8")
        return f"user:{template_id}"


class MainInputTests(unittest.TestCase):
    def test_first_file_name_then_text(self):
        self.assertEqual(history.main_input({"doc": "inputs/doc/report.pdf", "note": "x"}, FILE_FLOW), "report.pdf")
        long = "word " * 20
        self.assertEqual(history.main_input({"topic": long}, TEXT_FLOW), ("word " * 8).strip()[:40] + "…")
        self.assertEqual(history.main_input({"doc": "", "note": "short note"}, FILE_FLOW), "short note")
        several = workflow(ai("a", "x"), [], inputs="  - {id: docs, type: file, multiple: true}\n")
        self.assertEqual(history.main_input({"docs": ["inputs/docs/1/a.md", "inputs/docs/2/b.md"]}, several), "a.md +1")


class HistoryTests(Server):
    def test_history_search_and_event_cursor(self):
        eng = self.app.engine
        run_id = eng.start(TEXT_FLOW, {"topic": "test"}, launch=False)
        eng.store.update_run(run_id, label="İstanbul")
        eng.store.event(run_id, None, "marker", "second")
        status, rows = self.json("GET", "/api/runs?q=istanbul")
        self.assertEqual((status, [r["id"] for r in rows]), (200, [run_id]))
        cursor = eng.store.events(run_id)[-1]["id"]
        status, events = self.json("GET", f"/api/runs/{run_id}/events?before={cursor}")
        self.assertEqual((status, [e["kind"] for e in events]), (200, ["created"]))

    def test_finished_run_contains_a_manifest(self):
        run_id = self.run_flow()
        folder = self.app.engine.run_dir(run_id)
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual((manifest["id"], manifest["status"]), (run_id, "succeeded"))
        import hashlib
        for entry in manifest["files"]:
            self.assertEqual(entry["sha256"], hashlib.sha256((folder / entry["path"]).read_bytes()).hexdigest())

    def test_binary_upload_requires_matching_content(self):
        status, _ = self.json("PUT", "/api/uploads?file=wrong.pdf", raw=b"not a PDF")
        self.assertEqual(status, 400)

    def test_trash_and_restore_keep_the_run_files(self):
        run_id = self.run_flow()
        path = f"/api/runs/{run_id}"
        self.assertEqual(self.json("DELETE", path, {"trash": True}), (200, {"trashed": True}))
        self.assertEqual(self.json("GET", "/api/runs"), (200, []))
        self.assertEqual(self.json("GET", "/api/runs/trash")[1][0]["id"], run_id)
        self.assertTrue(self.app.engine.run_dir(run_id).is_dir())
        self.assertEqual(self.json("POST", path + "/restore", {}), (200, {"ok": True}))
        self.assertEqual(self.json("GET", path)[1]["status"], "succeeded")

    def test_storage_maintenance_is_opt_in_and_keeps_recent_runs(self):
        old, recent = self.run_flow(), self.run_flow()
        eng = self.app.engine
        eng.store.update_run(old, finished=time.time() - 120 * 86400)
        history.maintain_storage(eng)
        self.assertIsNotNone(eng.store.run(old))
        config = eng.home / "configurations" / "engine.toml"
        config.parent.mkdir(exist_ok=True)
        config.write_text("retain_runs_days = 90\n", encoding="utf-8")
        history.maintain_storage(eng)
        self.assertIsNone(eng.store.run(old))
        self.assertIsNotNone(eng.store.run(recent))

    def test_history_cursor_handles_equal_timestamps(self):
        eng = self.app.engine
        ids = [eng.start(TEXT_FLOW, {"topic": "test"}, launch=False) for _ in range(3)]
        for run_id in ids:
            eng.store.update_run(run_id, created=1)
        ordered = sorted(ids, reverse=True)
        status, rows = self.json("GET", "/api/runs?before=" + ordered[0])
        self.assertEqual(status, 200)
        self.assertEqual([row["id"] for row in rows], ordered[1:])

    def run_flow(self, text=TEXT_FLOW, values=None):
        run_id = self.app.engine.start(text, values or {"topic": "Ottoman music"})
        self.assertEqual(self.app.engine.wait(run_id, 30), "succeeded")
        return run_id

    def test_list_has_main_input_label_and_note(self):
        run_id = self.run_flow()
        status, runs = self.json("GET", "/api/runs")
        self.assertEqual(runs[0]["main_input"], "Ottoman music")
        status, data = self.json("PUT", f"/api/runs/{run_id}/label", {"label": "  My\n run ", "note": "line 1\nline 2"})
        self.assertEqual((status, data), (200, {"label": "My run", "note": "line 1\nline 2"}))
        status, runs = self.json("GET", "/api/runs")
        self.assertEqual((runs[0]["label"], runs[0]["note"]), ("My run", "line 1\nline 2"))
        status, data = self.json("PUT", f"/api/runs/{run_id}/label", {"label": "x" * 500})
        self.assertEqual(status, 400)
        status, data = self.json("PUT", f"/api/runs/{run_id}/label", {"label": "", "note": ""})
        self.assertEqual(data, {"label": None, "note": None})

    def test_delete_removes_rows_and_folder_and_names_the_size(self):
        run_id = self.run_flow()
        folder = self.app.engine.run_dir(run_id)
        status, data = self.json("DELETE", f"/api/runs/{run_id}", {"dry_run": True})
        self.assertEqual(status, 200)
        self.assertTrue(data["deletable"])
        self.assertEqual(data["size"], history.folder_size(folder))
        self.assertGreater(data["size"], 0)
        self.assertTrue(folder.is_dir())
        status, data = self.json("DELETE", f"/api/runs/{run_id}", {})
        self.assertEqual((status, data["deleted"]), (200, True))
        self.assertFalse(folder.exists())
        self.assertIsNone(self.app.engine.store.run(run_id))
        self.assertEqual(self.app.engine.store.events(run_id), [])
        status, data = self.json("DELETE", f"/api/runs/{run_id}", {})
        self.assertEqual(status, 400)  # gone

    def test_failed_file_purge_is_retried_after_restart(self):
        run_id = self.run_flow()
        engine = self.app.engine
        folder = engine.run_dir(run_id)
        with mock.patch.object(history.shutil, "rmtree", side_effect=PermissionError):
            with self.assertRaises(PermissionError):
                history.delete_run(engine, run_id)
        self.assertTrue(folder.is_dir())
        self.assertIsNone(engine.store.run(run_id))
        restarted = self.engine()
        self.assertEqual(restarted.store.pending_purges(), [run_id])
        history.recover_purges(restarted)
        self.assertFalse(folder.exists())
        self.assertEqual(restarted.store.pending_purges(), [])

    def test_failed_database_delete_keeps_run_files(self):
        run_id = self.run_flow()
        engine = self.app.engine
        with mock.patch.object(engine.store, "delete_run", side_effect=OSError):
            with self.assertRaises(OSError):
                history.delete_run(engine, run_id)
        self.assertTrue(engine.run_dir(run_id).is_dir())
        self.assertIsNotNone(engine.store.run(run_id))
        self.assertEqual(engine.store.pending_purges(), [])

    def test_delete_refuses_an_active_run_and_a_held_lock(self):
        run_id = self.app.engine.start(workflow(ai("slow", "TASK:slow SLEEP=3"), []))
        self.wait_for(lambda: self.app.engine.store.run(run_id)["status"] == "running")
        status, data = self.json("DELETE", f"/api/runs/{run_id}", {})
        self.assertEqual(status, 400, data)
        self.assertTrue(self.app.engine.run_dir(run_id).is_dir())
        self.app.engine.cancel(run_id)
        self.app.engine.wait(run_id, 30)
        # A finished run whose lock another process holds: not deleted.
        from mehteran.common import system
        with open(self.app.engine.run_dir(run_id) / ".lock", "a+") as handle:
            self.assertTrue(system.try_lock(handle))
            with mock.patch.object(self.app.engine, "is_active", return_value=False):
                with self.assertRaises(RunError):
                    history.delete_run(self.app.engine, run_id)
        self.assertTrue(self.app.engine.run_dir(run_id).is_dir())

    def test_delete_never_follows_a_link_out_of_the_data_folder(self):
        run_id = self.run_flow()
        outside = self.tmp / "outside"
        outside.mkdir()
        (outside / "keep.txt").write_text("keep", encoding="utf-8")
        (self.app.engine.run_dir(run_id) / "nodes" / "link").symlink_to(outside, target_is_directory=True)
        history.delete_run(self.app.engine, run_id)
        self.assertTrue((outside / "keep.txt").exists())

    def test_cleanup_older_than(self):
        old, new = self.run_flow(), self.run_flow()
        self.app.engine.store.update_run(old, created=time.time() - 100 * 86400, finished=time.time() - 100 * 86400)
        status, data = self.json("POST", "/api/runs/cleanup", {"days": 90, "dry_run": True})
        self.assertEqual((status, data["count"]), (200, 1))
        self.assertTrue(self.app.engine.run_dir(old).is_dir())
        status, data = self.json("POST", "/api/runs/cleanup", {"days": 90})
        self.assertEqual(data["deleted"], 1)
        self.assertFalse(self.app.engine.run_dir(old).exists())
        self.assertTrue(self.app.engine.run_dir(new).is_dir())
        self.assertEqual(self.json("POST", "/api/runs/cleanup", {"days": 0})[0], 400)


class FolderTests(Server):
    def test_folder_rules(self):
        out = self.tmp / "out"
        out.mkdir()
        self.assertEqual(history.folder_problem(str(out), self.home), (out.resolve(), None))
        for bad in ("relative/path", "", str(self.tmp / "missing"), str(paths.REPO), str(paths.REPO / "mehteran"),
                    str(self.home), str(self.home / "executions"), "/", "/etc", "/usr/bin"):
            folder, problem = history.folder_problem(bad, self.home)
            self.assertIsNone(folder, bad)
            self.assertTrue(problem, bad)
        if sys.platform == "darwin":
            self.assertIsNotNone(history.folder_problem("/System", self.home)[1])
            self.assertIsNotNone(history.folder_problem(str(Path.home() / "Library"), self.home)[1])

    def test_unique_names_never_overwrite(self):
        out = self.tmp / "out"
        out.mkdir()
        (out / "summary.md").write_text("mine", encoding="utf-8")
        self.assertEqual(history.unique_target(out, "summary.md").name, "summary (2).md")
        self.assertEqual(history.unique_target(out, "summary.md").name, "summary (3).md")
        self.assertEqual((out / "summary.md").read_text(encoding="utf-8"), "mine")

    def test_run_saves_to_folder_after_success_with_confirmation(self):
        ref = self.template(FILE_FLOW)
        out = self.tmp / "out"
        out.mkdir()
        (out / "summary.md").write_text("mine", encoding="utf-8")
        body = {"template": ref, "files": {"doc": self.upload("report.txt", "Some text.")}, "output_dir": str(out)}
        status, data = self.json("POST", "/api/runs", body)
        self.assertEqual(status, 409, data)  # first use: the user must confirm the folder
        status, data = self.json("POST", "/api/runs", {**body, "output_confirmed": True})
        self.assertEqual(status, 200, data)
        run_id = data["id"]
        self.assertEqual(self.app.engine.wait(run_id, 30), "succeeded")
        self.wait_for(lambda: self.app.engine.store.run(run_id).get("output_state"))
        state = json.loads(self.app.engine.store.run(run_id)["output_state"])
        self.assertEqual(state["saved"], ["summary (2).md"])
        self.assertEqual((out / "summary.md").read_text(encoding="utf-8"), "mine")
        self.assertIn("Fake answer", (out / "summary (2).md").read_text(encoding="utf-8"))
        # Remembered for this workflow and confirmed from now on.
        self.assertEqual(self.json("GET", "/api/output-folders/user/test-flow")[1]["path"], str(out.resolve()))
        self.assertTrue(self.json("POST", "/api/output-folders/check", {"path": str(out)})[1]["confirmed"])
        status, data = self.json("POST", "/api/runs", {**body, "files": {"doc": self.upload("b.txt", "B.")}})
        self.assertEqual(status, 200, data)
        # A system folder is refused by the server.
        status, data = self.json("POST", "/api/runs", {**body, "output_dir": "/etc", "output_confirmed": True})
        self.assertEqual(status, 400)

    def test_failed_run_saves_nothing(self):
        ref = self.template(workflow(ai("bad", "TASK:bad FAIL=9:" + str(self.tmp / "count")), [],
                                     head="outputs:\n  - {id: answer, from: bad.text}\n"))
        out = self.tmp / "out"
        out.mkdir()
        status, data = self.json("POST", "/api/runs", {"template": ref, "output_dir": str(out), "output_confirmed": True})
        self.assertEqual(self.app.engine.wait(data["id"], 30), "failed")
        time.sleep(0.3)
        self.assertEqual(list(out.iterdir()), [])
        self.assertIsNone(self.app.engine.store.run(data["id"])["output_state"])


class BatchTests(Server):
    def test_automation_checks_again_if_a_run_finishes_between_queries(self):
        self.app.automation.stop()
        eng = self.app.engine
        run_id = eng.start(TEXT_FLOW, {"topic": "test"}, launch=False)
        eng.store.update_run(run_id, output_dir=str(self.tmp), status="running")
        rows = eng.store._rows

        def finish_after_save_query(sql, args=()):
            result = rows(sql, args)
            if sql.startswith("SELECT id, output_dir"):
                eng.store.update_run(run_id, status="succeeded")
            return result

        with mock.patch.object(eng.store, "_rows", side_effect=finish_after_save_query):
            self.assertTrue(history.Automation(eng).step())

    def test_local_batch_refuses_cloud_models(self):
        ref = self.template(FILE_FLOW)
        upload = self.upload("doc.txt", "Example.")
        status, _ = self.json("POST", "/api/runs", {"template": ref, "privacy": "local",
                                                  "batch": {"input": "doc", "files": [upload]}})
        self.assertEqual(status, 400)
        self.assertEqual(self.app.engine.store.runs(), [])

    def test_one_run_per_file_two_at_a_time(self):
        ref = self.template(FILE_FLOW.replace("TASK:sum Summarize.", "TASK:sum SLEEP=0.6 Summarize."))
        out = self.tmp / "out"
        out.mkdir()
        ids = [self.upload(f"doc{n}.txt", f"Text {n}.") for n in range(4)]
        status, data = self.json("POST", "/api/runs", {"template": ref, "values": {"note": "same"},
                                                       "batch": {"input": "doc", "files": ids},
                                                       "output_dir": str(out), "output_confirmed": True})
        self.assertEqual(status, 200, data)
        self.assertEqual(len(data["ids"]), 4)
        most = 0
        end = time.time() + 40
        while time.time() < end:
            runs = [self.app.engine.store.run(r) for r in data["ids"]]
            most = max(most, sum(r["status"] == "running" for r in runs))
            if all(r["status"] == "succeeded" for r in runs):
                break
            time.sleep(0.05)
        self.assertTrue(all(self.app.engine.store.run(r)["status"] == "succeeded" for r in data["ids"]))
        self.assertLessEqual(most, history.BATCH_PARALLEL)
        self.assertGreaterEqual(most, 1)
        status, runs = self.json("GET", "/api/runs")
        self.assertEqual({r["batch"] for r in runs}, {data["batch"]})
        self.assertEqual(sorted(r["main_input"] for r in runs), [f"doc{n}.txt" for n in range(4)])
        self.wait_for(lambda: len(list(out.iterdir())) == 4)
        self.assertEqual(sorted(p.name for p in out.iterdir()), [f"doc{n} - summary.md" for n in range(4)])
        self.assertEqual(list((self.home / "executions" / ".uploads").iterdir()), [])

    def test_bad_file_creates_no_run(self):
        ref = self.template(FILE_FLOW)
        ids = [self.upload("a.txt", "A."), self.upload("b.csv", "x,y\n1,2\n")]
        status, data = self.json("POST", "/api/runs", {"template": ref, "batch": {"input": "doc", "files": ids}})
        self.assertEqual(status, 400, data)
        self.assertEqual(self.app.engine.store.runs(), [])
        status, data = self.json("POST", "/api/runs", {"template": ref, "batch": {"input": "note", "files": ids[:1]}})
        self.assertEqual(status, 400, data)


class ExportFormatTests(HomeCase):
    TABLE = "# Report\n\nIntro.\n\n| Name | Total |\n|---|---:|\n| Ali | 3 |\n| =SUM(A1) | -2 |\n"

    def test_eml_is_an_unsent_draft_with_both_parts(self):
        out = export_document("# Merhaba\n\nBir **metin**.", ["eml"], "Konu: rapor", "tr", self.tmp, "mail")
        message = email.message_from_bytes(out["eml"].read_bytes())
        self.assertEqual(message["Subject"], "Konu: rapor")
        self.assertEqual(message["X-Unsent"], "1")
        self.assertIsNone(message["To"])
        kinds = [part.get_content_type() for part in message.walk()]
        self.assertEqual(kinds, ["multipart/alternative", "text/plain", "text/html"])
        self.assertIn("Bir **metin**.", message.get_payload()[0].get_payload(decode=True).decode("utf-8"))

    def test_json_and_csv_from_a_table_and_from_json(self):
        self.assertEqual(json.loads(structured(self.TABLE, "json")),
                         [{"Name": "Ali", "Total": "3"}, {"Name": "=SUM(A1)", "Total": "-2"}])
        csv_text = structured(self.TABLE, "csv")
        self.assertTrue(csv_text.startswith("﻿Name,Total\r\n"))
        self.assertIn("'=SUM(A1),-2\r\n", csv_text)  # a formula is kept as text; a number is not changed
        source = '```json\n[{"a": 1, "b": {"c": 2}}, {"a": 3}]\n```'
        self.assertEqual(json.loads(structured(source, "json")), [{"a": 1, "b": {"c": 2}}, {"a": 3}])
        self.assertEqual(structured(source, "csv"), '﻿a,b\r\n1,"{""c"": 2}"\r\n3,\r\n')
        with self.assertRaises(NodeError):
            structured("Just prose.", "csv")
        with self.assertRaises(NodeError):
            export_document("Just prose.", ["md", "json"], "t", "en", self.tmp, "x")
        self.assertFalse((self.tmp / "x.md").exists())  # nothing written before the check

    def test_export_step_with_new_formats(self):
        engine = self.engine()
        table = json.dumps("| a | b |\n|---|---|\n| 1 | 2 |\n")
        flow = workflow(f"  - {{id: t, type: text.merge, config: {{template: {table}}}}}\n"
                        "  - {id: out, type: document.export, config: {formats: [eml, json, csv], title: T}}\n",
                        [("t", "out")])
        run_id = engine.start(flow)
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        folder = engine.run_dir(run_id) / "nodes" / "out"
        self.assertEqual(json.loads((folder / "out.json").read_text(encoding="utf-8")), [{"a": "1", "b": "2"}])
        self.assertEqual((folder / "out.csv").read_bytes(), "﻿a,b\r\n1,2\r\n".encode("utf-8"))
        self.assertTrue((folder / "out.eml").is_file())
        # Prose only: json and csv fail clearly.
        run_id = engine.start(workflow(ai("t", "TASK:t") + "  - {id: out, type: document.export, config: {formats: [csv]}}\n",
                                       [("t", "out")]))
        self.assertEqual(engine.wait(run_id, 30), "failed")
        self.assertIn("CSV", engine.get(run_id)["nodes"]["out"]["error"])


class JsonOutputTests(HomeCase):
    def flow(self, prompt, schema_text=None):
        config = {"provider": "fake", "prompt": prompt, "output": "json"}
        if schema_text:
            config["json_schema"] = schema_text
        return workflow(f"  - {{id: j, type: ai.cli, config: {json.dumps(config)}}}\n", [])

    def test_valid_json_is_pretty_printed(self):
        engine = self.engine()
        run_id = engine.start(self.flow('TASK:j ANSWER={"b":[1,2],"a":"x"}'))
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        text = (engine.run_dir(run_id) / "nodes" / "j" / "text.md").read_text(encoding="utf-8")
        self.assertEqual(json.loads(text), {"b": [1, 2], "a": "x"})
        self.assertIn('\n  "b": [', text)
        self.assertIn("Answer with JSON only", self.prompt_of("j"))
        self.assertEqual(self.tags(), ["j"])

    def test_one_retry_with_the_error_then_success(self):
        engine = self.engine()
        run_id = engine.start(self.flow('TASK:j ANSWER=not_json ONRETRY={"ok":true}'))
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        self.assertEqual(self.tags(), ["j", "j"])
        self.assertIn("previous answer was rejected: The answer is not valid JSON", self.prompt_of("j", 1))

    def test_schema_mismatch_fails_clearly_after_one_retry(self):
        schema_text = '{"type": "object", "required": ["count"], "properties": {"count": {"type": "integer"}}}'
        flow = self.flow('TASK:j ANSWER={"count":"three"}', schema_text).replace("config: {", "retries: 0, config: {", 1)
        engine = self.engine()
        run_id = engine.start(flow)
        self.assertEqual(engine.wait(run_id, 30), "failed")
        self.assertEqual(self.tags(), ["j", "j"])
        self.assertIn("$.count: expected integer", engine.get(run_id)["nodes"]["j"]["error"])
        self.assertIn('"required": ["count"]', self.prompt_of("j"))

    def test_bad_schema_is_a_workflow_problem(self):
        with self.assertRaises(schema.WorkflowError):
            schema.parse(self.flow("x", "{not json"))

    def test_json_problem(self):
        self.assertEqual(json_problem('Here:\n```json\n{"a": 1}\n```', None), ({"a": 1}, ""))
        self.assertEqual(json_problem('{"a": 1}', {"type": "object", "additionalProperties": False,
                                                   "properties": {"b": {}}})[1],
                         'The JSON does not match the schema: $: unexpected property "a"')


class ShareTests(Server):
    def test_share_adds_based_on_and_author_and_still_imports(self):
        status, body = self.call("GET", "/api/templates/builtin/document-explainer/share?author=Ay%C5%9Fe%20Y.")
        self.assertEqual(status, 200, body)
        text = body.decode("utf-8")
        wf = schema.parse(text)
        self.assertEqual(wf.data["author"], "Ayşe Y.")
        self.assertTrue(str(wf.data["based_on"]).startswith("builtin:document-explainer"))

    def test_preview_shows_prompts_tools_problems_and_taken_id(self):
        _, text = sharing.share_text("builtin", "document-explainer", self.home, "")
        status, data = self.json("POST", "/api/templates/preview", {"yaml": text})
        self.assertEqual(status, 200)
        self.assertTrue(data["valid"])
        self.assertTrue(data["exists"])  # the id of a built-in
        self.assertTrue(data["prompts"])
        self.assertTrue(all(p["text"].strip() for p in data["prompts"]))
        self.assertIn("graph", data)
        new = text.replace("id: document-explainer", "id: my-explainer", 1)
        status, data = self.json("POST", "/api/templates/import", {"yaml": text, "id": "my-explainer"})
        self.assertEqual(status, 200, data)
        self.assertTrue((self.home / "templates" / "my-explainer.yaml").exists())
        self.assertIn("based_on", new)
        # A file with a credential: the preview names the problem and the import refuses it.
        secret = text.replace("schema_version: 1", "schema_version: 1\napi_key: x", 1)
        status, data = self.json("POST", "/api/templates/preview", {"yaml": secret})
        self.assertFalse(data["valid"])
        self.assertTrue(any("api_key" in p for p in data["problems"]))
        self.assertEqual(self.json("POST", "/api/templates/import", {"yaml": secret, "id": "x-y"})[0], 400)


if __name__ == "__main__":
    unittest.main()
