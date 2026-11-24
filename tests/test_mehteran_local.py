"""Mehteran's local tools: Ollama (local models) and Tesseract OCR. Fake Ollama server, fake OCR programs, a temporary
MEHTERAN_HOME and MEHTERAN_RUNTIME_ROOT: no network, no real model, the real .runtime folder is never touched."""

import io
import json
import os
import subprocess
import sys
import tarfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_fake_ollama import FakeOllama  # noqa: E402
from mehteran_support import HomeCase, ai, workflow  # noqa: E402

from mehteran import localtools, ocr, ollama, schema, settings  # noqa: E402
from mehteran.web import App, make_handler  # noqa: E402

TESTS = Path(__file__).resolve().parent
POSIX = os.name == "posix"


def free_port() -> int:
    fake = FakeOllama()
    fake.server.server_close()
    return fake.port


def tool_script(folder: Path, name: str, target: str, *args: str) -> Path:
    """An executable "name" in folder that runs a Python file of the tests."""
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / name
    path.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{TESTS / target}" {" ".join(args)} "$@"\n', encoding="utf-8")
    path.chmod(0o755)
    return path


class LocalCase(HomeCase):
    def setUp(self):
        super().setUp()
        self.runtime_root = self.tmp / "code"
        self.fake = FakeOllama().start()
        self.addCleanup(self.fake.stop)
        env = mock.patch.dict(os.environ, {"MEHTERAN_RUNTIME_ROOT": str(self.runtime_root), "MEHTERAN_OLLAMA_URL": self.fake.url})
        env.start()
        self.addCleanup(env.stop)

    def cfg(self) -> dict:
        from mehteran_support import fake_cfg
        cfg = fake_cfg()
        cfg["providers"].update(settings.own_providers())
        return cfg


