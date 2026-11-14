"""The web interface never shows a raw text key, and a server older than the code on disk says so."""

import json
import re
import sys
import threading
import unittest
from unittest import mock
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase  # noqa: E402

from mehteran import i18n, i18n_tools, languages, paths, schema, web  # noqa: E402
from mehteran.i18n import UI  # noqa: E402

UI_DIR = paths.CODE / "ui"


def used_keys() -> set[str]:
    """Every text key the page uses: data-i18n* attributes, and S("key") / ternaries / with_* maps in the scripts."""
    keys = set(re.findall(r'data-i18n(?:-placeholder|-label)?="([a-z_0-9]+)"', (UI_DIR / "index.html").read_text(encoding="utf-8")))
    for name in ("app.js", "editor.js", "canvas.js", "live.js", "langpicker.js"):
        js = (UI_DIR / name).read_text(encoding="utf-8")
        keys |= set(re.findall(r'\bS\(\s*"([a-z_0-9]+)"', js))
        keys |= {k for pair in re.findall(r'\bS\([^()]*?\?\s*"([a-z_0-9]+)"\s*:\s*"([a-z_0-9]+)"', js) for k in pair}
        keys |= set(re.findall(r'"(with_[a-z]+)"', js))
    return {k for k in keys if not k.endswith("_")}  # "status_" + s: a family, checked below


class UiStringTests(unittest.TestCase):
    def test_every_used_key_exists_in_both_languages(self):
        keys = used_keys()
        self.assertGreater(len(keys), 200)
        missing = sorted(k for k in keys if k not in UI)
        self.assertEqual(missing, [])
        empty = sorted(k for k in keys if not (UI[k].get("tr", "").strip() and UI[k].get("en", "").strip()))
        self.assertEqual(empty, [])

    def test_key_families_are_complete(self):
        family = [f"status_{s}" for s in ("queued", "pending", "running", "waiting_approval", "succeeded", "failed",
                                          "rejected", "skipped", "cancelled", "interrupted")]
        family += [f"input_type_{t}" for t in schema.INPUT_TYPES]
        family += [f"effort_{e}" for e in ("low", "medium", "high", "xhigh", "max")]
        family += [f"port_{p}" for p in ("text", "comment", "md", "docx", "html", "pdf", "epub")]  # the names of the output ports
        from mehteran import ocr
        family += [f"ocr_lang_{code}" for code in ocr.LANGUAGES]  # the Setup tab's OCR language list
        from mehteran.nodes import REGISTRY
        family += ["node_simple_" + name.replace(".", "_") for name in REGISTRY]  # the simple node panel's sentence
        family += [f"category_{c}" for c in {schema.parse(p.read_text(encoding="utf-8")).data.get("category")
                                             for p in paths.BUILTIN_TEMPLATES.glob("*.yaml")}]
        self.assertEqual([k for k in family if k not in UI or not all(UI[k].values())], [])


class LocaleTests(unittest.TestCase):
    """The texts are in mehteran/locales/<code>.json (and pipeline/ui/locales/ for the book translation's interface).
    Turkish and English are complete; another language may be partial, with the placeholders of the English text."""

    def test_turkish_and_english_are_complete_and_every_language_is_valid(self):
        for lang in languages.UI_CODES:
            self.assertEqual(i18n_tools.problems(lang), [], lang)
        for lang in ("tr", "en"):
            self.assertEqual({group: len(keys) for group, keys in i18n_tools.missing(lang).items()},
                             {"ui": 0, "messages": 0, "translation": 0}, lang)

    def test_a_wrong_placeholder_or_an_unknown_key_is_reported(self):
        english = dict(i18n.UI["new_run_title"])
        with mock.patch.dict(i18n.UI, {"new_run_title": {**english, "de": "Lauf: {nome}"}, "no_such_key": {"de": "x"}}):
            found = i18n_tools.problems("de")
        self.assertEqual(len(found), 2)
        self.assertIn("placeholders ['nome']", found[0])
        self.assertIn("no such key in English", found[1])
        self.assertEqual(i18n_tools.placeholders("{a} and {{literal}} and {b_2}"), {"a", "b_2"})

    def test_a_missing_text_falls_back_to_english(self):
        i18n.set_request("de")
        self.addCleanup(i18n.set_request, None)
        self.assertEqual(i18n.t("status_running"), "läuft")
        # A key no locale file has (the catalogs merge languages, so patching a real key would keep its German text).
        with mock.patch.dict(i18n.MESSAGES, {"test_only_text": {"tr": "İzin yok.", "en": "Not allowed."}}):
            self.assertEqual(i18n.t("test_only_text"), "Not allowed.")  # no German text: the English one
        self.assertEqual(i18n.localized({"tr": "Rapor dili", "en": "Report language"}), "Report language")
        self.assertEqual(i18n.pipeline_lang(), "en")  # the translation app's messages are Turkish or English
        self.assertEqual(i18n.ui_strings("de")["approve"], {"de": "Genehmigen", "en": "Approve"})
        self.assertEqual(i18n.ui_strings("tr")["approve"], {"tr": "Onayla", "en": "Approve"})

    def test_a_text_block_in_i18n_py_keeps_the_other_languages(self):
        catalog = i18n.Catalog({"hello": {"en": "Hello", "de": "Hallo"}})
        catalog.update({"hello": {"tr": "Merhaba", "en": "Hello!"}, "new": {"tr": "Yeni", "en": "New"}})
        self.assertEqual(catalog["hello"], {"en": "Hello!", "de": "Hallo", "tr": "Merhaba"})
        self.assertEqual(catalog["new"], {"tr": "Yeni", "en": "New"})

    def test_the_registry_has_every_language_of_the_translation_app_and_a_flag_for_each(self):
        import tomllib
        with open(paths.REPO / "config.default.toml", "rb") as f:
            configured = tomllib.load(f)["languages"]
        self.assertEqual(sorted(set(configured) - set(languages.CODES)), [])
        for item in languages.LANGUAGES:
            self.assertEqual(set(item) - {"ui"}, {"code", "native", "english", "flag", "dir"}, item)
            self.assertIn(item["dir"], ("ltr", "rtl"))
            self.assertTrue((UI_DIR / "flags" / f"{item['flag']}.svg").is_file(), item["flag"])
        self.assertTrue((UI_DIR / "flags" / "LICENSE").is_file())  # flag-icons, MIT
        self.assertEqual(languages.UI_CODES[:2], ("tr", "en"))
        self.assertEqual({c for c in languages.UI_CODES if languages.BY_CODE[c]["dir"] == "rtl"}, {"ar", "fa", "ur"})
        for code in languages.UI_CODES:
            self.assertTrue((i18n.LOCALES / f"{code}.json").is_file(), code)


