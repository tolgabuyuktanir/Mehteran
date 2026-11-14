"""The visual editor's server side: the layout key, readable YAML out and back, renaming, saving from the model,
comment handling, the editor and setup routes (with every tool call mocked: nothing is installed or run)."""

import copy
import json
import re
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, ai, workflow  # noqa: E402

from mehteran import paths, schema, templates, web, yamlio  # noqa: E402
from mehteran.templates import TemplateError  # noqa: E402

LAYOUT = workflow(ai("a", "TASK:a") + ai("b", "TASK:b {{nodes.a.text}}"), [("a.text", "b")])

# Every input type and every node type, with multi-line prompts (one with a line that ends in spaces).
FULL = {
    "schema_version": 1, "id": "full-flow", "name": {"tr": "Tam akış", "en": "Full flow"},
    "description": "Line one.\nLine two: with a colon and \"quotes\".\n", "version": "2.1", "category": "research",
    "inputs": [
        {"id": "doc", "type": "file", "label": {"tr": "Belge", "en": "Document"}, "formats": ["pdf", "md"]},
        {"id": "extra", "type": "file", "required": False},
        {"id": "note", "type": "text", "multiline": True, "required": False, "default": "first\nsecond"},
        {"id": "lang", "type": "choice", "options": [{"value": "en", "label": {"tr": "İngilizce", "en": "English"}}, "tr"],
         "default": "en"},
        {"id": "model", "type": "provider", "default": "fake/small@high"},
    ],
    "nodes": [
        {"id": "read", "type": "document.extract", "label": "Read", "config": {"file": "{{inputs.doc}}", "max_chars": 5000}},
        {"id": "think", "type": "ai.cli", "retries": 1, "timeout": 120, "config": {
            "provider": "{{inputs.model}}",
            "prompt": "TASK:think Review in {{inputs.lang}}.\n\n# A heading, not a comment\n{{nodes.read.text}}\n  indented line\n"}},
        {"id": "odd", "type": "ai.cli", "config": {"provider": "fake", "prompt": "trailing spaces   \nnext {{nodes.read.text}}"}},
        {"id": "join", "type": "text.merge", "config": {"template": "{{nodes.think.text}}\n\n{{nodes.odd.text}}\n"}},
        {"id": "ok", "type": "approval", "config": {"show": "{{nodes.join.text}}", "instructions": {"tr": "Okuyun.", "en": "Read it."}}},
        {"id": "save", "type": "document.export", "config": {"source": "{{nodes.ok.text}}\n\n{{nodes.ok.comment}}", "title": "Report",
                                                           "lang": "{{inputs.lang}}", "formats": ["md", "html"], "filename": "report"}},
    ],
    "connections": [{"from": "read.text", "to": "think"}, {"from": "read.text", "to": "odd"}, {"from": "think.text", "to": "join"},
                    {"from": "odd.text", "to": "join"}, {"from": "join.text", "to": "ok"}, {"from": "ok", "to": "save"}],
    "outputs": [{"id": "report", "from": "save.md", "label": {"tr": "Rapor", "en": "Report"}}],
    "layout": {"read": {"x": 0, "y": 0}, "think": {"x": 320, "y": -40}, "odd": {"x": 320, "y": 120}, "join": {"x": 640, "y": 0},
               "ok": {"x": 960, "y": 0}, "save": {"x": 1280, "y": -100000}},
}


def problems(data) -> list[str]:
    try:
        schema.check(copy.deepcopy(data))
    except schema.WorkflowError as e:
        return e.messages()
    return []


