"""mehter doctor: an installed tool whose help no longer names one of Mehteran's options is reported."""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mehteran import doctor  # noqa: E402
from mehteran.providers.base import Adapter  # noqa: E402


class FakeTool(Adapter):
    id, name, vendor, tool = "fake", "Fake CLI", "Test", None

    def __init__(self, program: str):
        self.program = program

    def argv(self, model, effort, out_file):
        return [self.program, "exec", "--quiet", "--sandbox", "read-only", "--gone"]


@unittest.skipIf(os.name == "nt", "the fake tool is a shell script")
class DoctorTests(unittest.TestCase):
    def tool(self, help_text: str) -> FakeTool:
        folder = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: __import__("shutil").rmtree(folder))
        script = folder / "fake-cli"
        # "fake-cli exec --help" prints the subcommand's help; anything else prints nothing.
        script.write_text(f'#!/bin/sh\n[ "$1" = exec ] && [ "$2" = --help ] && printf %s "{help_text}"\nexit 0\n')
        script.chmod(0o755)
        return FakeTool(str(script))

    def test_missing_options_are_named(self):
        answered, missing = doctor.check_options(self.tool("Usage: fake-cli exec [--quiet] [--sandbox MODE]"))
        self.assertTrue(answered)
        self.assertEqual(missing, ["--gone"])

    def test_all_options_present(self):
        self.assertEqual(doctor.check_options(self.tool("--quiet --sandbox MODE --gone")), (True, []))

    def test_no_help_is_reported(self):
        self.assertEqual(doctor.check_options(self.tool("")), (False, []))


if __name__ == "__main__":
    unittest.main()
