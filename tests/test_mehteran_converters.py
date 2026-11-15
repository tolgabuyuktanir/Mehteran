"""Mehteran's added local tools: Typst (PDF export), Pandoc (EPUB, Word with equations, .odt/.rtf input), whisper.cpp
with ffmpeg (speech to text), qpdf (repairing PDFs), the added OCR languages and recommended models. Fake programs, a
temporary MEHTERAN_HOME and MEHTERAN_RUNTIME_ROOT: no network, the real .runtime folder is never touched."""

import io
import json
import os
import sys
import tarfile
import threading
import time
import unittest
import urllib.error
import urllib.request
import zipfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, workflow  # noqa: E402
from test_mehteran_local import LocalCase, tool_script  # noqa: E402

from mehteran import localtools, nodes, ocr, ollama, pandoc, qpdf, schema, speech, typst  # noqa: E402
from mehteran.web import App, make_handler  # noqa: E402

POSIX = os.name == "posix"
SAMPLE = """# Rapor: Öğrenci başarısı

Bu **kalın** ve *italik*; `kod #x` ve [bağlantı](https://example.org) ile [kötü](javascript:alert(1)).[^1]

[^1]: Dipnot *metni*.

| Ad | Not |
|---|--:|
| Ayşe | 95 |
| محمد | 80 |

- bir
  - alt #madde $x$ @ref <etiket>
- iki

3. üç
4. dört

> Alıntı "tırnak" \\ ters bölü

بسم الله الرحمن الرحيم هذا نص عربي

```python
print("#[x]")
```

---

Son // yorum değil /* bu da */
"""


class TypstSourceTests(unittest.TestCase):
    def setUp(self):
        self.source = typst.to_typst(SAMPLE, 'Başlık "x"', "tr")

    def test_text_is_never_markup(self):
        s = self.source
        self.assertIn('#set document(title: "Başlık \\"x\\"")', s)
        self.assertIn('lang: "tr"', s)
        self.assertIn('#heading(level: 1)[#"Rapor: Öğrenci başarısı"]', s)
        self.assertIn('#strong[#"kalın"]', s)
        self.assertIn('#emph[#"italik"]', s)
        self.assertIn('#raw("kod #x")', s)
        self.assertIn('#"alt #madde $x$ @ref <etiket>"', s)
        self.assertIn('#"Son // yorum değil /* bu da */"', s)
        self.assertIn('#"Alıntı \\"tırnak\\" \\\\ ters bölü"', s)
        # Outside string literals, only the converter's own code: no "//", "$", "@" or "<" from the text.
        outside = __import__("re").sub(r'"(?:[^"\\]|\\.)*"', '""', s)
        for bad in ("//", "$", "@", "<", "/*"):
            self.assertNotIn(bad, outside)

    def test_structure(self):
        s = self.source
        self.assertIn('#link("https://example.org")[#"bağlantı"]', s)
        self.assertNotIn("javascript", s.replace('#"kötü"', ""))  # an unsafe link keeps only its text
        self.assertIn('#footnote[#"Dipnot "#emph[#"metni"]#"."]', s)
        self.assertIn("#table(columns: 2, align: (start, end,),", s)
        self.assertIn('table.header([#"Ad"], [#"Not"])', s)
        self.assertIn('[#"محمد"], [#"80"]', s)
        self.assertIn('- #"bir"\n  - #"alt', s)
        self.assertIn('3. #"üç"\n4. #"dört"', s)
        self.assertIn("#quote(block: true)[", s)
        self.assertIn('#block(width: 100%)[#set text(dir: rtl, lang: "ar")', s)
        self.assertIn('#raw("print(\\"#[x]\\")", block: true, lang: "python")', s)
        self.assertIn("#line(length: 100%", s)

    def test_language_and_direction(self):
        s = typst.to_typst("مرحبا بالعالم", "t", "ar")
        self.assertIn('lang: "ar"', s)
        self.assertNotIn("dir: rtl", s)  # an Arabic document: the whole text is right to left already
        self.assertIn('lang: "pt", region: "BR"', typst.to_typst("x", "t", "pt-BR"))
        self.assertEqual(typst.string('a"b\\c\nd\x00'), '"a\\"b\\\\c\\nd"')