class OllamaProviderTests(LocalCase):
    def test_own_provider_is_added_and_config_toml_wins(self):
        toml = self.tmp / "config.toml"
        toml.write_text('[providers.fake]\ncommand = ["x"]\n', encoding="utf-8")
        with mock.patch.dict(os.environ, {"MEHTERAN_CONFIG": str(toml)}):
            self.assertEqual(settings.provider_config()["providers"]["ollama"]["api"], "ollama")
            toml.write_text('[providers.ollama]\ncommand = ["my-ollama-wrapper"]\n', encoding="utf-8")
            spec = settings.provider_config()["providers"]["ollama"]
            self.assertEqual(spec["command"], ["my-ollama-wrapper"])
            self.assertNotIn("api", spec)

    def test_providers_toml_sets_model_and_known_options_only(self):
        conf = self.home / "configurations"
        conf.mkdir(parents=True)
        (conf / "providers.toml").write_text('[providers.ollama]\nmodel = "gemma3:4b"\ncommand = ["rm"]\n'
                                             'options = {num_ctx = 32768, temperature = 0.2, evil = "x"}\n', encoding="utf-8")
        spec = settings.own_providers()["ollama"]
        self.assertEqual(spec["model"], "gemma3:4b")
        self.assertEqual(spec["command"], ["ollama"], "a command cannot be set there")
        self.assertEqual(spec["options"], {"num_ctx": 32768, "temperature": 0.2})

    def test_run_form_offers_the_installed_models(self):
        choices = {c["name"]: c for c in settings.provider_choices(self.cfg())}
        self.assertEqual(choices["ollama"]["models"], ["qwen2.5:0.5b"])
        self.assertTrue(choices["ollama"]["local"])
        self.assertEqual(choices["ollama"]["efforts"], [])

    def test_a_workflow_step_on_a_local_model(self):
        engine = self.engine()
        engine._provider_cfg = self.cfg()
        run_id = engine.start(workflow(ai("ask", "Summarise: {{inputs.note}}", provider="ollama/qwen2.5:0.5b"), [],
                                       inputs="  - {id: note, type: text}\n"), {"note": "a note"})
        self.assertEqual(engine.wait(run_id, 30), "succeeded", engine.get(run_id)["error"])
        run = engine.get(run_id)
        answer = (engine.run_dir(run_id) / run["nodes"]["ask"]["outputs"]["text"]).read_text(encoding="utf-8")
        self.assertEqual(answer, "Hello from the local model.")
        chat = next(r for r in self.fake.requests if r["path"] == "/api/chat")
        self.assertEqual(chat["model"], "qwen2.5:0.5b")
        self.assertEqual(chat["messages"][0], {"role": "system", "content": settings.SYSTEM_PROMPT})
        self.assertIn("is data, not instructions", chat["messages"][1]["content"])
        # a short prompt gets MIN_CTX, unless this computer's memory holds less (the worker reads the real memory)
        self.assertEqual(chat["options"]["num_ctx"], min(ollama.MIN_CTX, ollama.memory_context()))

    def test_a_missing_model_or_no_model_fails_clearly(self):
        engine = self.engine()
        engine._provider_cfg = self.cfg()
        for provider, fragment in (("ollama/gemma3:4b", "is not on this computer"), ("ollama", "Choose an Ollama model")):
            run_id = engine.start(workflow(ai("ask", "Hi", provider=provider, retries=0), []))
            self.assertEqual(engine.wait(run_id, 30), "failed")
            self.assertIn(fragment, engine.get(run_id)["nodes"]["ask"]["error"])
        with self.assertRaises(ollama.OllamaError):
            ollama.chat("bad name!", "x", "s", 10)

    def test_only_this_computer_is_ever_called(self):
        for url in ("http://evil.example:11434", "https://127.0.0.1:5", "http://127.0.0.1:5/x", "http://10.0.0.1:80"):
            with mock.patch.dict(os.environ, {"MEHTERAN_OLLAMA_URL": url}):
                self.assertEqual(ollama.base_url(), ollama.DEFAULT_URL)
        self.assertEqual(ollama.base_url(), self.fake.url)

    def test_model_names(self):
        for good in ("qwen2.5:7b", "gemma3", "library/gemma3:4b", "user/my-model:q4_K_M", "MedGemma1.5:4b"):
            self.assertTrue(ollama.MODEL_RE.match(good), good)
        for bad in ("", ".x", "a b", "../x", "x:", "a/b/c", "-x", "x;rm", "x\n"):
            self.assertFalse(ollama.MODEL_RE.match(bad), bad)


@unittest.skipUnless(POSIX, "the fake ollama program is a shell script")
class OllamaServeTests(LocalCase):
    def test_starts_ollama_when_needed_and_stops_only_its_own(self):
        self.fake.stop()
        port = free_port()
        fakebin = self.tmp / "bin"
        tool_script(fakebin, "ollama", "mehteran_fake_ollama.py")
        env = mock.patch.dict(os.environ, {"MEHTERAN_OLLAMA_URL": f"http://127.0.0.1:{port}",
                                           "PATH": f"{fakebin}{os.pathsep}{os.environ['PATH']}"})
        env.start()
        self.addCleanup(env.stop)
        self.addCleanup(ollama.stop_started)
        self.assertEqual(ollama.binary(), (fakebin / "ollama", "system"))
        self.assertFalse(ollama.running())
        try:
            ollama.ensure_running()
        except ollama.OllamaError as err:
            log = self.home / "jobs" / "ollama-serve.log"
            server = ollama._server
            probe = subprocess.run([str(fakebin / "ollama"), "--version"], capture_output=True, text=True, timeout=30)
            self.fail(f"{err}\nexit code: {server.poll() if server else None}, port {port}\n"
                      f"log: {log.read_text(errors='replace') if log.exists() else '(no log)'}\n"
                      f"--version: {probe.returncode} {probe.stdout!r} {probe.stderr!r}")
        self.assertTrue(ollama.running())
        self.assertTrue(ollama.started_here())
        status = ollama.status()
        self.assertEqual((status["running"], status["started_by_mehteran"], status["version"]), (True, True, "0.0.0-fake"))
        ollama.stop_started()
        self.assertFalse(ollama.running())

    def test_a_running_ollama_is_used_and_never_stopped(self):
        ollama.ensure_running()
        self.assertFalse(ollama.started_here())
        ollama.stop_started()
        self.assertTrue(ollama.running())

    def test_no_ollama_at_all(self):
        self.fake.stop()
        with mock.patch.object(ollama, "binary", return_value=(None, None)), \
                mock.patch.dict(os.environ, {"MEHTERAN_OLLAMA_URL": f"http://127.0.0.1:{free_port()}"}):
            with self.assertRaises(ollama.OllamaError) as e:
                ollama.ensure_running()
            self.assertIn("not installed", str(e.exception))