class LayoutTests(HomeCase):
    def test_layout_is_optional_and_strictly_checked(self):
        wf = schema.parse(LAYOUT + "layout:\n  a: {x: 10, y: -20}\n  b: {x: 300, y: 0}\n")
        self.assertEqual(wf.graph()["layout"]["a"], {"x": 10, "y": -20})
        self.assertEqual(schema.parse(LAYOUT).graph()["layout"], {})
        for bad, fragment in (
                ("layout: [a]\n", "layout: must be a mapping"),
                ("layout:\n  ghost: {x: 1, y: 2}\n", "layout.ghost: there is no node 'ghost'"),
                ("layout:\n  a: {x: 1}\n", "layout.a: a position"),
                ("layout:\n  a: {x: 1, y: 2, z: 3}\n", "layout.a: a position"),
                ("layout:\n  a: {x: 1.5, y: 2}\n", "layout.a: a position"),
                ("layout:\n  a: {x: true, y: 2}\n", "layout.a: a position"),
                ("layout:\n  a: {x: 100001, y: 2}\n", "layout.a: a position"),
                ("layout:\n  a: [1, 2]\n", "layout.a: a position")):
            found = problems(yamlio.load(LAYOUT + bad))
            self.assertTrue(any(fragment in p for p in found), (bad, found))

    def test_the_engine_ignores_the_layout(self):
        engine = self.engine()
        run_id = engine.start(LAYOUT + "layout:\n  a: {x: 0, y: 0}\n  b: {x: 300, y: 0}\n", {}, {})
        self.assertEqual(engine.wait(run_id, 60), "succeeded", engine.get(run_id)["error"])
        self.assertEqual(self.tags(), ["a", "b"])

    def test_an_empty_optional_file_gives_empty_text(self):
        text = workflow("  - {id: x, type: document.extract, config: {file: '{{inputs.doc}}'}}\n"
                        + ai("b", "TASK:b [{{nodes.x.text}}]"), [("x.text", "b")],
                        inputs="  - {id: doc, type: file, required: false}\n")
        engine = self.engine()
        run_id = engine.start(text, {}, {})
        self.assertEqual(engine.wait(run_id, 60), "succeeded", engine.get(run_id)["error"])
        self.assertIn("[<data source=\"nodes.x.text\">\n\n</data>]", self.prompt_of("b"))


class ReadableYamlTests(HomeCase):
    def round_trip(self, data):
        text = schema.dump(data)
        back = yamlio.load(text)
        self.assertEqual(back, data)
        self.assertEqual(schema.dump(back), text, "the writing is stable")
        return text

    def test_builtin_templates_round_trip(self):
        for path in sorted(paths.BUILTIN_TEMPLATES.glob("*.yaml")):
            with self.subTest(path.name):
                data = schema.parse(path.read_text(encoding="utf-8")).data
                text = self.round_trip(data)
                schema.parse(text)

    def test_every_input_and_node_type_round_trips(self):
        self.assertEqual(problems(FULL), [])
        text = self.round_trip(FULL)
        keys = [line.split(":")[0] for line in text.splitlines() if line and not line.startswith((" ", "-"))]
        self.assertEqual(keys, ["schema_version", "id", "name", "description", "version", "category", "inputs", "nodes",
                                "connections", "outputs", "layout"])
        self.assertIn("name: {tr: Tam akış, en: Full flow}", text)  # unicode as it is, short maps on one line
        self.assertNotIn("\\u", text)

    def test_multiline_prompts_are_literal_blocks(self):
        text = schema.dump(FULL)
        self.assertIn("      prompt: |\n        TASK:think Review in {{inputs.lang}}.\n\n        # A heading, not a comment\n", text)
        self.assertIn("      template: |\n", text)
        # A line that ends in spaces cannot be a block; the text falls back to quotes and still reads back the same.
        self.assertEqual(yamlio.load(text)["nodes"][2]["config"]["prompt"], FULL["nodes"][2]["config"]["prompt"])
        self.assertEqual(yamlio.comments(text), [], "a '#' line inside a prompt is not a comment")

    def test_keys_come_in_the_documented_order_and_unknown_keys_are_kept(self):
        data = {"nodes": [{"config": {"prompt": "p", "provider": "fake"}, "type": "ai.cli", "id": "a", "speed": 3}],
                "name": "N", "id": "x", "schema_version": 1, "colour": "red"}
        text = schema.dump(data)
        self.assertTrue(text.startswith("schema_version: 1\nid: x\nname: N\n"), text)
        self.assertIn("  - id: a\n    type: ai.cli\n    config: {provider: fake, prompt: p}\n    speed: 3\n", text)
        self.assertTrue(text.rstrip().endswith("colour: red"))

    def test_comments_and_header(self):
        text = "# Header line\n# second\nid: x  # a note\nprompt: |\n  # not a comment\nname: '# not one'\n# last\n"
        self.assertEqual(yamlio.comments(text), [0, 1, 2, 6])
        self.assertEqual(yamlio.header(text), "# Header line\n# second\n")
        self.assertEqual(yamlio.comments("a: [unclosed\n"), [])


