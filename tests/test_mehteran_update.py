"""An update of Mehteran ("git pull" at start): the user's own work stays as it is, and a computer that used the book
translation app keeps it after the update that removed it from Mehteran (mehteran/update.py)."""

import hashlib
import io
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, ai, workflow  # noqa: E402

from mehteran import templates, update  # noqa: E402

# The paths that the removal commit puts into .gitignore (as the repository's .gitignore does).
IGNORED = "/pipeline/\n/translate\n/translate.cmd\n/config.default.toml\n/config.toml\n/prompts/\nbooks/\n"


def tree(folder: Path) -> dict[str, str]:
    """{relative path: hash} of every file below the folder (SQLite's -wal and -shm side files change on a read)."""
    return {p.relative_to(folder).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(folder.rglob("*")) if p.is_file() and not p.name.endswith(("-wal", "-shm"))}


@unittest.skipUnless(shutil.which("git"), "git is not installed")
class UpdateTests(HomeCase):
    def git(self, folder: Path, *args: str) -> str:
        return subprocess.run(["git", "-C", str(folder), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                              check=True, capture_output=True, text=True).stdout

    def write(self, root: Path, files: dict[str, str]) -> None:
        for name, text in files.items():
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            (root / name).write_text(text, encoding="utf-8")

    def commit(self, dev: Path, message: str) -> None:
        self.git(dev, "add", "-A")
        self.git(dev, "commit", "-q", "-m", message)
        self.git(dev, "push", "-q", "origin", "HEAD:main")

    def repositories(self) -> tuple[Path, Path]:
        """A developer's copy and a user's copy of one repository; the first commit has the translation app."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp)
        self.git(tmp, "init", "--bare", "-q", str(tmp / "origin.git"))
        dev, app = tmp / "dev", tmp / "app"
        self.git(tmp, "clone", "-q", str(tmp / "origin.git"), str(dev))
        self.write(dev, {".gitignore": "/config.toml\n/prompts/*.md\nbooks/\n", "mehteran/engine.py": "v1\n",
                         "mehteran/templates/paper.yaml": "builtin v1\n", "mehteran/templates/old.yaml": "builtin old\n",
                         "pipeline/core.py": "translation v1\n", "pipeline/ui/app.js": "ui v1\n", "translate": "#!/bin/sh\n",
                         "config.default.toml": "[general]\n", "prompts/defaults/review.md": "review v1\n"})
        self.commit(dev, "A")
        self.write(dev, {"pipeline/core.py": "translation v2\n"})  # the last version of the translation app
        self.commit(dev, "B")
        self.git(tmp, "clone", "-q", "-b", "main", str(tmp / "origin.git"), str(app))
        return dev, app

    def remove_translation(self, dev: Path) -> None:
        """The commit that takes the translation app out of Mehteran."""
        for path in ("pipeline", "translate", "config.default.toml", "prompts/defaults"):
            self.git(dev, "rm", "-r", "-q", path)
        self.write(dev, {".gitignore": IGNORED, "mehteran/engine.py": "v2\n"})
        self.commit(dev, "without the translation app")

    def test_update_changes_the_code_and_nothing_of_the_user(self):
        dev, app = self.repositories()
        # Mehteran's data of the user: an own template, a changed copy of a built-in one, a finished run, a model list.
        templates.import_text(workflow(ai("a", "TASK:a"), []).replace("id: test-flow", "id: my-flow"), self.home)
        templates.customize("builtin", "document-comparison", "my-comparison", self.home)
        engine = self.engine()
        run_id = engine.start(templates.read("user", "my-flow", self.home), {}, {})
        self.assertEqual(engine.wait(run_id, 30), "succeeded")
        self.write(self.home, {"configurations/models.json": '{"claude": ["opus"]}\n'})
        before = tree(self.home)

        self.write(dev, {"mehteran/engine.py": "v2\n", "mehteran/templates/paper.yaml": "builtin v2\n"})
        self.git(dev, "rm", "-q", "mehteran/templates/old.yaml")
        self.commit(dev, "C")
        with redirect_stdout(io.StringIO()):
            self.assertEqual(update.update(app), 0)

        self.assertEqual((app / "mehteran" / "engine.py").read_text(), "v2\n")  # the update did arrive
        self.assertEqual((app / "mehteran" / "templates" / "paper.yaml").read_text(), "builtin v2\n")
        self.assertFalse((app / "mehteran" / "templates" / "old.yaml").exists())
        self.assertEqual(tree(self.home), before)

    def test_a_computer_that_used_the_translation_keeps_it(self):
        dev, app = self.repositories()
        mine = {"config.toml": "[stages]\nflow = [\"review1\"]\n", "prompts/review.md": "my review\n",
                "books/my-book/source.md": "kitap\n", "books/my-book/work/run.json": "{}\n"}
        self.write(app, mine)
        self.remove_translation(dev)
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(update.update(app), 0)

        self.assertEqual((app / "mehteran" / "engine.py").read_text(), "v2\n")
        # The translation app is back from the git history, in its last version, with its launcher and defaults.
        self.assertEqual((app / "pipeline" / "core.py").read_text(), "translation v2\n")
        self.assertEqual((app / "pipeline" / "ui" / "app.js").read_text(), "ui v1\n")
        self.assertTrue((app / "translate").is_file())
        self.assertEqual((app / "prompts" / "defaults" / "review.md").read_text(), "review v1\n")
        for name, text in mine.items():
            self.assertEqual((app / name).read_text(encoding="utf-8"), text, name)
        self.assertIn("./translate ui", out.getvalue())
        self.assertEqual(self.git(app, "status", "--porcelain"), "")  # git does not see the restored files

        # Later updates leave it alone, and it is not restored twice.
        self.write(dev, {"mehteran/engine.py": "v3\n"})
        self.commit(dev, "D")
        with redirect_stdout(io.StringIO()):
            update.update(app)
        self.assertEqual((app / "mehteran" / "engine.py").read_text(), "v3\n")
        self.assertEqual((app / "pipeline" / "core.py").read_text(), "translation v2\n")
        self.assertFalse(update.keep_translation(app))

    def test_a_computer_that_did_not_use_it_gets_nothing_back(self):
        dev, app = self.repositories()
        self.remove_translation(dev)
        with redirect_stdout(io.StringIO()):
            update.update(app)
        self.assertFalse((app / "pipeline").exists())
        self.assertFalse((app / "translate").exists())
        self.assertEqual(self.git(app, "status", "--porcelain"), "")

    def test_code_removed_on_this_computer_comes_back_in_its_last_version(self):
        """The translation app's code was deleted here but is still in git: the newest committed version comes back."""
        _, app = self.repositories()
        self.write(app, {"books/my-book/source.md": "kitap\n"})
        shutil.rmtree(app / "pipeline")
        with redirect_stdout(io.StringIO()):
            self.assertTrue(update.keep_translation(app))
        self.assertEqual((app / "pipeline" / "core.py").read_text(), "translation v2\n")

    def test_a_copy_without_git_is_left_as_it_is(self):
        root = self.tmp / "code"
        self.write(root, {"books/my-book/source.md": "kitap\n"})
        self.assertFalse(update.keep_translation(root))
        self.assertEqual(update.update(root), 0)


if __name__ == "__main__":
    unittest.main()