class ToolCase(LocalCase):
    """Fake programs in Mehteran's own .runtime folders."""

    def setUp(self):
        super().setUp()
        self.runtime = self.runtime_root / ".runtime"

    def tool(self, *names: str) -> None:
        places = {"typst": self.runtime / "typst", "pandoc": self.runtime / "pandoc" / "bin",
                  "whisper-cli": self.runtime / "speech" / "bin", "ffmpeg": self.runtime / "speech" / "bin",
                  "qpdf": self.runtime / "qpdf" / "bin", "pdftotext": self.runtime / "poppler" / "bin"}
        for name in names:
            tool_script(places[name], name, "mehteran_fake_tools.py", name)

    def run_flow(self, text: str, files: dict | None = None) -> tuple[dict, Path]:
        engine = self.engine()
        run_id = engine.start(text, files=files or {})
        engine.wait(run_id, 30)
        return engine.get(run_id), engine.run_dir(run_id)

    EXPORT = workflow("  - {id: out, type: document.export, config: {source: SOURCE, lang: tr, formats: FORMATS CONFIG}}\n", [])

    def export(self, source: str, formats: str, config: str = "") -> tuple[dict, Path]:
        text = self.EXPORT.replace("SOURCE", json.dumps(source)).replace("FORMATS", formats).replace("CONFIG", config)
        run, run_dir = self.run_flow(text)
        return run["nodes"]["out"], run_dir


@unittest.skipUnless(POSIX, "the fake programs are shell scripts")
class ExportTests(ToolCase):
    def test_pdf_with_typst(self):
        self.tool("typst")
        (self.runtime / "typst" / "fonts").mkdir(parents=True)
        node, run_dir = self.export("# Başlık\n\nMetin ve عربي.", "[md, pdf]")
        self.assertEqual(node["status"], "succeeded", node["error"])
        pdf = (run_dir / node["outputs"]["pdf"]).read_text(encoding="utf-8")
        self.assertTrue(pdf.startswith("%PDF-fake fonts=" + str(self.runtime / "typst" / "fonts")))
        self.assertIn('#heading(level: 1)[#"Başlık"]', pdf)
        self.assertTrue((run_dir / node["outputs"]["md"]).is_file())

    def test_pdf_without_typst_says_what_to_install(self):
        with mock.patch.object(typst, "binary", return_value=(None, None)):
            node, run_dir = self.export("Text.", "[md, pdf]")
        self.assertEqual(node["status"], "failed")
        self.assertIn("Install Typst on the Setup tab", node["error"])
        self.assertEqual(list(run_dir.rglob("out.md")), [], "nothing is written before the check")

    def test_typst_failure_is_shown(self):
        self.tool("typst")
        node, _ = self.export("FAIL_TYPST", "[pdf]")
        self.assertEqual(node["status"], "failed")
        self.assertIn("fake failure", node["error"])

    def test_epub_and_word_with_pandoc(self):
        self.tool("pandoc")
        node, run_dir = self.export("Formula: $x^2$.", "[docx, epub]")
        self.assertEqual(node["status"], "succeeded", node["error"])
        self.assertTrue((run_dir / node["outputs"]["epub"]).read_text().startswith("FAKE-epub markdown+hard_line_breaks lang=tr title=out"))
        self.assertTrue((run_dir / node["outputs"]["docx"]).read_text().startswith("FAKE-docx"), "math: Pandoc's Word file")
        node, run_dir = self.export("No formula, $5 only.", "[docx]")
        self.assertEqual((run_dir / node["outputs"]["docx"]).read_bytes()[:2], b"PK", "no math: Mehteran's own Word file")
        node, run_dir = self.export("No formula.", "[docx]", ", converter: pandoc")
        self.assertTrue((run_dir / node["outputs"]["docx"]).read_text().startswith("FAKE-docx"))
        node, run_dir = self.export("$x$", "[docx]", ", converter: builtin")
        self.assertEqual((run_dir / node["outputs"]["docx"]).read_bytes()[:2], b"PK")

    def test_without_pandoc_word_stays_and_epub_fails(self):
        with mock.patch.object(pandoc, "binary", return_value=(None, None)):
            node, run_dir = self.export("Formula: $x^2$.", "[docx]")
            self.assertEqual(node["status"], "succeeded", node["error"])
            self.assertEqual((run_dir / node["outputs"]["docx"]).read_bytes()[:2], b"PK")
            node, _ = self.export("Text.", "[epub]")
            self.assertEqual(node["status"], "failed")
            self.assertIn("Install Pandoc on the Setup tab", node["error"])

    def test_math_detection(self):
        for text in ("$x^2$", "Euler: $e^{i\\pi} + 1 = 0$.", "$$\n\\int_0^1 x\\,dx\n$$"):
            self.assertTrue(pandoc.has_math(text), text)
        for text in ("It costs $5 and $10.", "No math", "A $ sign", "\\$x\\$"):
            self.assertFalse(pandoc.has_math(text), text)

    def test_checks(self):
        schema.parse(self.EXPORT.replace("SOURCE", "x").replace("FORMATS", "[md, docx, html, pdf, epub]").replace("CONFIG", ", converter: auto"))
        with self.assertRaises(schema.WorkflowError) as e:
            schema.parse(self.EXPORT.replace("SOURCE", "x").replace("FORMATS", "[odt]").replace("CONFIG", ", converter: word"))
        messages = " ".join(e.exception.messages())
        self.assertIn("converter: must be one of", messages)
        self.assertIn("pdf, epub", messages)
        self.assertEqual(nodes.REGISTRY["document.export"].outputs({"formats": ["pdf", "epub"]}), {"pdf": "file", "epub": "file"})


