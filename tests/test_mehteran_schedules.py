"""Scheduled runs (mehteran/schedules.py) and the background server (mehteran/background.py).

The Scheduler is driven by tick(now) with a chosen time; no thread is started and no notification is sent (a list
takes them). The background service file is only written as text; no service is turned on.
"""

import json
import os
import plistlib
import sys
import time
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran_support import HomeCase, ai, workflow  # noqa: E402

from mehteran import background, schedules  # noqa: E402
from mehteran.engine import RunError  # noqa: E402

TOPIC = "  - {id: topic, type: text, default: news}\n"
FLOW = workflow(ai("say", "TASK:say Say {{inputs.topic}}."), [], inputs=TOPIC).replace("id: test-flow", "id: daily")
FILE_FLOW = workflow(ai("say", "TASK:say Read {{inputs.doc}}."), [],
                     inputs="  - {id: doc, type: file}\n").replace("id: test-flow", "id: needs-file")
DAILY = {"days": [0, 1, 2, 3, 4, 5, 6], "time": "08:00"}


def at(text: str) -> float:
    return datetime.fromisoformat(text).timestamp()


class RuleTests(unittest.TestCase):
    def test_the_next_time_of_days_and_a_time(self):
        weekdays = {"days": [0, 1, 2, 3, 4], "time": "08:30"}
        self.assertEqual(schedules.next_time(weekdays, at("2026-11-13 07:00")), at("2026-11-13 08:30"))  # Friday
        self.assertEqual(schedules.next_time(weekdays, at("2026-11-13 08:30")), at("2026-11-16 08:30"))  # then Monday
        self.assertEqual(schedules.next_time({"every_hours": 6}, 1000.0), 1000.0 + 6 * 3600)

    def test_a_bad_rule_is_refused(self):
        for rule in (None, {}, {"days": [], "time": "08:00"}, {"days": [7], "time": "08:00"}, {"days": [1], "time": "8:00"},
                     {"days": [1], "time": "24:00"}, {"every_hours": 0}, {"every_hours": 169}, {"every_hours": True},
                     {"days": [True], "time": "08:00"}):
            with self.assertRaises(RunError, msg=rule):
                schedules.clean_rule(rule)
        self.assertEqual(schedules.clean_rule({"days": [3, 1, 1], "time": "07:05", "x": 1}), {"days": [1, 3], "time": "07:05"})