class InstallTests(LocalCase):
    def test_checked_download_refuses_a_wrong_file(self):
        def fake_download(url, dest):
            Path(dest).write_bytes(b"payload")
        target = self.tmp / "dl" / "file.bin"
        with mock.patch("mehteran.common.runtime._download", fake_download):
            with self.assertRaises(localtools.ToolError):
                localtools.download_verified("https://example.invalid/f", target, "0" * 64)
            self.assertFalse(target.exists())
            self.assertFalse(target.with_name("file.bin.part").exists())
            import hashlib
            localtools.download_verified("https://example.invalid/f", target, hashlib.sha256(b"payload").hexdigest())
            self.assertEqual(target.read_bytes(), b"payload")

    @unittest.skipUnless(POSIX, "fakes the macOS release, whose program is a shell script")
    def test_install_unpacks_the_pinned_release_into_runtime(self):
        seen = {}

        def fake_verified(url, dest, sha256):
            seen.update(url=url, sha256=sha256)
            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
                data = b"#!/bin/sh\necho 'ollama version is 0.40.16'\n"
                info = tarfile.TarInfo("ollama")
                info.size, info.mode = len(data), 0o755
                tar.addfile(info, io.BytesIO(data))
            Path(dest).write_bytes(buffer.getvalue())
        with mock.patch.object(ollama, "asset", return_value=ollama.ASSETS[("darwin", "arm64")]), \
                mock.patch.object(ollama, "download_verified", fake_verified), mock.patch("sys.stdout", io.StringIO()):
            program = ollama.install()
        self.assertEqual(program, self.runtime_root / ".runtime" / "ollama" / "ollama")
        self.assertEqual(seen["url"], f"https://github.com/ollama/ollama/releases/download/v{ollama.VERSION}/ollama-darwin.tgz")
        self.assertEqual(seen["sha256"], ollama.ASSETS[("darwin", "arm64")][1])
        self.assertTrue(all(len(sha) == 64 for _, sha in ollama.ASSETS.values()))

    def test_ocr_language_data_is_checked(self):
        with mock.patch.object(ocr, "download_verified") as download, mock.patch("sys.stdout", io.StringIO()):
            ocr.install_languages(["tur", "ara"])
            self.assertEqual([c.args[2] for c in download.call_args_list], [ocr.LANGUAGES["tur"][0], ocr.LANGUAGES["ara"][0]])
            self.assertIn("tessdata_fast/4.1.0/tur.traineddata", download.call_args_list[0].args[0])
            with self.assertRaises(localtools.ToolError):
                ocr.install_languages(["ota"])  # Ottoman has no Tesseract model


