"""Scheduled and batch runs use only local models and API keys, unless the user allows subscriptions on the Setup
tab (Engine.unattended_problem): the providers' consumer terms do not clearly allow automated use of a subscription."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, adapter_cfg, ai, fake_cfg, ready_tools, workflow  # noqa: E402

from mehteran import providers, schedules, templates  # noqa: E402
from mehteran.engine import Engine, RunError  # noqa: E402


class UnattendedTests(HomeCase):
    def engine_with(self, cfg=None, states=ready_tools) -> Engine:
        engine = Engine(self.home, cfg or adapter_cfg())
        engine.awake = False
        engine.tool_states = states
        return engine

    def allow(self, **change):
        user = providers.read_settings(self.home)
        user.update(change)
        providers.write_settings(self.home, user)

    def test_a_subscription_is_refused_for_an_unattended_run_only(self):
        engine = self.engine_with()
        text = workflow(ai("a", "TASK:a", provider="claude"), [])
        with self.assertRaises(RunError) as e:
            engine.start(text, launch=False, unattended=True)
        self.assertIn("Claude Code", e.exception.messages[0])
        engine.start(text, launch=False)  # a run that a person starts: as before

    def test_allowing_subscriptions_on_the_setup_tab(self):
        self.allow(unattended_subscriptions=True)
        self.assertTrue(providers.read_settings(self.home)["unattended_subscriptions"])
        self.engine_with().start(workflow(ai("a", "TASK:a", provider="claude"), []), launch=False, unattended=True)

    def test_an_api_key_or_a_command_provider_is_accepted(self):
        def api_key_states():
            states = ready_tools()
            states["claude"] = {**states["claude"], "billing": "api_key", "key_source": "ANTHROPIC_API_KEY"}
            return states
        self.allow(providers={"claude": {"api_key": True}})
        self.engine_with(states=api_key_states).start(workflow(ai("a", "TASK:a", provider="claude"), []),
                                                      launch=False, unattended=True)
        # a provider given by its command has no known billing (the tests' fake tool)
        self.engine_with(fake_cfg()).start(workflow(ai("a", "TASK:a", provider="fake"), []), launch=False, unattended=True)

    def test_auto_skips_subscriptions_and_says_why_when_nothing_is_left(self):
        engine = self.engine_with()
        with self.assertRaises(RunError) as e:
            engine.start(workflow(ai("a", "TASK:a", provider="auto"), []), launch=False, unattended=True)
        self.assertIn("scheduled or batch run", e.exception.messages[0])
        found = engine.start(workflow(ai("a", "TASK:a", provider="auto"), []), launch=False)
        self.assertEqual(engine.get(found)["status"], "queued")

    def test_a_schedule_is_refused_when_it_is_made(self):
        engine = self.engine_with()
        templates.import_text(workflow(ai("a", "TASK:a", provider="claude"), []).replace("id: test-flow", "id: daily"), self.home)
        with self.assertRaises(RunError):
            schedules.create(engine, "user:daily", {}, {"kind": "days", "days": [0, 1, 2, 3, 4, 5, 6], "time": "09:00"})
        self.assertEqual(schedules.load(self.home), [])
        self.allow(unattended_subscriptions=True)
        schedules.create(engine, "user:daily", {}, {"kind": "days", "days": [0, 1, 2, 3, 4, 5, 6], "time": "09:00"})
        self.assertEqual(len(schedules.load(self.home)), 1)
