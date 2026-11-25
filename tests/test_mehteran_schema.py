"""Mehteran workflow schema: every rejection case, the bilingual messages and single-pass placeholders."""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, ai, workflow  # noqa: E402

from mehteran import i18n, placeholders, schema  # noqa: E402

VALID = workflow(ai("a", "TASK:a") + ai("b", "TASK:b {{nodes.a.text}}"), [("a.text", "b")])


def problems(text: str) -> list[str]:
    try:
        schema.parse(text)
    except schema.WorkflowError as e:
        return e.messages()
    return []


class SchemaTests(HomeCase):
    def assertRejected(self, text: str, *fragments: str):
        found = problems(text)
        self.assertTrue(found, "the workflow was accepted")
        for fragment in fragments:
            self.assertTrue(any(fragment in p for p in found), f"{fragment!r} not in {found}")

    def test_valid_workflow_parses(self):
        wf = schema.parse(VALID)
        self.assertEqual(wf.order, ["a", "b"])
        self.assertEqual(wf.upstream["b"], {"a"})
        self.assertEqual(wf.graph()["nodes"][1]["layer"], 1)

    def test_localized_text_default_and_override(self):
        text = workflow(ai("a", "Read {{inputs.reader}}"), [], inputs=(
            "  - {id: reader, type: text, default: {tr: okur, en: reader}}\n"))
        engine = self.engine()
        try:
            for lang, expected in (("tr", "okur"), ("en", "reader"), ("de", "reader")):
                i18n.set_request(lang)
                run = engine.start(text, launch=False)
                self.assertEqual(engine.get(run)["inputs"]["reader"], expected)
            run = engine.start(text, {"reader": "custom"}, launch=False)
            self.assertEqual(engine.get(run)["inputs"]["reader"], "custom")
        finally:
            i18n.set_request(None)
        for invalid in ("{}", "{tr: 12}", "{other: reader}"):
            self.assertTrue(problems(text.replace("{tr: okur, en: reader}", invalid)))

    def test_unknown_keys_are_rejected_at_every_level(self):
        self.assertRejected(VALID + "colour: red\n", "colour: unknown key")
        self.assertRejected(VALID.replace("type: ai.cli,", "type: ai.cli, speed: 3,", 1), "nodes.a.speed: unknown key")
        self.assertRejected(VALID.replace("provider: fake,", "provider: fake, temperature: 1,", 1),
                            "nodes.a.config.temperature: unknown key")
        self.assertRejected(VALID.replace("  - {from: a.text, to: b}", "  - {from: a.text, to: b, via: x}"),
                            "connections[0].via: unknown key")

    def test_ids_must_be_unique_and_well_formed(self):
        self.assertRejected(workflow(ai("a", "x") + ai("a", "y"), []), "the id 'a' is used more than once")
        self.assertRejected(workflow(ai("Bad", "x"), []), "'Bad' is not a valid id")
        self.assertRejected(workflow(ai("a", "x"), [], inputs="  - {id: q, type: text}\n  - {id: q, type: text}\n"),
                            "the id 'q' is used more than once")

    def test_connections_must_reference_existing_nodes_and_ports(self):
        self.assertRejected(VALID.replace("{from: a.text, to: b}", "{from: zz.text, to: b}"), "there is no node 'zz'")
        self.assertRejected(VALID.replace("{from: a.text, to: b}", "{from: a.nope, to: b}"), "node 'a' has no output 'nope'")
        self.assertRejected(VALID.replace("{from: a.text, to: b}", "{from: a.text, to: qq}"), "there is no node 'qq'")
        self.assertRejected(VALID.replace("{from: a.text, to: b}", "{from: a.text, to: a}"), "cannot connect to itself")

    def test_graph_must_be_acyclic(self):
        text = workflow(ai("a", "{{nodes.c.text}}") + ai("b", "{{nodes.a.text}}") + ai("c", "{{nodes.b.text}}"),
                        [("a.text", "b"), ("b.text", "c"), ("c.text", "a")])
        self.assertRejected(text, "the connections form a cycle: a, b, c")

    def test_wrong_value_types_are_problems_not_crashes(self):
        self.assertRejected(workflow("  - {id: a, type: [x], config: {}}\n", []), "nodes.a.type: unknown node type")
        self.assertRejected(workflow(ai("a", "x") + "  - {id: e, type: document.export, config: zzz}\n", [("e.md", "a")]),
                            "nodes.e.config: must be a mapping")
        self.assertRejected(workflow(ai("a", "x"), []).replace("id: test-flow", 'id: "test\\n"'),
                            "is not a valid id")

    def test_node_type_must_be_registered(self):
        self.assertRejected(workflow("  - {id: a, type: shell.exec, config: {cmd: ls}}\n", []),
                            "unknown node type 'shell.exec'")

    def test_references_must_resolve(self):
        self.assertRejected(workflow(ai("a", "{{inputs.missing}}"), []), "'{{inputs.missing}}': there is no such input")
        self.assertRejected(workflow(ai("a", "{{nodes.ghost.text}}"), []), "'{{nodes.ghost.text}}': there is no such node")
        self.assertRejected(VALID.replace("{{nodes.a.text}}", "{{nodes.a.answer}}"), "the node has no such output")
        self.assertRejected(workflow(ai("a", "{{ secrets }}"), []), "is not a valid placeholder")
        # A node may only use the output of a node that is connected to it.
        self.assertRejected(workflow(ai("a", "x") + ai("b", "{{nodes.a.text}}"), []),
                            "there is no connection a.text → b")

    def test_credentials_are_rejected(self):
        self.assertRejected(VALID.replace("provider: fake,", "provider: fake, api_key: abc,", 1), "Credentials")
        self.assertRejected(VALID.replace("TASK:a", "use key sk-ant-abcdefghijklmnopqrstuvwxyz0123"), "looks like an API key")

    def test_input_rules(self):
        base = ai("a", "{{inputs.x}}")
        self.assertRejected(workflow(base, [], inputs="  - {id: x, type: number}\n"), "type must be one of")
        self.assertRejected(workflow(base, [], inputs="  - {id: x, type: choice, options: [a, b], default: c}\n"),
                            "the default must be one of the options")
        self.assertRejected(workflow(base, [], inputs="  - {id: x, type: choice}\n"), "a choice input needs options")
        self.assertRejected(workflow(base, [], inputs="  - {id: x, type: file, formats: [exe]}\n"), "must be a non-empty list of")
        self.assertRejected(workflow(base, [], inputs="  - {id: x, type: text, formats: [md]}\n"),
                            "only for inputs of type 'file'")
        self.assertRejected(workflow(ai("a", "x", provider="'{{inputs.x}}'"), [], inputs="  - {id: x, type: text}\n"),
                            "an input of type 'provider'")
        # A "language" input offers every language of the registry; its default, when given, is a language code.
        self.assertEqual(problems(workflow(base, [], inputs="  - {id: x, type: language}\n")), [])
        self.assertEqual(problems(workflow(base, [], inputs="  - {id: x, type: language, default: uz}\n")), [])
        self.assertRejected(workflow(base, [], inputs="  - {id: x, type: language, default: klingon}\n"),
                            "'klingon' is not a known language code")
        self.assertRejected(workflow(base, [], inputs="  - {id: x, type: language, options: [tr, en]}\n"),
                            "only for inputs of type 'choice'")

    def test_type_specific_rules(self):
        self.assertRejected(workflow("  - {id: e, type: document.extract, config: {file: notes.pdf}}\n", []),
                            "exactly one file placeholder")
        self.assertRejected(workflow("  - {id: ok, type: approval, retries: 2, config: {show: x}}\n", []),
                            "takes no retries and no timeout")
        self.assertRejected(workflow(ai("a", "x", retries=99), []), "from 0 to 10")
        self.assertRejected(workflow("  - {id: x, type: document.export, config: {source: a, formats: [odt]}}\n", []),
                            "must be a non-empty list of: md, docx, html, pdf, epub")
        self.assertRejected(workflow(ai("a", "x"), []).replace("provider: fake", "provider: '-rm'"),
                            "not a valid provider name")

    def test_top_level_rules(self):
        self.assertRejected(VALID.replace("schema_version: 1", "schema_version: 2"), "schema_version must be 1")
        self.assertRejected(VALID.replace("name: Test flow", "name: {de: Ablauf}"), "name: must be a non-empty text")
        self.assertRejected(VALID.replace("name: Test flow\n", ""), "name: is required")
        self.assertRejected("schema_version: 1\nid: x\nname: x\nnodes: []\n", "at least one node")
        self.assertRejected("- just\n- a list\n", "must be a mapping")
        self.assertRejected("a: [unclosed\n", "Cannot read the YAML")
        self.assertRejected(VALID + "name: twice\n", "duplicate key 'name'")
        self.assertRejected(VALID + "outputs:\n  - {id: r, from: a}\n", "'from' must be <node>.<output>")

    def test_all_problems_are_listed_at_once(self):
        text = workflow(ai("a", "{{inputs.nope}}") + ai("a", "x") + "  - {id: c, type: magic}\n", [("zz.text", "c")])
        found = problems(text + "extra: 1\n")
        self.assertGreaterEqual(len(found), 4, found)

    def test_messages_are_bilingual(self):
        text = workflow(ai("a", "{{inputs.nope}}"), [])
        english = problems(text)
        i18n.set_default("tr")
        turkish = problems(text)
        self.assertNotEqual(english, turkish)
        self.assertIn("böyle bir girdi yok", turkish[0])


class PlaceholderTests(unittest.TestCase):
    def test_substitution_is_a_single_pass(self):
        values = {"inputs.doc": "text with {{inputs.secret}} inside", "inputs.secret": "SECRET"}
        out = placeholders.render("A: {{inputs.doc}} B: {{ inputs.secret }}", values.__getitem__)
        self.assertEqual(out, "A: text with {{inputs.secret}} inside B: SECRET")

    def test_parse_and_only_reference(self):
        self.assertEqual(placeholders.parse("nodes.a.text"), ("nodes", "a", "text"))
        self.assertEqual(placeholders.parse("inputs.paper"), ("inputs", "paper", ""))
        self.assertIsNone(placeholders.parse("nodes.a"))
        self.assertIsNone(placeholders.parse("env.HOME"))
        self.assertEqual(placeholders.only_reference(" {{inputs.paper}} "), "inputs.paper")
        self.assertIsNone(placeholders.only_reference("x {{inputs.paper}}"))


if __name__ == "__main__":
    unittest.main()