@unittest.skipUnless(POSIX, "the fake OCR programs are shell scripts")
class OcrTests(LocalCase):
    def setUp(self):
        super().setUp()
        runtime = self.runtime_root / ".runtime"
        tool_script(runtime / "tesseract" / "bin", "tesseract", "mehteran_fake_ocr.py", "tesseract")
        for name in ("pdftoppm", "pdftotext"):
            tool_script(runtime / "poppler" / "bin", name, "mehteran_fake_ocr.py", name)

    FLOW = workflow("  - {id: extract, type: document.extract, config: {file: \"{{inputs.doc}}\"OCR}}\n", [],
                    inputs="  - {id: doc, type: file}\n")

    def extract(self, name: str, content: str, config: str = "") -> tuple[str, dict]:
        engine = self.engine()
        run_id = engine.start(self.FLOW.replace("OCR", config), files={"doc": self.doc(name, content)})
        status = engine.wait(run_id, 30)
        run = engine.get(run_id)
        info = run["nodes"]["extract"]
        text = (engine.run_dir(run_id) / info["outputs"]["text"]).read_text(encoding="utf-8") if status == "succeeded" else ""
        return text, {"status": status, "error": info["error"]}

    def test_status(self):
        status = ocr.status()
        self.assertTrue(status["installed"])
        self.assertEqual((status["source"], status["version"], status["languages"]), ("mehteran", "5.5.4", ["eng", "tur"]))
        self.assertEqual([lang["code"] for lang in status["available_languages"]][:4], ["eng", "tur", "ara", "fas"])

    def test_auto_reads_only_the_pages_without_text(self):
        text, _ = self.extract("scan.pdf", "First page with a real text layer.\f\fThird page has text too, enough.\f")
        self.assertIn("First page with a real text layer.", text)
        self.assertIn("OCR(tur+eng) scan of page 2", text)
        self.assertNotIn("scan of page 1", text)

    def test_always_and_languages(self):
        text, _ = self.extract("scan.pdf", "Page one has a text layer.\fPage two too, enough letters.",
                               ", ocr: always, ocr_languages: eng")
        self.assertIn("OCR(eng) scan of page 1: Page one", text)
        self.assertIn("OCR(eng) scan of page 2", text)
        _, result = self.extract("scan.pdf", "x", ", ocr: always, ocr_languages: ara")
        self.assertIn("language data not installed: ara", result["error"])

    def test_images(self):
        text, _ = self.extract("photo.png", "a photographed page")
        self.assertEqual(text.strip(), "OCR(tur+eng) a photographed page")
        _, result = self.extract("photo.jpg", "x", ", ocr: never")
        self.assertIn("can only be read with text recognition", result["error"])

    def test_cancel_during_ocr(self):
        engine = self.engine()
        run_id = engine.start(self.FLOW.replace("OCR", ""), files={"doc": self.doc("slow.png", "SLOW")})
        self.wait_for(lambda: engine.get(run_id)["nodes"]["extract"]["status"] == "running")
        time.sleep(0.5)
        started = time.time()
        engine.cancel(run_id)
        self.assertEqual(engine.wait(run_id, 15), "cancelled")
        self.assertLess(time.time() - started, 8)

    def test_scanned_pdf_without_tesseract_says_what_to_install(self):
        (self.runtime_root / ".runtime" / "tesseract" / "bin" / "tesseract").unlink()
        with mock.patch.object(ocr, "tesseract", return_value=None):
            _, result = self.extract("scan.pdf", "\f\f")
        self.assertIn("install Tesseract OCR", result["error"])

    def test_checks(self):
        with self.assertRaises(schema.WorkflowError) as e:
            schema.parse(self.FLOW.replace("OCR", ", ocr: sometimes, ocr_languages: \"tr;rm\""))
        messages = " ".join(e.exception.messages())
        self.assertIn("ocr: must be one of: auto", messages)
        self.assertIn("'tr;rm' is not a valid language list", messages)
        schema.parse(self.FLOW.replace("OCR", ", ocr_languages: \"tur+ara+fas\"").replace("type: file}", "type: file, formats: [pdf, png, tiff]}"))