@unittest.skipUnless(POSIX, "the fake programs are shell scripts")
class ExtractTests(ToolCase):
    FLOW = workflow("  - {id: extract, type: document.extract, config: {file: \"{{inputs.doc}}\"CONFIG}}\n", [],
                    inputs="  - {id: doc, type: file}\n")

    def extract(self, name: str, content: str, config: str = "") -> tuple[str, dict]:
        run, run_dir = self.run_flow(self.FLOW.replace("CONFIG", config), files={"doc": self.doc(name, content)})
        info = run["nodes"]["extract"]
        text = (run_dir / info["outputs"]["text"]).read_text(encoding="utf-8") if info["status"] == "succeeded" else ""
        return text, info

    def models(self, *names: str) -> None:
        small = {name: ("0" * 64, 10 + n) for n, name in enumerate(speech.MODELS)}
        patcher = mock.patch.dict(speech.MODELS, small)
        patcher.start()
        self.addCleanup(patcher.stop)
        folder = self.runtime / "whisper-models"
        folder.mkdir(parents=True, exist_ok=True)
        for name in names:
            (folder / f"ggml-{name}.bin").write_bytes(b"x" * speech.MODELS[name][1])

    def test_audio_and_video_are_transcribed(self):
        self.tool("whisper-cli", "ffmpeg")
        self.models("small", "tiny")
        text, info = self.extract("talk.mp3", "Merhaba dünya")
        self.assertEqual(info["status"], "succeeded", info["error"])
        self.assertEqual(text.strip(), "[auto|ggml-small.bin] Merhaba dünya", "auto: the first installed model in order")
        text, _ = self.extract("talk.mp4", "Hello", ", speech_model: tiny, speech_language: en")
        self.assertEqual(text.strip(), "[en|ggml-tiny.bin] Hello")
        _, info = self.extract("talk.wav", "x", ", speech_model: medium")
        self.assertIn("'medium' is not installed", info["error"])

    def test_speech_without_tools_or_models(self):
        with mock.patch.object(speech, "whisper", return_value=(None, None)):
            _, info = self.extract("talk.m4a", "x")
        self.assertIn("install speech to text (whisper.cpp) on the Setup tab", info["error"])
        self.tool("whisper-cli", "ffmpeg")
        self.models()
        _, info = self.extract("talk.ogg", "x")
        self.assertIn("No speech model", info["error"])

    def test_cancel_during_transcription(self):
        self.tool("whisper-cli", "ffmpeg")
        self.models("base")
        engine = self.engine()
        run_id = engine.start(self.FLOW.replace("CONFIG", ""), files={"doc": self.doc("long.wav", "SLOW")})
        self.wait_for(lambda: engine.get(run_id)["nodes"]["extract"]["status"] == "running")
        time.sleep(0.5)
        started = time.time()
        engine.cancel(run_id)
        self.assertEqual(engine.wait(run_id, 15), "cancelled")
        self.assertLess(time.time() - started, 8)

    def test_odt_and_rtf_through_pandoc(self):
        self.tool("pandoc")
        text, info = self.extract("letter.odt", "Sayın okur,")
        self.assertEqual(info["status"], "succeeded", info["error"])
        self.assertEqual(text, "# From pandoc\n\nSayın okur,")
        with mock.patch.object(pandoc, "binary", return_value=(None, None)):
            _, info = self.extract("letter.rtf", "x")
        self.assertIn("Install Pandoc on the Setup tab", info["error"])

    def test_a_damaged_pdf_is_read_after_qpdf_repairs_it(self):
        self.tool("pdftotext")
        tool_script(self.runtime / "tesseract" / "bin", "tesseract", "mehteran_fake_ocr.py", "tesseract")
        tool_script(self.runtime / "poppler" / "bin", "pdftoppm", "mehteran_fake_ocr.py", "pdftoppm")
        content = "BROKEN first page with a real text layer.\f\f"
        with mock.patch.object(qpdf, "binary", return_value=(None, None)):
            _, info = self.extract("damaged.pdf", content)
        self.assertEqual(info["status"], "failed")
        self.assertIn("trailer", info["error"])
        self.tool("qpdf")
        text, info = self.extract("damaged.pdf", content)
        self.assertEqual(info["status"], "succeeded", info["error"])
        self.assertIn("FIXED first page with a real text layer.", text)
        self.assertIn("OCR(tur+eng) scan of page 2", text)

    def test_checks(self):
        schema.parse(self.FLOW.replace("CONFIG", ", speech_model: base, speech_language: tr")
                     .replace("type: file}", "type: file, formats: [mp3, wav, mp4, webm, odt, rtf]}"))
        with self.assertRaises(schema.WorkflowError) as e:
            schema.parse(self.FLOW.replace("CONFIG", ", speech_model: huge, speech_language: klingon"))
        messages = " ".join(e.exception.messages())
        self.assertIn("speech_model: must be one of", messages)
        self.assertIn("speech_language: must be one of", messages)
        field = nodes.REGISTRY["document.extract"].config
        self.assertEqual([v for v, _ in field["speech_language"].options], list(speech.LANGUAGES))
        self.assertEqual({v for v, _ in field["speech_model"].options} - {"auto"}, set(speech.MODELS))
        self.assertTrue(set(speech.FORMATS) | set(pandoc.READS) <= set(schema.FILE_FORMATS))


