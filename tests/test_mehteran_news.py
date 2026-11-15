"""News feeds and the parts the news bulletins use: RSS and Atom feeds read as text (urlfetch.feed_text), a url input
with several addresses, a condition that passes on another text, and links in the HTML and Word exports.
No request leaves this computer: urlfetch.fetch is replaced.
"""

import io
import sys
import unittest
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, ai, workflow  # noqa: E402

from mehteran import schema, tables, urlfetch  # noqa: E402
from mehteran.engine import RunError  # noqa: E402

NOW = datetime(2026, 11, 15, 12, 0, tzinfo=timezone.utc)
RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel><title>Lab news</title>
<item><title>Old story</title><link>https://example.com/old</link><pubDate>Mon, 02 Nov 2026 08:00:00 +0000</pubDate>
<description>From two weeks ago.</description></item>
<item><title>New model released</title><link>https://example.com/new</link><pubDate>Fri, 13 Nov 2026 09:30:00 +0000</pubDate>
<description>&lt;p&gt;The lab &lt;b&gt;released&lt;/b&gt; a model.&lt;/p&gt;</description></item>
<item><title>Undated note</title><guid>https://example.com/note</guid><description>No date.</description></item>
<item><title>Newest</title><link>/relative</link><pubDate>Sat, 14 Nov 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""
ATOM = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Atom blog</title>
<entry><title>Atom entry</title><link rel="alternate" href="https://example.org/entry"/><link rel="self" href="https://example.org/self"/>
<updated>2026-11-14T07:00:00Z</updated><summary>Short summary.</summary></entry>
</feed>"""
BOMB = b"""<?xml version="1.0"?><!DOCTYPE r [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;">]><rss><channel><title>&b;</title></channel></rss>"""


class FeedTextTests(unittest.TestCase):
    def test_rss_items_newest_first_with_dates_links_and_summaries(self):
        text = urlfetch.feed_text(RSS, "https://example.com/feed.xml", now=NOW)
        self.assertTrue(text.startswith("# Lab news"))
        self.assertIn("Items: 4 of 4", text)
        order = [text.index(t) for t in ("## Newest", "## New model released", "## Old story", "## Undated note")]
        self.assertEqual(order, sorted(order))
        self.assertIn("- Published: 2026-11-13 09:30 UTC", text)
        self.assertIn("- Link: https://example.com/relative", text)  # a relative link, made absolute
        self.assertIn("- Link: https://example.com/note", text)  # the guid when there is no link
        self.assertIn("The lab released a model.", text)  # the HTML of a summary becomes text
        self.assertNotIn("<b>", text)

    def test_max_age_days_keeps_the_last_days_and_undated_items(self):
        text = urlfetch.feed_text(RSS, "https://example.com/feed.xml", max_age_days=7, now=NOW)
        self.assertNotIn("Old story", text)
        self.assertIn("Undated note", text)
        self.assertIn("Items: 3 of 4, published 2026-11-13 to 2026-11-14; the last 7 days up to 2026-11-15 12:00 UTC.", text)
        empty = urlfetch.feed_text(RSS, "https://example.com/feed.xml", max_age_days=1, now=datetime(2027, 1, 1, tzinfo=timezone.utc))
        self.assertIn("Undated note", empty)
        self.assertNotIn("Newest", empty)

    def test_atom_uses_the_alternate_link(self):
        text = urlfetch.feed_text(ATOM, "https://example.org/atom", now=NOW)
        self.assertIn("## Atom entry", text)
        self.assertIn("- Link: https://example.org/entry", text)
        self.assertNotIn("/self", text)
        self.assertIn("- Published: 2026-11-14 07:00 UTC", text)

    def test_entities_and_broken_xml_are_refused(self):
        late = b"<?xml version='1.0'?><!--" + b" " * 70_000 + b"--><!DOCTYPE rss SYSTEM 'file:///etc/passwd'><rss/>"
        utf16 = BOMB.decode().replace('version="1.0"', 'version="1.0" encoding="UTF-16"').encode("utf-16")
        for body in (BOMB, late, utf16, b"<rss><channel><title>x</title>", b"<html><body>not a feed</body></html>"):
            with self.subTest(body=body[:30]), self.assertRaises(urlfetch.FetchError):
                urlfetch.feed_text(body, "https://example.com/f")

    def test_a_feed_is_recognised_by_its_type_or_its_start(self):
        self.assertTrue(urlfetch.is_feed("application/rss+xml", b""))
        self.assertTrue(urlfetch.is_feed("text/html", b'\xef\xbb\xbf<?xml version="1.0"?>\n<?xml-stylesheet href="x"?>\n<rss>'))
        self.assertTrue(urlfetch.is_feed("text/plain", b"<feed xmlns='http://www.w3.org/2005/Atom'>"))
        self.assertFalse(urlfetch.is_feed("text/html", b"<!doctype html><html>"))

    def test_read_url_reads_a_feed(self):
        with mock.patch.object(urlfetch, "fetch", lambda url, abort=None: (url, "text/xml", "utf-8", RSS)):
            self.assertIn("## New model released", urlfetch.read_url("https://example.com/feed.xml"))


FEEDS = {
    "https://a.example/feed": ("application/rss+xml", RSS),
    "https://b.example/atom": ("application/atom+xml", ATOM),
}


def fake_fetch(url, abort=None):
    if url not in FEEDS:
        raise urlfetch.FetchError(f"cannot read {url}")
    kind, body = FEEDS[url]
    return url, kind, "utf-8", body


class SeveralAddressesTests(HomeCase):
    FLOW = workflow("  - {id: read, type: document.extract, config: {file: '{{inputs.feeds}}', max_age_days: '{{inputs.days}}'}}\n"
                    + "  - {id: each, type: ai.map, config: {source: '{{nodes.read.text}}', split: files, provider: fake, "
                      "prompt: 'TASK:each {{item.text}}'}}\n",
                    [("read", "each")],
                    inputs="  - {id: feeds, type: url, multiple: true}\n  - {id: days, type: text, default: '3650'}\n")

    def test_schema_takes_several_addresses_and_checks_each_default(self):
        self.assertTrue(schema.parse(self.FLOW).inputs["feeds"]["multiple"])
        ok = self.FLOW.replace("multiple: true}", "multiple: true, default: \"https://a.example/x\\n# off\\nhttps://b.example/y\"}")
        schema.parse(ok)
        with self.assertRaises(schema.WorkflowError):
            schema.parse(self.FLOW.replace("multiple: true}", "multiple: true, default: \"https://a.example/x\\nftp://b\"}"))
        with self.assertRaises(schema.WorkflowError):
            schema.parse(self.FLOW.replace("type: url, multiple: true", "type: text, multiple: true"))

    def test_each_address_is_read_and_one_that_fails_is_noted(self):
        engine = self.engine()
        feeds = "https://a.example/feed\n\n# a comment\nhttps://b.example/atom\nhttps://c.example/missing\n"
        with mock.patch.object(urlfetch, "fetch", fake_fetch):
            run_id = engine.start(self.FLOW, {"feeds": feeds})
            self.assertEqual(engine.wait(run_id, 30), "succeeded", engine.get(run_id)["error"])
        self.assertEqual(engine.get(run_id)["inputs"]["feeds"],
                         "https://a.example/feed\nhttps://b.example/atom\nhttps://c.example/missing")
        text = (engine.run_dir(run_id) / "nodes" / "read" / "text.md").read_text(encoding="utf-8")
        self.assertIn('<document name="https://a.example/feed" index="1">', text)
        self.assertIn("## Atom entry", text)
        self.assertIn("cannot read https://c.example/missing", text)
        self.assertEqual(len(self.calls()), 3)  # one model call per address

    def test_the_step_fails_when_no_address_can_be_read_and_bad_input_is_refused(self):
        engine = self.engine()
        with mock.patch.object(urlfetch, "fetch", fake_fetch):
            run_id = engine.start(self.FLOW, {"feeds": "https://x.example/1\nhttps://x.example/2"})
            self.assertEqual(engine.wait(run_id, 30), "failed")
        self.assertIn("2", engine.get(run_id)["nodes"]["read"]["error"])
        with self.assertRaises(RunError):
            engine.start(self.FLOW, {"feeds": "https://a.example/feed\nfile:///etc/passwd"})
        with self.assertRaises(RunError):
            engine.start(self.FLOW, {"feeds": "\n".join(f"https://a.example/{n}" for n in range(schema.MAX_URLS + 1))})

    def test_a_bad_number_of_days_fails_the_step(self):
        engine = self.engine()
        with mock.patch.object(urlfetch, "fetch", fake_fetch):
            run_id = engine.start(self.FLOW, {"feeds": "https://a.example/feed", "days": "a week"})
            self.assertEqual(engine.wait(run_id, 30), "failed")
        self.assertIn("a week", engine.get(run_id)["nodes"]["read"]["error"])


class ConditionPassTests(HomeCase):
    def test_the_taken_branch_gets_the_text_named_in_pass(self):
        flow = workflow(ai("doc", "TASK:doc Write.")
                        + "  - {id: gate, type: condition, config: {value: '{{inputs.pdf}}', operator: equals, match: 'yes', "
                          "pass: '{{nodes.doc.text}}'}}\n"
                        + "  - {id: out, type: document.export, config: {source: '{{nodes.gate.true}}', formats: [md]}}\n",
                        [("doc", "gate"), ("gate.true", "out")],
                        inputs="  - {id: pdf, type: choice, options: ['no', 'yes'], default: 'no'}\n")
        engine = self.engine()
        run_id = engine.start(flow, {"pdf": "yes"})
        self.assertEqual(engine.wait(run_id, 30), "succeeded", engine.get(run_id)["error"])
        exported = engine.run_dir(run_id) / engine.get(run_id)["nodes"]["out"]["outputs"]["md"]
        self.assertEqual(exported.read_text(encoding="utf-8"),
                         (engine.run_dir(run_id) / "nodes" / "doc" / "text.md").read_text(encoding="utf-8"))
        run_id = engine.start(flow, {"pdf": "no"})
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        self.assertEqual(engine.get(run_id)["nodes"]["out"]["status"], "skipped")


class LinkTests(unittest.TestCase):
    MD = "# T\n\n- [Source](https://example.com/a?x=1&y=2) and <https://example.com/b>\n\n`[code](https://example.com/c)`\n"

    def test_html_export_has_real_links_outside_code(self):
        page = tables.to_html(self.MD, "T", "en")
        self.assertIn('<a href="https://example.com/a?x=1&amp;y=2">Source</a>', page)
        self.assertIn('<a href="https://example.com/b">https://example.com/b</a>', page)
        self.assertNotIn('href="https://example.com/c"', page)
        self.assertNotIn("<a ", tables.to_html("[x](javascript:alert(1))", "T", "en"))

    def test_word_export_writes_the_address_after_the_text(self):
        with zipfile.ZipFile(io.BytesIO(tables.to_docx(self.MD, "T", "en"))) as z:
            document = z.read("word/document.xml").decode("utf-8")
        self.assertIn("Source (https://example.com/a?x=1&amp;y=2)", document)


if __name__ == "__main__":
    unittest.main()