class StaleServerTests(HomeCase):
    def setUp(self):
        super().setUp()
        self.app = web.App(self.engine())
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        self.port = self.server.server_address[1]
        self.server.RequestHandlerClass = web.make_handler(self.app, self.port)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def get(self, path, host=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}")
        if host:
            req.add_header("Host", host)
        try:
            with urllib.request.urlopen(req, timeout=10) as res:
                return res.status, res.read(), res.headers
        except urllib.error.HTTPError as e:
            with e:
                return e.code, e.read(), e.headers

    def test_version_needs_no_key_but_the_right_host(self):
        status, body, headers = self.get("/api/version")
        data = json.loads(body)
        self.assertEqual((status, data["app"], data["stale"]), (200, "Mehteran", False))
        self.assertEqual(set(data), {"app", "version", "stamp", "stale"})  # nothing else without the key
        self.assertTrue(headers["Server"].startswith("Mehteran"))
        self.assertEqual(self.get("/api/version", host="evil.test:80")[0], 403)
        self.assertEqual(self.get("/api/info")[0], 403)  # every other route still needs the key

    def test_a_changed_file_makes_the_server_stale(self):
        self.assertFalse(web.running_stale(self.port))
        # The code on disk differs from the code that the server started with (the files themselves are not
        # touched: a Mehteran that the user has open would show its "updated" notice).
        with mock.patch.object(web, "code_stamp", return_value="another-stamp"):
            self.assertTrue(json.loads(self.get("/api/version")[1])["stale"])
            self.assertTrue(web.running_stale(self.port))
        self.assertFalse(json.loads(self.get("/api/version")[1])["stale"])

    def test_icon_is_served_as_svg(self):
        status, body, headers = self.get("/icon.svg")
        if (paths.CODE / "ui" / "icon.svg").is_file():
            self.assertEqual(status, 200)
            self.assertTrue(headers["Content-Type"].startswith("image/svg+xml"))
            self.assertIn("img-src 'self'", headers["Content-Security-Policy"])
        else:
            self.assertEqual(status, 404)  # not there yet: a clean 404, not a server error

    def test_flags_and_the_translation_texts_are_served(self):
        status, body, headers = self.get("/flags/tr.svg")
        self.assertEqual((status, headers["Content-Type"]), (200, "image/svg+xml"))
        self.assertEqual(self.get("/flags/es-ct.svg")[0], 200)
        self.assertEqual(self.get("/flags/zz.svg")[0], 404)
        self.assertEqual(self.get("/flags/..%2Fapp.js")[0], 404)
        self.assertEqual(self.get("/flags/LICENSE")[0], 404)
        status, body, headers = self.get("/tr/locales/de.json")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["tab_books"], "Bücher")
        self.assertEqual(self.get("/tr/locales/tr.json")[0], 404)  # Turkish and English are in the interface's own file
        self.assertEqual(self.get("/langpicker.js")[0], 200)

    def test_busy_port_is_not_mehteran(self):
        self.assertIsNone(web.running_stale(1))  # nothing listens there


if __name__ == "__main__":
    unittest.main()