def tar_xz(path: Path, files: dict) -> None:
    with tarfile.open(path, "w:xz") as tar:
        for name, data in files.items():
            info = tarfile.TarInfo(name)
            info.size, info.mode = len(data), 0o755
            tar.addfile(info, io.BytesIO(data))


def zip_of(path: Path, files: dict) -> None:
    with zipfile.ZipFile(path, "w") as z:
        for name, data in files.items():
            z.writestr(name, data)


class InstallTests(LocalCase):
    def test_pinned_sums(self):
        for table in (typst.ASSETS, pandoc.ASSETS):
            for name, sha, size in table.values():
                self.assertRegex(sha, r"\A[0-9a-f]{64}\Z")
                self.assertGreater(size, 1_000_000)
        for sha, size in list(speech.MODELS.values()) + list(ocr.LANGUAGES.values()):
            self.assertRegex(sha, r"\A[0-9a-f]{64}\Z")
        self.assertIn("/5359861c739e955e79d9a303bcbc70fb988958b1/", speech.MODEL_URL)

    def test_typst_install_unpacks_the_release_and_the_font(self):
        seen = []

        def fake_verified(url, dest, sha256):
            seen.append((url, sha256))
            if url.endswith(".tar.xz"):
                tar_xz(Path(dest), {"typst-aarch64-apple-darwin/typst": b"#!/bin/sh\necho typst 0.15.1\n",
                                    "typst-aarch64-apple-darwin/LICENSE": b"Apache"})
            else:
                zip_of(Path(dest), {"Amiri-1.003/Amiri-Regular.ttf": b"font", "Amiri-1.003/OFL.txt": b"OFL"})
        with mock.patch.object(localtools, "platform_key", return_value=("darwin", "arm64")), \
                mock.patch.object(typst, "platform_key", return_value=("darwin", "arm64")), \
                mock.patch.object(localtools, "download_verified", fake_verified), mock.patch("sys.stdout", io.StringIO()):
            program = typst.install()
        self.assertEqual(program, self.runtime_root / ".runtime" / "typst" / "typst")
        self.assertEqual(seen[0], (f"{typst.RELEASE}/typst-aarch64-apple-darwin.tar.xz", typst.ASSETS[("darwin", "arm64")][1]))
        self.assertEqual(seen[1], (typst.FONT_URL, typst.FONT_SHA256))
        self.assertTrue((typst.fonts_dir() / "Amiri-Regular.ttf").is_file())
        status = typst.status()
        self.assertEqual((status["installed"], status["source"], status["arabic_font"]), (True, "mehteran", True))

    def test_pandoc_install(self):
        def fake_verified(url, dest, sha256):
            zip_of(Path(dest), {"pandoc-3.14-arm64/bin/pandoc": b"#!/bin/sh\necho pandoc 3.14\n"})
        with mock.patch.object(pandoc, "platform_key", return_value=("darwin", "arm64")), \
                mock.patch.object(localtools, "download_verified", fake_verified), mock.patch("sys.stdout", io.StringIO()):
            program = pandoc.install()
        self.assertEqual(program, self.runtime_root / ".runtime" / "pandoc" / "bin" / "pandoc")
        self.assertTrue(os.access(program, os.X_OK))
        with mock.patch.object(pandoc, "platform_key", return_value=("windows", "arm64")):
            self.assertEqual(pandoc.asset(), pandoc.ASSETS[("windows", "x64")])
        with mock.patch.object(typst, "platform_key", return_value=("linux", "riscv64")):
            with self.assertRaises(localtools.ToolError):
                typst.asset()

    def test_speech_install_skips_ffmpeg_when_the_computer_has_one(self):
        specs = []

        def fake_conda(prefix, wanted):
            specs.append(wanted)
            tool_script(prefix / "bin", "whisper-cli", "mehteran_fake_tools.py", "whisper-cli")
        with mock.patch.object(speech, "conda_install", fake_conda), mock.patch.object(speech, "install_models") as models:
            with mock.patch.object(speech, "ffmpeg", return_value=(Path("/usr/bin/ffmpeg"), "system")):
                speech.install()
            with mock.patch.object(speech, "ffmpeg", return_value=(None, None)):
                speech.install(["tiny"])
        self.assertEqual(specs, [[speech.WHISPER_SPEC], [speech.WHISPER_SPEC, speech.FFMPEG_SPEC]])
        self.assertEqual(models.call_args_list[0].args[0], ["base"])
        self.assertEqual(models.call_args_list[1].args[0], ["tiny"])

    def test_speech_models_are_checked(self):
        with mock.patch.object(speech, "download_verified") as download, mock.patch("sys.stdout", io.StringIO()):
            speech.install_models(["tiny", "base"])
            self.assertEqual([c.args[0] for c in download.call_args_list],
                             [speech.MODEL_URL.format(name="tiny"), speech.MODEL_URL.format(name="base")])
            self.assertEqual(download.call_args_list[0].args[2], speech.MODELS["tiny"][0])
            download.reset_mock()
            with self.assertRaises(localtools.ToolError):
                speech.install_models(["tiny", "large-v9"])
            download.assert_not_called()

    def test_qpdf_install(self):
        def fake_conda(prefix, wanted):
            self.assertEqual(wanted, [qpdf.SPEC])
            tool_script(prefix / "bin", "qpdf", "mehteran_fake_tools.py", "qpdf")
        with mock.patch.object(qpdf, "conda_install", fake_conda), mock.patch("sys.stdout", io.StringIO()):
            qpdf.install()
        self.assertEqual(qpdf.status()["source"], "mehteran")

    def test_conda_install_uses_the_runtime_folder_only(self):
        runtime = self.runtime_root / ".runtime"
        micromamba = runtime / "micromamba" / localtools.exe("micromamba")
        micromamba.parent.mkdir(parents=True)
        micromamba.write_text("")
        calls = []

        def fake_run(argv, env, stdin):
            calls.append((argv, env))
            return mock.Mock(returncode=0)
        with mock.patch("subprocess.run", fake_run), mock.patch("sys.stdout", io.StringIO()):
            localtools.conda_install(runtime / "qpdf", ["qpdf=12.4.2"])
        create, env = calls[0]
        self.assertEqual(create[:2], [str(micromamba), "create"])
        self.assertEqual(create[-3:], ["conda-forge", "--override-channels", "qpdf=12.4.2"])
        self.assertEqual(env["CONDA_PKGS_DIRS"], str(runtime / "mamba" / "pkgs"))
        with mock.patch("subprocess.run", return_value=mock.Mock(returncode=1)), mock.patch("sys.stdout", io.StringIO()):
            with self.assertRaises(localtools.ToolError):
                localtools.conda_install(runtime / "qpdf", ["qpdf=12.4.2"])

    def test_ocr_offers_more_languages_but_installs_the_usual_ones(self):
        for code in ("deu", "fra", "spa", "rus", "urd", "chi_sim", "jpn", "ita", "por", "nld", "aze", "kmr"):
            self.assertIn(code, ocr.LANGUAGES)
            self.assertRegex(code, ocr.LANG_RE)
        self.assertEqual(ocr.DEFAULT_LANGUAGES, ["eng", "tur", "ara", "fas"])
        with mock.patch.object(ocr, "download_verified") as download, mock.patch("sys.stdout", io.StringIO()):
            ocr.install_languages(["chi_sim"])
        self.assertIn("tessdata_fast/4.1.0/chi_sim.traineddata", download.call_args.args[0])

    def test_recommended_vision_and_embedding_models(self):
        kinds = {m["name"]: m.get("kind") for m in ollama.RECOMMENDED}
        self.assertEqual(kinds["qwen2.5vl:7b"], "vision")
        self.assertEqual(kinds["bge-m3:567m"], "embedding")
        for name in kinds:
            self.assertTrue(ollama.MODEL_RE.match(name), name)