class RenameTests(HomeCase):
    def test_renaming_a_node_updates_every_use(self):
        data = copy.deepcopy(FULL)
        data["nodes"][3]["config"]["template"] = "{{ nodes.think.text }} and {{nodes.thinker.text}} {{nodes.think.text}}"
        out = schema.rename(data, "nodes", "think", "analyse")
        self.assertEqual(data, {**data}, "the input is not changed")
        self.assertEqual(out["nodes"][1]["id"], "analyse")
        self.assertEqual(out["nodes"][3]["config"]["template"],
                         "{{ nodes.analyse.text }} and {{nodes.thinker.text}} {{nodes.analyse.text}}")
        self.assertIn({"from": "analyse.text", "to": "join"}, out["connections"])
        self.assertEqual(out["layout"]["analyse"], {"x": 320, "y": -40})
        self.assertNotIn("think", out["layout"])
        out = schema.rename(out, "nodes", "save", "store")
        self.assertEqual(out["outputs"][0]["from"], "store.md")
        self.assertIn({"from": "ok", "to": "store"}, out["connections"])
        out["nodes"][3]["config"]["template"] = "{{nodes.analyse.text}}\n\n{{nodes.odd.text}}\n"
        self.assertEqual(problems(out), [])

    def test_renaming_an_input_updates_its_placeholders(self):
        out = schema.rename(FULL, "inputs", "lang", "language")
        self.assertIn("{{inputs.language}}", out["nodes"][1]["config"]["prompt"])
        self.assertEqual(out["nodes"][5]["config"]["lang"], "{{inputs.language}}")
        self.assertEqual(problems(out), [])

    def test_bad_renames_are_refused(self):
        for kind, old, new, fragment in (("nodes", "think", "Bad", "not a valid id"), ("nodes", "think", "odd", "more than once"),
                                         ("nodes", "ghost", "x", "no node"), ("nodes", "think", "x\n", "not a valid id"),
                                         ("edges", "think", "x", "Cannot rename")):
            with self.assertRaises(schema.WorkflowError) as e:
                schema.rename(FULL, kind, old, new)
            self.assertIn(fragment, e.exception.messages()[0], (kind, new))


class SaveModelTests(HomeCase):
    def test_saving_from_the_model_keeps_comments_next_to_their_key_or_node(self):
        text = templates.read("builtin", "document-comparison", self.home)
        templates.import_text(templates.with_id(text, "mine"), self.home)
        path = self.home / "templates" / "mine.yaml"
        stored = re.sub(r"(?m)^version: .*$", lambda m: m.group(0) + "  # bump me", path.read_text(encoding="utf-8"), count=1)
        if "  # the reader's summary\n  - id: summary\n" not in stored:  # the template may already have this comment
            stored = stored.replace("  - id: summary\n", "  # the reader's summary\n  - id: summary\n")
        stored = stored.replace("      prompt: |\n        Task: Write the opening",
                                "      # the opening\n      prompt: |\n        Task: Write the opening")
        self.assertIn("# bump me", stored)
        self.assertIn("# the opening", stored)
        path.write_text(stored, encoding="utf-8")
        model = schema.parse(stored).data
        model["version"] = "9.9"
        model["nodes"].insert(0, model["nodes"].pop(3))  # a node moved: its comment moves with it
        self.assertEqual(templates.save_model("mine", model, self.home), {"saved": True, "comments": 0})
        saved = path.read_text(encoding="utf-8")
        self.assertTrue(saved.startswith("# Built-in template"), "the header comment is kept")
        self.assertIn("# bump me\nversion: '9.9'", saved)
        self.assertIn("  # the reader's summary\n  - id: summary\n", saved)
        self.assertIn("      # the opening\n      prompt: |\n", saved)
        self.assertEqual(schema.parse(saved).data, model)

    def test_saving_asks_before_comments_of_a_removed_node_are_lost(self):
        text = templates.read("builtin", "document-comparison", self.home)
        templates.import_text(templates.with_id(text, "mine"), self.home)
        path = self.home / "templates" / "mine.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("  - id: export\n", "  # save it\n  - id: export\n"),
                        encoding="utf-8")
        model = schema.parse(path.read_text(encoding="utf-8")).data
        model["nodes"] = [n for n in model["nodes"] if n["id"] != "export"]
        model["connections"] = [c for c in model["connections"] if c["to"] != "export"]
        model["outputs"] = []
        before = path.read_text(encoding="utf-8")
        self.assertEqual(templates.save_model("mine", model, self.home), {"saved": False, "comments": 1})
        self.assertEqual(path.read_text(encoding="utf-8"), before, "nothing is written before the user agrees")
        self.assertEqual(templates.save_model("mine", model, self.home, drop_comments=True), {"saved": True, "comments": 1})
        saved = path.read_text(encoding="utf-8")
        self.assertTrue(saved.startswith("# Built-in template"))
        self.assertNotIn("save it", saved)
        self.assertEqual(schema.parse(saved).data, model)
        self.assertEqual(templates.save_model("mine", model, self.home)["saved"], True)

    def test_invalid_models_and_builtins_are_not_saved(self):
        with self.assertRaises(TemplateError) as e:
            templates.save_model("document-comparison", {"id": "document-comparison"}, self.home)
        self.assertEqual(e.exception.code, 403)
        templates.create_model(FULL, self.home)
        bad = copy.deepcopy(FULL)
        bad["connections"] = bad["connections"][1:]
        with self.assertRaises(TemplateError) as e:
            templates.save_model("full-flow", bad, self.home, drop_comments=True)
        self.assertIn("no connection read.text → think", e.exception.messages[0])
        with self.assertRaises(TemplateError) as e:
            templates.create_model(FULL, self.home)
        self.assertEqual(e.exception.code, 409)


