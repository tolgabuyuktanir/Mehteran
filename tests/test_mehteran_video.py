from contextlib import redirect_stdout
from io import StringIO
import json
import shutil
import subprocess
import zipfile
from unittest.mock import patch

from tests.mehteran_support import HomeCase
from mehteran import cli, templates, video


class VideoTests(HomeCase):
    def test_missing_video_tools_stop_before_model_calls(self):
        engine = self.engine()
        yaml = templates.read("builtin", "topic-video-series", self.home)
        with patch.object(video, "video_tools", side_effect=ValueError("Missing media tools")):
            rid = engine.start(yaml, {"topics": "Olives", "model": "fake"})
            self.assertEqual(engine.wait(rid, 30), "failed")
        self.assertIn("Missing media tools", engine.get(rid)["nodes"]["check"]["error"])
        self.assertEqual(self.calls(), [])


    def test_premium_requires_credentials(self):
        engine = self.engine()
        yaml = templates.read("builtin", "topic-video-series", self.home)
        with (patch.dict("os.environ", {"OPENAI_API_KEY": "", "ELEVENLABS_API_KEY": ""}),
              patch.object(video, "ffmpeg", return_value=(self.tmp / "ffmpeg", None)),
              patch.object(video.shutil, "which", return_value="/fixture/tool")):
            rid = engine.start(yaml, {"topics": "Olives", "model": "fake"})
            self.assertEqual(engine.wait(rid, 30), "failed")
        self.assertIn("ElevenLabs", engine.get(rid)["nodes"]["check"]["error"])
        self.assertEqual(self.calls(), [])

    def test_render_series(self):
        if not all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe", "pango-view")):
            self.skipTest("FFmpeg and Pango required")
        engine = self.engine()
        art = self.tmp / "fixture.png"
        speech = self.tmp / "fixture.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=green:s=96x64",
                        "-frames:v", "1", str(art)], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=1",
                        str(speech)], check=True)
        video.video_media.save(engine.home, {"openai_key": "fixture-openai-key", "elevenlabs_key": "fixture-eleven-key",
                                             "voice_id": "FixtureVoiceId01"})
        with patch.object(video.video_media, "image", side_effect=lambda prompt, portrait, path, abort, config: shutil.copyfile(art, path)) as images, \
             patch.object(video.video_media, "speech", side_effect=lambda line, lang, path, abort, config: shutil.copyfile(speech, path)) as voices:
            self._test_platforms(engine)
        self.assertEqual(images.call_count, 8)
        self.assertEqual(voices.call_count, 12)
        self.assertEqual(images.call_args.args[-1]["openai_key"], "fixture-openai-key")
        self.assertEqual(voices.call_args.args[-1]["voice_id"], "FixtureVoiceId01")

    def _test_platforms(self, engine):
        for mode, platform, seconds, size in (("short", "youtube", 20, (720, 1280)),
                                              ("standard", "instagram", 40, (1280, 720)),
                                              ("standard", "tiktok", 40, (720, 1280)),
                                              ("short", "whatsapp", 20, (720, 1280))):
            with self.subTest(platform=platform, mode=mode):
                inputs = {"topics": "Olives\nTrees", "model": "fake", "language": "tr", "platform": platform, "mode": mode}
                args = [arg for key, value in inputs.items() for arg in ("--input", f"{key}={value}")]
                stdout = StringIO()
                with patch.object(cli, "Engine", return_value=engine), patch.object(cli.paths, "home", return_value=self.home), redirect_stdout(stdout):
                    self.assertEqual(cli.main(["run", "builtin:topic-video-series", *args]), 3, stdout.getvalue())
                    rid = engine.list()[0]["id"]
                    self.assertEqual(cli.main(["approve", rid, "review"]), 3, stdout.getvalue())
                    preview = engine.get(rid)["nodes"]["voice"]["outputs"]["audio"]
                    self.assertGreater((engine.run_dir(rid) / preview).stat().st_size, 1000)
                    self.assertIn(str(engine.run_dir(rid) / preview), stdout.getvalue())
                    self.assertEqual(cli.main(["approve", rid, "listen"]), 0, stdout.getvalue())
                self.assertIn("videos.zip", stdout.getvalue())
                output = engine.get(rid)["nodes"]["render"]["outputs"]["zip"]
                with zipfile.ZipFile(engine.run_dir(rid) / output) as archive:
                    names = [f"{title}-{platform}-{mode}.mp4" for title in ("01-Olives", "02-Trees")]
                    self.assertEqual(archive.namelist(), names)
                    for member in names:
                        video = archive.extract(member, self.tmp)
                        data = subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-of", "json", video])
                        streams = json.loads(data)["streams"]
                        self.assertEqual([s["codec_name"] for s in streams], ["h264", "aac"])
                        self.assertAlmostEqual(float(streams[0]["duration"]), seconds, delta=0.25)
                        self.assertEqual((streams[0]["width"], streams[0]["height"]), size)