class ScheduleTests(HomeCase):
    def setUp(self):
        super().setUp()
        (self.home / "templates").mkdir(parents=True, exist_ok=True)
        (self.home / "templates" / "daily.yaml").write_text(FLOW, encoding="utf-8")
        (self.home / "templates" / "needs-file.yaml").write_text(FILE_FLOW, encoding="utf-8")
        self.sent = []
        self.eng = self.engine()
        self.scheduler = schedules.Scheduler(self.eng, notify_fn=lambda title, text: self.sent.append(text))

    def make(self, **more):
        return schedules.create(self.eng, "user:daily", {"topic": "rain"}, more.pop("rule", DAILY), **more)

    def test_a_schedule_starts_its_run_at_its_time_with_its_inputs(self):
        item = self.make(name="Morning")
        self.assertEqual(self.scheduler.tick(item["next_at"] - 60), [])
        [run_id] = self.scheduler.tick(item["next_at"] + 1)
        self.assertEqual(self.eng.wait(run_id, 30), "succeeded")
        run = self.eng.get(run_id)
        self.assertEqual(run["inputs"]["topic"], "rain")
        self.assertEqual(self.eng.store.run(run_id)["schedule"], item["id"])
        saved = schedules.load(self.home)[0]
        self.assertEqual(saved["last_run"], run_id)
        self.assertGreater(saved["next_at"], item["next_at"])
        self.scheduler.tick(item["next_at"] + 2)
        self.assertEqual(self.sent, ["“Morning” is ready."])  # once per status
        self.scheduler.tick(item["next_at"] + 3)
        self.assertEqual(len(self.sent), 1)

    def test_times_missed_while_closed_start_one_run(self):
        item = self.make()
        started = self.scheduler.tick(item["next_at"] + 5 * 86400)  # five days later
        self.assertEqual(len(started), 1)
        self.eng.wait(started[0], 30)
        self.assertEqual(self.scheduler.tick(item["next_at"] + 5 * 86400 + 60), [])

    def test_a_running_previous_run_skips_the_time(self):
        item = self.make()
        [first] = self.scheduler.tick(item["next_at"] + 1)
        self.eng.wait(first, 30)
        self.eng.store.update_run(first, status="running")
        later = schedules.load(self.home)[0]["next_at"]
        self.assertEqual(self.scheduler.tick(later + 1), [])
        self.assertIn("still running", schedules.load(self.home)[0]["last_error"])
        self.eng.store.update_run(first, status="waiting_approval")  # waiting for a person does not hold it up
        [second] = self.scheduler.tick(schedules.load(self.home)[0]["next_at"] + 1)
        self.eng.wait(second, 30)

    def test_a_paused_schedule_does_not_start_and_resumes_from_now(self):
        item = self.make()
        schedules.update(self.home, item["id"], {"enabled": False})
        self.assertEqual(self.scheduler.tick(item["next_at"] + 86400 * 3), [])
        resumed = schedules.update(self.home, item["id"], {"enabled": True})
        self.assertGreater(resumed["next_at"], time.time())

    def test_a_workflow_that_no_longer_starts_is_reported(self):
        item = self.make()
        item.pop("workflow_yaml")  # a schedule created before snapshots were stored
        schedules._save(self.home, [item])
        (self.home / "templates" / "daily.yaml").unlink()
        self.assertEqual(self.scheduler.tick(item["next_at"] + 1), [])
        self.assertTrue(schedules.load(self.home)[0]["last_error"])
        self.assertTrue(self.sent and "could not start" in self.sent[0])

    def test_new_schedule_uses_snapshot_after_template_is_removed(self):
        item = self.make()
        (self.home / "templates" / "daily.yaml").unlink()
        run_id = schedules.run_now(self.eng, item["id"])
        self.assertEqual(self.eng.wait(run_id, 30), "succeeded")
        self.assertEqual(self.eng.get(run_id)["workflow_yaml"], item["workflow_yaml"])

    def test_legacy_schedule_recovers_its_last_run_version(self):
        item = self.make()
        prior = schedules.run_now(self.eng, item["id"])
        self.assertEqual(self.eng.wait(prior, 30), "succeeded")
        [legacy] = schedules.load(self.home)
        legacy.pop("workflow_yaml")
        schedules._save(self.home, [legacy])
        (self.home / "templates" / "daily.yaml").unlink()
        schedules.pin_legacy_schedules(self.eng)
        [pinned] = schedules.load(self.home)
        self.assertEqual(pinned["workflow_yaml"], item["workflow_yaml"])

    def test_what_cannot_be_scheduled(self):
        with self.assertRaises(RunError) as caught:
            schedules.create(self.eng, "user:needs-file", {}, DAILY)
        self.assertIn("file", caught.exception.messages[0])
        with self.assertRaises(RunError):
            schedules.create(self.eng, "user:daily", {"nope": "x"}, DAILY)
        with self.assertRaises(RunError):
            schedules.create(self.eng, "user:daily", {}, {"every_hours": 0})

    def test_run_now_delete_and_the_web_routes(self):
        from mehteran.web import App
        with mock.patch("mehteran.history.Automation.kick"):
            app = App(self.eng)
        item = app.schedule_create(None, {"template": "user:daily", "values": {"topic": "sun"}, "rule": {"every_hours": 2}})
        self.assertEqual([s["id"] for s in app.schedule_list(None, {})], [item["id"]])
        run_id = app.schedule_run([None, item["id"]], {})["id"]
        self.assertEqual(self.eng.wait(run_id, 30), "succeeded")
        self.assertEqual(app.schedule_list(None, {})[0]["last_status"], "succeeded")
        self.assertFalse(app.schedule_update([None, item["id"]], {"enabled": False})["enabled"])
        app.schedule_delete([None, item["id"]], {})
        self.assertEqual(app.schedule_list(None, {}), [])
        with self.assertRaises(RunError):
            app.schedule_delete([None, item["id"]], {})


class BackgroundTests(HomeCase):
    def test_the_service_file_starts_the_interface_without_keys(self):
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "secret-value", "PATH": "/opt/tools/bin:/usr/bin"}):
            for platform in ("darwin", "linux", "win32"):
                with mock.patch.object(sys, "platform", platform):
                    text = background.service_text(self.home)
                    shown = text.decode("utf-16" if platform == "win32" else "utf-8")
                    self.assertNotIn("secret-value", shown, platform)
                    self.assertIn("/opt/tools/bin", shown, platform)
                    self.assertIn("--no-browser", shown, platform)
                    self.assertIn(background.ENV_FLAG, shown, platform)
        with mock.patch.object(sys, "platform", "darwin"), \
                mock.patch.dict(os.environ, {"PATH": "/usr/bin"}):
            plist = plistlib.loads(background.service_text(self.home))
        self.assertEqual(plist["ProgramArguments"][1:], ["-m", "mehteran", "ui", "--no-browser"])
        self.assertTrue(plist["RunAtLoad"])
        self.assertEqual(plist["EnvironmentVariables"][background.ENV_FLAG], "1")

    def test_the_status_reads_the_process_id(self):
        self.home.mkdir(parents=True)
        self.assertFalse(background.status(self.home)["running"])
        background.pid_file(self.home).write_text(str(os.getpid()))
        self.assertTrue(background.status(self.home)["running"])
        background.pid_file(self.home).write_text("999999999")
        self.assertFalse(background.status(self.home)["running"])
        json.dumps(background.status(self.home))


if __name__ == "__main__":
    unittest.main()