class ServerCase(HomeCase):
    """A real server on a free port (as in test_mehteran_web)."""

    def setUp(self):
        super().setUp()
        self.app = web.App(self.engine())
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        self.port = self.server.server_address[1]
        self.server.RequestHandlerClass = web.make_handler(self.app, self.port)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def json(self, method, path, body=None, token=True, host=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        if token:
            req.add_header("X-Token", self.app.token)
        if host:
            req.add_header("Host", host)
        req.add_header("X-Lang", "en")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())


class EditorRouteTests(ServerCase):

    def test_new_routes_need_token_and_host(self):
        for method, path in (("POST", "/api/editor/check"), ("POST", "/api/editor/yaml"), ("POST", "/api/editor/parse"),
                             ("POST", "/api/editor/rename"), ("POST", "/api/templates/new"), ("PUT", "/api/templates/user/x/model"),
                             ("GET", "/api/tools"), ("POST", "/api/tools/claude/install"), ("POST", "/api/models/test")):
            self.assertEqual(self.json(method, path, body={}, token=False)[0], 403, path)
            self.assertEqual(self.json(method, path, body={}, host="evil.test:80")[0], 403, path)

    def test_check_returns_problems_with_places_and_ports(self):
        status, data = self.json("POST", "/api/editor/check", body={"model": FULL})
        self.assertEqual((status, data["valid"]), (200, True))
        self.assertEqual(data["ports"]["save"], {"md": "file", "html": "file"})
        bad = copy.deepcopy(FULL)
        bad["connections"].pop(0)
        status, data = self.json("POST", "/api/editor/check", body={"model": bad})
        self.assertFalse(data["valid"])
        self.assertIn({"where": "nodes.think.config.prompt",
                       "message": "'{{nodes.read.text}}' is used but there is no connection read.text → think. Add it under connections."},
                      data["problems"])
        self.assertEqual(self.json("POST", "/api/editor/check", body={"model": [1]})[0], 400)

    def test_wrong_value_types_are_problems_not_errors(self):
        """Every value of a valid model replaced by a list, a mapping, a number, null and a text: always 200."""
        def places(value, path=()):
            yield path
            if isinstance(value, dict):
                for k, v in value.items():
                    yield from places(v, path + (k,))
            elif isinstance(value, list):
                for i, v in enumerate(value):
                    yield from places(v, path + (i,))
        for path in list(places(FULL))[1:]:
            for wrong in ([1, "x"], {"k": [1]}, 7, None, "{{nodes.ghost.x}}", True, [{"a": 1}]):
                model = copy.deepcopy(FULL)
                target = model
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = wrong
                status, data = self.json("POST", "/api/editor/check", body={"model": model})
                self.assertEqual(status, 200, (path, wrong, data))
                self.assertEqual(self.json("POST", "/api/editor/yaml", body={"model": model})[0], 200, (path, wrong))

    def test_yaml_and_back(self):
        status, data = self.json("POST", "/api/editor/yaml", body={"model": FULL})
        self.assertEqual(status, 200)
        status, back = self.json("POST", "/api/editor/parse", body={"yaml": data["yaml"]})
        self.assertEqual((status, back["model"], back["valid"]), (200, FULL, True))
        # Text that is not a mapping is refused with its problem, so the editor keeps it on the YAML tab.
        status, err = self.json("POST", "/api/editor/parse", body={"yaml": "a: [unclosed\n"})
        self.assertEqual(status, 400)
        self.assertIn("Cannot read the YAML", err["error"])
        self.assertEqual(self.json("POST", "/api/editor/parse", body={"yaml": "- a\n"})[0], 400)
        # YAML types without a JSON form (dates, NaN) come back as text instead of a server error.
        status, back = self.json("POST", "/api/editor/parse", body={"yaml": "id: x\nversion: 2024-01-02\nx: .nan\n"})
        self.assertEqual((status, back["model"]["version"], back["model"]["x"]), (200, "2024-01-02", "nan"))

    def test_rename_route(self):
        status, data = self.json("POST", "/api/editor/rename", body={"model": FULL, "kind": "nodes", "old": "read", "new": "extract"})
        self.assertEqual(status, 200)
        self.assertIn("{{nodes.extract.text}}", data["model"]["nodes"][1]["config"]["prompt"])
        for new in ("Bad", "x\n", "odd", ""):
            status, data = self.json("POST", "/api/editor/rename", body={"model": FULL, "kind": "nodes", "old": "read", "new": new})
            self.assertEqual(status, 400, new)

    def test_create_and_save_from_the_model(self):
        status, data = self.json("POST", "/api/templates/new", body={"model": FULL})
        self.assertEqual((status, data["ref"]), (200, "user:full-flow"))
        self.assertEqual(self.json("POST", "/api/templates/new", body={"model": FULL})[0], 409)
        for bad_id in ("Bad", "full-flow\n", "../x", 5):
            self.assertEqual(self.json("POST", "/api/templates/new", body={"model": {**FULL, "id": bad_id}})[0], 400, bad_id)
        changed = {**FULL, "version": "3"}
        status, data = self.json("PUT", "/api/templates/user/full-flow/model", body={"model": changed})
        self.assertEqual(data, {"saved": True, "comments": 0})
        status, tpl = self.json("GET", "/api/templates/user/full-flow")
        self.assertEqual(tpl["model"], changed)
        self.assertIn("prompt: |", tpl["yaml"])
        invalid = {**changed, "connections": []}
        status, data = self.json("PUT", "/api/templates/user/full-flow/model", body={"model": invalid})
        self.assertEqual(status, 400)
        self.assertGreaterEqual(len(data["problems"]), 5)
        self.assertEqual(self.json("PUT", "/api/templates/user/Bad/model", body={"model": FULL})[0], 404)
        self.assertEqual(self.json("PUT", "/api/templates/user/full-flow%0A/model", body={"model": FULL})[0], 404)
        self.assertEqual(self.json("PUT", "/api/templates/builtin/document-comparison/model", body={"model": FULL})[0], 404)
        self.assertEqual(self.json("PUT", "/api/templates/user/document-comparison/model", body={"model": FULL})[0], 403)

    def test_info_describes_the_node_types(self):
        status, info = self.json("GET", "/api/info")
        extract = info["node_types"]["document.extract"]
        self.assertEqual(extract["config"]["file"]["kind"], "template")
        self.assertEqual(info["node_types"]["ai.cli"]["config"]["provider"]["widget"], "provider")
        self.assertEqual(info["node_types"]["document.export"]["outputs"], {"md": "file"})
        self.assertFalse(info["node_types"]["approval"]["takes_retries"])
        self.assertEqual(info["formats"], ["md", "docx", "html", "pdf", "epub", "eml", "json", "csv"])
        self.assertTrue(info["node_types"]["ai.cli"]["description"]["tr"])


