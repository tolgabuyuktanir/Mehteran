"""An update of the application ("git pull" at start) and the shared zip: the user's own work stays as it is.

The user's Mehteran data (their templates, runs, model lists) is in the data folder, outside the code folder; the
translation app's workflow and instructions are in config.toml and prompts/, which the update writes back unchanged.
"""

import argparse
import hashlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, ai, workflow  # noqa: E402

from mehteran import templates  # noqa: E402
from pipeline import cli, update  # noqa: E402
from pipeline.core import Project  # noqa: E402


def tree(folder: Path) -> dict[str, str]:
    """{relative path: hash} of every file below the folder (SQLite's -wal and -shm side files change on a read)."""
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file() and not p.name.endswith(("-wal", "-shm"))}


class UpdateKeepsTheUsersWork(HomeCase):
    def git(self, folder: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(folder), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                              check=True, capture_output=True, text=True).stdout

    def write(self, root: Path, files: dict[str, str]) -> None:
        for name, text in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(text, encoding="utf-8")

    @unittest.skipUnless(shutil.which("git"), "git is not installed")
    def test_update_changes_the_code_and_nothing_of_the_user(self):
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        self.git(tmp, "init", "--bare", "-q", str(tmp / "origin.git"))
        dev, app = tmp / "dev", tmp / "app"
        self.git(tmp, "clone", "-q", str(tmp / "origin.git"), str(dev))
        ignore = "/config.toml\n/prompts/*.md\n/prompts/custom/\n/prompts/.defaults.json\n"
        self.write(dev, {".gitignore": ignore, "config.default.toml": "[stages]\nflow = []\n[general]\nretries = 3\n",
                         "prompts/defaults/review.md": "review v1\n", "mehteran/engine.py": "v1\n",
                         "mehteran/templates/paper.yaml": "builtin v1\n", "mehteran/templates/old.yaml": "builtin old\n"})
        self.git(dev, "add", "-A")
        self.git(dev, "commit", "-q", "-m", "A")
        self.git(dev, "push", "-q", "origin", "HEAD:main")
        self.git(tmp, "clone", "-q", "-b", "main", str(tmp / "origin.git"), str(app))

        # The user's work on this computer: the translation workflow, an edited and an own instruction ...
        mine = {"config.toml": "[stages]\nflow = [\"review1\", \"custom1\"]\n[general]\nretries = 7\n",
                "prompts/review.md": "my review\n", "prompts/custom/custom1.md": "my step\n"}
        self.write(app, mine)
        # ... and in Mehteran: an own template, a changed copy of a built-in one, a finished run and a model list.
        templates.import_text(workflow(ai("a", "TASK:a"), []).replace("id: test-flow", "id: my-flow"), self.home)
        templates.customize("builtin", "document-comparison", "my-comparison", self.home)
        engine = self.engine()
        run_id = engine.start(templates.read("user", "my-flow", self.home), {}, {})
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        self.write(self.home, {"configurations/models.json": '{"claude": ["opus"]}\n'})
        before = tree(self.home)
        self.assertTrue({"templates/my-flow.yaml", "templates/my-comparison.yaml", "configurations/models.json"} <= set(before))

        # The update: new code, a changed and a removed built-in template, a changed default instruction and setting.
        self.write(dev, {"mehteran/engine.py": "v2\n", "mehteran/templates/paper.yaml": "builtin v2\n",
                         "prompts/defaults/review.md": "review v2\n",
                         "config.default.toml": "[stages]\nflow = [\"x\"]\n[general]\nretries = 1\nnew_setting = 5\n"})
        self.git(dev, "rm", "-q", "mehteran/templates/old.yaml")
        self.git(dev, "add", "-A")
        self.git(dev, "commit", "-q", "-m", "B")
        self.git(dev, "push", "-q", "origin", "HEAD:main")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(update.update(app), 0)

        self.assertEqual((app / "mehteran" / "engine.py").read_text(), "v2\n")  # the update did arrive
        self.assertEqual((app / "mehteran" / "templates" / "paper.yaml").read_text(), "builtin v2\n")
        self.assertFalse((app / "mehteran" / "templates" / "old.yaml").exists())
        for name, text in mine.items():
            self.assertEqual((app / name).read_text(encoding="utf-8"), text, name)
        self.assertEqual(tree(self.home), before)
        # The first start after the update adds only what is new: the workflow and the user's values stay.
        Project.load(app)
        config = (app / "config.toml").read_text(encoding="utf-8")
        self.assertIn('flow = ["review1", "custom1"]', config)
        self.assertIn("retries = 7", config)
        self.assertIn("new_setting = 5", config)
        self.assertEqual((app / "prompts" / "review.md").read_text(), "my review\n")
        self.assertEqual((app / "prompts" / "custom" / "custom1.md").read_text(), "my step\n")
        self.assertEqual(tree(self.home), before)

    def test_package_holds_mehteran_and_none_of_its_user_data(self):
        root = self.tmp / "code"
        self.write(root, {"mehteran/engine.py": "x\n", "mehteran/templates/paper.yaml": "x\n", "mehteran/_vendor/yaml/LICENSE": "x\n",
                          "mehteran/__pycache__/engine.cpython-314.pyc": "x\n", "mehter": "#!/bin/sh\n", "mehter.cmd": "x\n",
                          "Open Mehteran.command": "x\n", "Open Mehteran.bat": "x\n", "pipeline/cli.py": "x\n"})
        out = self.tmp / "share.zip"
        with redirect_stdout(io.StringIO()):
            cli.cmd_package(Project(root, {}), argparse.Namespace(out=str(out)))
        with zipfile.ZipFile(out) as z:
            names = set(z.namelist())
        for name in ("mehteran/engine.py", "mehteran/templates/paper.yaml", "mehteran/_vendor/yaml/LICENSE", "mehter",
                     "mehter.cmd", "Open Mehteran.command", "Open Mehteran.bat"):
            self.assertIn("TranslationPipeline/" + name, names)
        self.assertFalse([n for n in names if "__pycache__" in n or "my-flow" in n or "executions" in n])


if __name__ == "__main__":
    unittest.main()
