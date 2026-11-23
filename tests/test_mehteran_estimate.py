"""The run window's estimate (mehteran/estimate.py, POST /api/templates/<source>/<id>/estimate) and the first-start
welcome of the library (GET/PUT /api/welcome)."""

import json
import sys
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, fake_cfg  # noqa: E402

from mehteran import estimate, schema, templates, web  # noqa: E402
from mehteran.web import App, make_handler  # noqa: E402

WORKFLOW = """
schema_version: 1
id: estimate-sample
name: Estimate sample
inputs:
  - {id: notes, type: text}
  - {id: model, type: provider, default: claude}
  - {id: second, type: provider, default: "fake/small@low"}
nodes:
  - id: draft
    type: ai.cli
    config: {provider: "{{inputs.model}}", prompt: "Draft: {{inputs.notes}}"}
  - id: parts
    type: ai.map
    retries: 1
    config: {provider: "{{inputs.second}}", source: "{{nodes.draft.text}}", prompt: "Shorten.", max_items: 7}
  - id: good
    type: condition
    config: {operator: ai, provider: "{{inputs.model}}", question: "Is it good?", value: "{{nodes.draft.text}}"}
  - id: polish
    type: ai.cli
    retries: 0
    config: {provider: chatgpt, prompt: "Polish: {{nodes.good.true}}"}
  - id: plain
    type: condition
    config: {operator: contains, value: "{{nodes.draft.text}}", match: "x"}
  - id: join
    type: text.merge
    config: {}
connections:
  - {from: draft.text, to: parts}
  - {from: draft.text, to: good}
  - {from: good.true, to: polish}
  - {from: draft.text, to: plain}
  - {from: parts.text, to: join}
  - {from: polish.text, to: join}
"""


class EstimateTests(HomeCase):
    def estimate(self, values=None):
        return estimate.estimate(schema.parse(WORKFLOW), values or {}, fake_cfg())

    def test_counts_per_step(self):
        steps = {s["node"]: s for s in self.estimate()["steps"]}
        self.assertEqual(set(steps), {"draft", "parts", "good", "polish"})  # no model: plain (not "ai"), join
        # ai.cli: one call per attempt; its default is 2 retries.
        self.assertEqual((steps["draft"]["calls"], steps["draft"]["retries"], steps["draft"]["max_calls"]), (1, 2, 3))
        # ai.map: one call per part, counted only as a bound (max_items parts per attempt).
        self.assertEqual((steps["parts"]["calls"], steps["parts"]["per_part"], steps["parts"]["max_parts"],
                          steps["parts"]["max_calls"]), (0, True, 7, 14))
        # an "ai" condition: one call, a second one when the answer is unclear; no retries by default.
        self.assertEqual((steps["good"]["calls"], steps["good"]["max_calls"], steps["good"]["conditional"]), (1, 2, False))
        self.assertEqual((steps["polish"]["calls"], steps["polish"]["max_calls"], steps["polish"]["conditional"]), (1, 1, True))

    def test_totals_and_models(self):
        found = self.estimate()
        self.assertEqual((found["calls"], found["loops"], found["max_parts"], found["conditional"], found["max_calls"]),
                         (3, 1, 7, 1, 20))
        models = {m["model"]: m for m in found["models"]}
        self.assertEqual(list(models), ["claude", "fake/small@low", "chatgpt"])
        self.assertEqual((models["claude"]["provider"], models["claude"]["calls"], models["claude"]["max_calls"]), ("claude", 2, 5))
        self.assertEqual((models["fake/small@low"]["provider"], models["fake/small@low"]["calls"],
                          models["fake/small@low"]["loops"], models["fake/small@low"]["max_parts"]), ("fake", 0, 1, 7))
        self.assertTrue(all(m["configured"] for m in models.values()))

    def test_a_chosen_model_moves_the_calls(self):
        found = self.estimate({"model": "fake/large", "second": "fake/large"})
        models = {m["model"]: m for m in found["models"]}
        self.assertEqual(list(models), ["fake/large", "chatgpt"])
        self.assertEqual((models["fake/large"]["calls"], models["fake/large"]["loops"]), (2, 1))
        self.assertEqual(found["max_calls"], 20)  # the same steps: the same bound
        unknown = self.estimate({"model": "nobody/x"})["models"][0]
        self.assertEqual((unknown["provider"], unknown["configured"]), ("nobody", False))
        self.assertEqual(self.estimate({"model": "--flag"})["models"][0]["provider"], "")  # not a model name

    def test_a_workflow_without_models(self):
        wf = schema.parse("schema_version: 1\nid: no-model\nname: No model\ninputs:\n  - {id: a, type: text}\n"
                          "nodes:\n  - {id: join, type: text.merge, config: {template: \"{{inputs.a}}\"}}\n")
        self.assertEqual(estimate.estimate(wf, {}, fake_cfg()),
                         {"steps": [], "models": [], "calls": 0, "loops": 0, "max_parts": 0, "conditional": 0, "max_calls": 0,
                          "privacy": "", "refused": 0})

    def test_every_builtin_template_has_an_estimate(self):
        for item in templates.listing(self.home):
            wf = schema.parse(templates.read(item["source"], item["id"], self.home))
            found = estimate.estimate(wf, {}, fake_cfg())
            self.assertGreaterEqual(found["max_calls"], found["calls"], item["id"])
            self.assertTrue(found["steps"], item["id"])  # every built-in template asks a model