def fake_status(tool):
    return {"id": tool, "name": tool, "provider": web.tools.TOOLS[tool]["provider"], "installed": tool != "codex",
            "version": "1.0", "signed_in": tool == "claude", "sign_in_info": "", "login_command": "x"}


@mock.patch.object(web.tools, "extend_path", lambda *a: None)
class SetupRouteTests(ServerCase):
    """The Setup tab's routes. Every call into pipeline.tools is mocked: nothing is installed, signed in or run."""

    def test_tools_status(self):
        with mock.patch.object(web.tools, "status", side_effect=fake_status), \
                mock.patch.object(web.system, "can_open_terminal", return_value=True):
            status, data = self.json("GET", "/api/tools")
        self.assertEqual(status, 200)
        by = {t["id"]: t for t in data["tools"]}
        self.assertIn("Academic paper review", by["claude"]["templates"])
        self.assertTrue(by["claude"]["required"] and by["pdf"]["required"])
        self.assertFalse(by["gemini"]["configured"])  # not in the fake config: Mehteran cannot use it
        self.assertEqual(data["runs"], 0)
        self.assertTrue(by["pdf"]["requirements"])

    def test_install_starts_mehterans_installer_without_running_it(self):
        with mock.patch.object(web.Jobs, "start") as start:
            status, data = self.json("POST", "/api/tools/claude/install")
        self.assertEqual(status, 200)
        argv = start.call_args.args[1]
        self.assertEqual(argv[1:], ["-m", "mehteran", "install", "claude"])
        self.assertTrue(str(start.call_args.args[2]).startswith(str(self.home)))
        self.assertEqual(self.json("POST", "/api/tools/nope/install")[0], 404)
        with mock.patch.object(web.Jobs, "start") as start, mock.patch.object(web.shutil, "which", return_value=None):
            self.json("POST", "/api/tools/install-missing")
        self.assertIn("pdf", start.call_args.args[1])
        self.assertIn("claude", start.call_args.args[1])
        self.assertNotIn("gemini", start.call_args.args[1])  # no template uses it
        with mock.patch.object(web.Jobs, "start") as start, mock.patch.object(web.shutil, "which", return_value="/bin/x"):
            status, data = self.json("POST", "/api/tools/install-missing")
        start.assert_not_called()
        self.assertEqual(data["message"], "All tools are already installed.")

    def test_sign_in_and_model_test(self):
        with mock.patch.object(web.tools, "login", return_value="ok") as login:
            status, data = self.json("POST", "/api/tools/codex/login", body={"method": "key", "key": "k" * 30})
        self.assertEqual((status, data["message"]), (200, "ok"))
        login.assert_called_once_with("codex", "key", "k" * 30)
        self.assertEqual(self.json("POST", "/api/tools/pdf/login", body={})[0], 404)
        with mock.patch("pipeline.providers.run", return_value="OK") as run:
            status, data = self.json("POST", "/api/models/test", body={"name": "fake/small@high"})
        self.assertEqual(status, 200)
        self.assertIn("OK", data["message"])
        self.assertEqual(run.call_args.args[1], "fake/small@high")
        self.assertEqual(self.json("POST", "/api/models/test", body={"name": "nope"})[0], 400)
        self.assertEqual(self.json("POST", "/api/models/test", body={"name": "-rm"})[0], 400)

    def test_model_lists_are_kept_in_mehterans_own_folder(self):
        with mock.patch.object(web.tools, "list_models", return_value=["opus", "sonnet"]):
            status, data = self.json("GET", "/api/tools/claude/models")
        self.assertEqual(data["models"], ["opus", "sonnet"])
        stored = json.loads((self.home / "configurations" / "models.json").read_text(encoding="utf-8"))
        self.assertEqual(stored, {"claude": ["opus", "sonnet"]})
        status, info = self.json("GET", "/api/info")
        self.assertEqual(next(p for p in info["providers"] if p["name"] == "claude")["models"], ["opus", "sonnet"])
        with mock.patch.object(web.tools, "list_models", return_value=[]):
            self.assertEqual(self.json("GET", "/api/tools/claude/models")[1]["models"], ["opus", "sonnet"])
        self.assertEqual(self.json("GET", "/api/tools/pdf/models")[0], 404)


if __name__ == "__main__":
    unittest.main()