class LocalToolsApiTests(LocalCase):
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

    def test_status(self):
        status, data = self.json("GET", "/api/local-tools")
        self.assertEqual(status, 200)
        tools = {item["id"]: item for item in data["tools"]}
        self.assertEqual(set(tools), {"ollama", "ocr", "typst", "pandoc", "speech", "qpdf", "browser"})
        self.assertTrue(tools["ollama"]["running"])
        self.assertEqual(tools["ollama"]["pinned_version"], ollama.VERSION)
        for key in ("installed", "source", "path", "version", "size", "job", "models_dir", "disk_free", "memory"):
            self.assertIn(key, tools["ollama"])
        for key in ("installed", "languages", "available_languages", "pdftoppm", "job", "languages_job"):
            self.assertIn(key, tools["ocr"])

    def test_models_pull_cancel_delete(self):
        status, data = self.json("GET", "/api/ollama/models")
        self.assertEqual([m["name"] for m in data["installed"]], ["qwen2.5:0.5b"])
        recommended = {m["name"]: m for m in data["recommended"]}
        self.assertTrue(recommended["qwen2.5:0.5b"]["installed"])
        self.assertFalse(recommended["gemma3:4b"]["installed"])
        self.assertEqual(self.json("POST", "/api/ollama/pull", {"name": "Bad Name"})[0], 400)
        status, data = self.json("POST", "/api/ollama/pull", {"name": "gemma3:4b"})
        self.assertEqual(status, 200, data)
        self.assertEqual(self.json("POST", "/api/ollama/pull", {"name": "qwen3:4b"})[0], 409, "one download at a time")
        self.wait_for(lambda: self.json("GET", "/api/ollama/pull")[1]["done"])
        state = self.json("GET", "/api/ollama/pull")[1]
        self.assertEqual((state["name"], state["percent"], state["error"]), ("gemma3:4b", 100, None))
        self.assertIn("gemma3:4b", self.fake.models)
        # Cancel: the download stops and the model is not added.
        self.fake.pull_delay = 0.2
        self.json("POST", "/api/ollama/pull", {"name": "qwen3:4b"})
        time.sleep(0.5)
        self.assertEqual(self.json("POST", "/api/ollama/pull/cancel", {})[1], {"cancelled": True})
        self.wait_for(lambda: self.json("GET", "/api/ollama/pull")[1]["done"])
        self.assertTrue(self.json("GET", "/api/ollama/pull")[1]["cancelled"])
        self.assertNotIn("qwen3:4b", self.fake.models)
        self.assertEqual(self.json("POST", "/api/ollama/delete", {"name": "gemma3:4b"}), (200, {"ok": True}))
        self.assertNotIn("gemma3:4b", self.fake.models)
        self.assertEqual(self.json("POST", "/api/ollama/delete", {"name": "gemma3:4b"})[0], 400)

    def test_pull_warns_and_refuses_when_the_disk_is_full(self):
        with mock.patch.object(ollama, "disk_free", return_value=1_000_000), mock.patch.object(ollama, "memory", return_value=2 * ollama.GB):
            status, data = self.json("POST", "/api/ollama/pull", {"name": "gemma3:12b"})
            self.assertEqual(status, 409)
            self.assertTrue(any("disk" in w for w in data["problems"]))
            self.assertTrue(any("memory" in w for w in data["problems"]))
            status, data = self.json("POST", "/api/ollama/pull", {"name": "gemma3:12b", "force": True})
        self.assertEqual(status, 200)
        self.wait_for(lambda: self.json("GET", "/api/ollama/pull")[1]["done"])

    def test_install_jobs_and_cancel(self):
        self.assertEqual(self.json("POST", "/api/local-tools/ocr-languages/install", {"languages": ["ota"]})[0], 400)
        with mock.patch.object(self.app.jobs, "start") as start:
            self.assertEqual(self.json("POST", "/api/local-tools/ollama/install", {})[0], 200)
            self.assertEqual(self.json("POST", "/api/local-tools/ocr-languages/install", {"languages": ["tur", "ara"]})[0], 200)
        self.assertEqual(start.call_args_list[0].args[0], "local:ollama")
        self.assertEqual(start.call_args_list[0].args[1][-2:], ["install-local", "ollama"])
        self.assertEqual(start.call_args_list[1].args[1][-3:], ["ocr-languages", "tur", "ara"])
        self.assertEqual(self.json("POST", "/api/local-tools/ocr/cancel", {}), (200, {"cancelled": False}))

    def test_model_test_button_with_a_local_model(self):
        self.app.engine._provider_cfg = self.cfg()
        status, data = self.json("POST", "/api/models/test", {"name": "ollama/qwen2.5:0.5b"})
        self.assertEqual(status, 200, data)
        self.assertIn("Hello from the local model.", data["message"])


if __name__ == "__main__":
    unittest.main()