class WebCase(HomeCase):
    def setUp(self):
        super().setUp()
        root = mock.patch.object(web, "ROOT", self.tmp / "trroot")  # no books of the real translation app
        root.start()
        self.addCleanup(root.stop)
        self.app = App(self.engine())
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        self.port = self.server.server_address[1]
        self.server.RequestHandlerClass = make_handler(self.app, self.port)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def json(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=data, method=method)
        req.add_header("X-Token", self.app.token)
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())


class EstimateApiTests(WebCase):
    def test_estimate_of_a_template(self):
        status, found = self.json("POST", "/api/templates/builtin/document-explainer/estimate", {"values": {}})
        self.assertEqual(status, 200)
        self.assertEqual((found["calls"], found["loops"], found["max_calls"]), (2, 0, 6))
        self.assertEqual([(m["model"], m["tool"], m["tool_name"], m["calls"]) for m in found["models"]],
                         [("claude", "claude", "Claude Code", 2)])
        # The form's model choice: one step moves to the other tool.
        status, found = self.json("POST", "/api/templates/builtin/document-explainer/estimate",
                                  {"values": {"review_model": "chatgpt/gpt-x@high"}})
        self.assertEqual([(m["model"], m["tool"], m["calls"]) for m in found["models"]],
                         [("claude", "claude", 1), ("chatgpt/gpt-x@high", "codex", 1)])
        self.assertIsNone(self.json("POST", "/api/templates/builtin/document-explainer/estimate",
                                    {"values": {"model": "fake"}})[1]["models"][0]["tool"])  # no tool of the Setup tab

    def test_bad_requests(self):
        self.assertEqual(self.json("POST", "/api/templates/builtin/no-such-flow/estimate", {})[0], 404)
        self.assertEqual(self.json("POST", "/api/templates/builtin/document-explainer/estimate", {"values": []})[0], 200)
        self.assertEqual(self.json("POST", "/api/templates/builtin/document-explainer/estimate", {"values": "x"})[0], 400)


class WelcomeTests(WebCase):
    def test_shown_at_first_with_choices_that_exist(self):
        status, found = self.json("GET", "/api/welcome")
        self.assertEqual((status, found["show"]), (200, True))
        self.assertEqual([c["id"] for c in found["choices"]], ["document", "writing", "data", "education", "research"])
        known = {item["id"]: item for item in templates.listing(self.home) if item["source"] == "builtin"}
        for choice in found["choices"]:
            self.assertEqual({"run": 1}.get(choice["action"], len(choice["templates"])), len(choice["templates"]))
            for template_id in choice["templates"]:
                self.assertIn(template_id, known)
            if choice["action"] == "category":
                self.assertEqual({known[x]["category"] for x in choice["templates"]}, {choice["category"]})
            if choice["action"] != "translation":
                self.assertEqual(choice["providers"], ["claude"], choice["id"])  # the templates' default model
        # Every template named in the choices is in the library (a renamed template would drop out silently).
        named = [x for _, target in web.WELCOME_CHOICES for x in (target.get("templates") or [target.get("template")]) if x]
        self.assertEqual([x for x in named if x not in known], [])
        self.assertFalse((self.home / "configurations" / "library.json").exists())  # asking writes nothing

    def test_dismissed_for_good_and_favorites_keep_it(self):
        self.assertEqual(self.json("PUT", "/api/welcome", {"dismissed": False})[0], 400)
        self.assertEqual(self.json("PUT", "/api/welcome", {"dismissed": True}), (200, {"show": False}))
        self.assertEqual(self.json("GET", "/api/welcome"), (200, {"show": False}))
        self.json("PUT", "/api/templates/builtin/document-explainer/favorite", {"on": True})  # the same file
        stored = json.loads((self.home / "configurations" / "library.json").read_text(encoding="utf-8"))
        self.assertEqual(stored, {"welcome_closed": "dismissed", "favorites": ["builtin:document-explainer"]})
        self.assertEqual(App(self.engine()).welcome(None, {}), {"show": False})  # a restart

    def test_not_shown_after_a_run(self):
        workflow = ("schema_version: 1\nid: tiny\nname: Tiny\ninputs:\n  - {id: a, type: text}\n"
                    "nodes:\n  - {id: join, type: text.merge, config: {template: \"{{inputs.a}}\"}}\n")
        self.app.engine.start(workflow, {"a": "x"})
        self.assertEqual(self.json("GET", "/api/welcome"), (200, {"show": False}))
        stored = json.loads((self.home / "configurations" / "library.json").read_text(encoding="utf-8"))
        self.assertEqual(stored["welcome_closed"], "used")

    def test_standalone_book_translation_does_not_hide_welcome(self):
        work = self.tmp / "trroot" / "books" / "kitap" / "work"
        work.mkdir(parents=True)
        (work / "run.json").write_text(json.dumps({"state": "finished", "started": 1.0}), encoding="utf-8")
        status, data = self.json("GET", "/api/welcome")
        self.assertEqual(status, 200)
        self.assertTrue(data["show"])


if __name__ == "__main__":
    import unittest
    unittest.main()
