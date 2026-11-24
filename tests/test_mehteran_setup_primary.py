"""Setup's first question ("Which AI account do you have?"): the chosen account decides which tool Setup asks for,
what "Install missing tools" installs and which tool `auto` tries first. Nothing is installed or signed in here."""

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_mehteran_editor as editor  # noqa: E402  (its ServerCase and fake tool states; no test class is imported)

from mehteran import providers, web  # noqa: E402
from mehteran.common import tools  # noqa: E402


class SettingTests(unittest.TestCase):
    def test_primary_is_kept_only_when_known(self):
        import tempfile
        home = Path(tempfile.mkdtemp())
        user = providers.read_settings(home)
        self.assertEqual(user["primary"], "")
        user["primary"] = "codex"
        self.assertEqual(providers.write_settings(home, user)["primary"], "codex")
        user["primary"] = "rm -rf"
        self.assertEqual(providers.write_settings(home, user)["primary"], "")

    def test_codex_sign_in_mode_is_shown_in_the_interface_language(self):
        from mehteran import i18n
        i18n.set_request("tr")
        try:
            self.assertEqual(tools._codex_mode("Logged in using ChatGPT"), "ChatGPT hesabı")
            self.assertEqual(tools._codex_mode("Logged in using an API key - sk-***"), "API anahtarı")
            self.assertEqual(tools._codex_mode("something else"), "something else")
        finally:
            i18n.set_request("en")


@mock.patch.object(web.tools, "extend_path", lambda *a: None)
class PrimaryRouteTests(editor.ServerCase):
    def tools(self):
        with mock.patch.object(web.tools, "status", side_effect=editor.fake_status), \
                mock.patch.object(web.system, "can_open_terminal", return_value=True):
            status, data = self.json("GET", "/api/tools")
        self.assertEqual(status, 200)
        return data, {t["id"]: t for t in data["tools"]}

    def test_without_a_choice_the_templates_decide(self):
        data, by = self.tools()
        self.assertEqual(data["primary"], "")
        self.assertTrue(by["claude"]["required"], "a template uses Claude Code")

    def test_the_chosen_account_is_the_one_tool_asked_for(self):
        with mock.patch.object(web.Jobs, "start") as start, mock.patch.object(web.shutil, "which", return_value=None):
            status, data = self.json("PUT", "/api/setup/primary", {"primary": "codex"})
        self.assertEqual((status, data["primary"]), (200, "codex"))
        names = start.call_args.args[1]
        self.assertIn("codex", names)
        self.assertIn("pdf", names)
        self.assertNotIn("claude", names, "a ChatGPT user does not get Claude Code because a template names it")
        data, by = self.tools()
        self.assertEqual(data["primary"], "codex")
        self.assertTrue(by["codex"]["required"] and by["pdf"]["required"])
        self.assertFalse(by["claude"]["required"])
        self.assertEqual(providers.read_settings(self.home)["order"][0], "codex", "`auto` tries the chosen tool first")

    def test_install_missing_follows_the_choice(self):
        with mock.patch.object(web.Jobs, "start"), mock.patch.object(web.shutil, "which", return_value=None):
            self.json("PUT", "/api/setup/primary", {"primary": "antigravity"})
        with mock.patch.object(web.Jobs, "start") as start, mock.patch.object(web.shutil, "which", return_value=None):
            self.json("POST", "/api/tools/install-missing")
        self.assertEqual(set(start.call_args.args[1][4:]), {"antigravity", "pdf"})

    def test_no_subscription_installs_ollama_and_keeps_the_order(self):
        with mock.patch.object(web.Jobs, "start") as start, mock.patch.object(web.shutil, "which", return_value=None), \
                mock.patch("mehteran.ollama.binary", return_value=(None, None)):
            status, data = self.json("PUT", "/api/setup/primary", {"primary": "ollama"})
        self.assertEqual((status, data["primary"]), (200, "ollama"))
        started = [c.args[0] for c in start.call_args_list]
        self.assertIn("local:ollama", started)
        self.assertEqual(providers.read_settings(self.home)["order"], [])

    def test_change_and_bad_values(self):
        with mock.patch.object(web.Jobs, "start"), mock.patch.object(web.shutil, "which", return_value=None):
            self.json("PUT", "/api/setup/primary", {"primary": "claude"})
        self.assertEqual(self.json("PUT", "/api/setup/primary", {"primary": ""}), (200, {"primary": ""}))
        self.assertEqual(providers.read_settings(self.home)["primary"], "")
        for bad in ("gemini", "openai-local", 3, None):
            self.assertEqual(self.json("PUT", "/api/setup/primary", {"primary": bad})[0], 400, bad)


if __name__ == "__main__":
    unittest.main()
