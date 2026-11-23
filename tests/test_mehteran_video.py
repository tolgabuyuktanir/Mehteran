import json
import shutil
import subprocess
import zipfile

from tests.mehteran_support import HomeCase
from mehteran import templates


class VideoTests(HomeCase):
    def test_render_series(self):
        if not all(shutil.which(tool) for tool in ("ffmpeg", "ffprobe", "pango-view")) or not (shutil.which("say") or shutil.which("espeak-ng")):
            self.skipTest("FFmpeg and local speech synthesis required")
        engine = self.engine()
        yaml = templates.read("builtin", "topic-video-series", self.home)
        for mode, platform, seconds, size in (("short", "youtube", 20, (720, 1280)),
                                              ("standard", "instagram", 40, (1280, 720)),
                                              ("standard", "tiktok", 40, (720, 1280)),
                                              ("short", "whatsapp", 20, (720, 1280))):
            with self.subTest(platform=platform, mode=mode):
                inputs = {"topics": "Olives\nTrees", "language": "en", "platform": platform, "mode": mode}
                rid = engine.start(yaml, inputs)
                self.assertEqual(engine.wait(rid, 30), "waiting_approval")
                engine.decide(rid, "review", True)
                self.assertEqual(engine.wait(rid, 90), "succeeded", engine.get(rid)["nodes"])
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
