import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from mehteran.common import tools


class CodexCredentialsTests(unittest.TestCase):
    def test_stored_sign_in_counts_when_status_command_fails(self):
        failed = mock.Mock(returncode=1, stdout="", stderr="error")
        with tempfile.TemporaryDirectory() as home:
            (Path(home) / "auth.json").write_text('{"a":1}')
            with mock.patch.dict(os.environ, {"CODEX_HOME": home}), mock.patch.object(tools, "_run", return_value=failed):
                self.assertTrue(tools.login_status("codex")[0])
        with tempfile.TemporaryDirectory() as empty:
            with mock.patch.dict(os.environ, {"CODEX_HOME": empty}), mock.patch.object(tools, "_run", return_value=failed):
                self.assertFalse(tools.login_status("codex")[0])


if __name__ == "__main__":
    unittest.main()