class ApiTests(LocalCase):
    def setUp(self):
        super().setUp()
        self.app = App(self.engine())
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), None)
        self.port = self.server.server_address[1]
        self.server.RequestHandlerClass = make_handler(self.app, self.port)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def json(self, method, path, body=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", method=method,
                                     data=json.dumps(body).encode() if body is not None else None)
        req.add_header("X-Token", self.app.token)
        req.add_header("X-Lang", "en")
        try:
            with urllib.request.urlopen(req, timeout=30) as res:
                return res.status, json.loads(res.read())
        except urllib.error.HTTPError as e:
            with e:
                return e.code, json.loads(e.read())

    def test_status_of_every_tool(self):
        status, data = self.json("GET", "/api/local-tools")
        self.assertEqual(status, 200)
        tools = {item["id"]: item for item in data["tools"]}
        self.assertEqual(list(tools), ["ollama", "ocr", "typst", "pandoc", "speech", "qpdf", "browser"])
        for tool_id in ("typst", "pandoc", "speech", "qpdf", "browser"):
            for key in ("installed", "source", "path", "version", "pinned_version", "size", "download_size", "install_dir",
                        "disk_free", "job"):
                self.assertIn(key, tools[tool_id], tool_id)
        self.assertEqual(tools["typst"]["pinned_version"], typst.VERSION)
        self.assertIn("arabic_font", tools["typst"])
        for key in ("ffmpeg", "models", "available_models", "models_job"):
            self.assertIn(key, tools["speech"])
        self.assertEqual([m["name"] for m in tools["speech"]["available_models"]], list(speech.MODELS))

    def test_install_jobs(self):
        self.assertEqual(self.json("POST", "/api/local-tools/speech-models/install", {"models": ["huge"]})[0], 400)
        self.assertEqual(self.json("POST", "/api/local-tools/latex/install", {})[0], 404)
        with mock.patch.object(self.app.jobs, "start") as start:
            for tool_id in ("typst", "pandoc", "speech", "qpdf"):
                self.assertEqual(self.json("POST", f"/api/local-tools/{tool_id}/install", {})[0], 200)
            self.assertEqual(self.json("POST", "/api/local-tools/speech-models/install", {"models": ["small", "tiny"]})[0], 200)
        calls = [(c.args[0], c.args[1][-3:]) for c in start.call_args_list]
        self.assertEqual([key for key, _ in calls], ["local:typst", "local:pandoc", "local:speech", "local:qpdf", "local:speech-models"])
        self.assertEqual(calls[0][1][-2:], ["install-local", "typst"])
        self.assertEqual(calls[4][1], ["speech-models", "small", "tiny"])
        self.assertEqual(self.json("POST", "/api/local-tools/speech/cancel", {}), (200, {"cancelled": False}))

    def test_editor_offers_the_new_formats(self):
        status, info = self.json("GET", "/api/info")
        self.assertEqual(status, 200)
        self.assertEqual(info["formats"], ["md", "docx", "html", "pdf", "epub", "eml", "json", "csv"])
        for fmt in ("odt", "rtf", "mp3", "mp4", "webm"):
            self.assertIn(fmt, info["file_formats"])


class CliTests(HomeCase):
    def test_install_local_targets(self):
        from mehteran import cli
        quiet = mock.patch("pipeline.i18n.set_default")  # the process-wide language of the translation app stays
        quiet.start()
        self.addCleanup(quiet.stop)
        with mock.patch.object(speech, "install_models") as models, mock.patch.object(typst, "install") as install_typst:
            self.assertEqual(cli.main(["install-local", "speech-models", "tiny"]), 0)
            self.assertEqual(cli.main(["install-local", "typst"]), 0)
        models.assert_called_once_with(["tiny"])
        install_typst.assert_called_once_with()
        with mock.patch.object(ocr, "install_languages") as languages:
            cli.main(["install-local", "ocr-languages"])
        languages.assert_called_once_with(ocr.DEFAULT_LANGUAGES)


if __name__ == "__main__":
    unittest.main()
