"""Windows-specific code of Mehteran, tested on any system: the job object calls are checked against a fake kernel32
(the real behaviour needs a Windows machine), and the platform guards by mocking sys.platform."""

import ctypes
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from mehteran import paths, web, winjob  # noqa: E402

REPO = Path(__file__).resolve().parent.parent


class FakeKernel32:
    """Records the calls; every function succeeds."""

    def __init__(self, fail=None):
        self.calls, self.fail = [], fail
        for name in ("CreateJobObjectW", "OpenProcess", "SetInformationJobObject", "AssignProcessToJobObject", "CloseHandle"):
            setattr(self, name, self._make(name))

    def _make(self, name):
        def call(*args):
            self.calls.append((name, args))
            return 0 if name == self.fail else (7 if name in ("CreateJobObjectW", "OpenProcess") else 1)
        call.restype = call.argtypes = None
        return call


class JobObjectTest(unittest.TestCase):
    def attach(self, fake):
        with mock.patch.object(sys, "platform", "win32"), mock.patch.object(ctypes, "WinDLL", create=True, return_value=fake):
            return winjob.attach(4321)

    def test_not_windows_does_nothing(self):
        with mock.patch.object(sys, "platform", "darwin"):
            self.assertIsNone(winjob.attach(os.getpid()))
            winjob.close(5)  # no error

    def test_kill_on_close_job_is_created_and_the_process_assigned(self):
        fake = FakeKernel32()
        self.assertEqual(self.attach(fake), 7)
        names = [name for name, _ in fake.calls]
        self.assertEqual(names, ["CreateJobObjectW", "OpenProcess", "SetInformationJobObject", "AssignProcessToJobObject",
                                 "CloseHandle"])  # the process handle is closed, the job handle stays open
        self.assertEqual(fake.calls[1][1][2], 4321)
        _, (job, info_class, buffer, size) = fake.calls[2]
        self.assertEqual(info_class, winjob.JOB_OBJECT_EXTENDED_LIMIT_INFORMATION)
        self.assertEqual(size, 144 if ctypes.sizeof(ctypes.c_void_p) == 8 else 112)  # JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        flags = ctypes.c_uint32.from_buffer(buffer._obj, 16)  # BasicLimitInformation.LimitFlags
        self.assertEqual(flags.value, winjob.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE)

    def test_refused_assignment_closes_the_job_and_returns_none(self):
        fake = FakeKernel32(fail="AssignProcessToJobObject")
        self.assertIsNone(self.attach(fake))
        self.assertEqual([n for n, _ in fake.calls].count("CloseHandle"), 2)  # process and job

    def test_close_closes_the_handle(self):
        fake = FakeKernel32()
        with mock.patch.object(sys, "platform", "win32"), mock.patch.object(ctypes, "WinDLL", create=True, return_value=fake):
            winjob.close(7)
            winjob.close(None)
        self.assertEqual(fake.calls, [("CloseHandle", (7,))])


class ReplaceTest(unittest.TestCase):
    def test_windows_retries_a_refused_replace(self):
        results = [PermissionError(), PermissionError(), None]
        with mock.patch.object(sys, "platform", "win32"), mock.patch.object(paths.os, "replace", side_effect=results) as rep, \
                mock.patch.object(paths.time, "sleep"):
            paths.replace(Path("a"), Path("b"))
        self.assertEqual(rep.call_count, 3)

    def test_windows_gives_up_after_the_wait(self):
        with mock.patch.object(sys, "platform", "win32"), mock.patch.object(paths.os, "replace", side_effect=PermissionError()), \
                mock.patch.object(paths.time, "sleep"):
            with self.assertRaises(PermissionError):
                paths.replace(Path("a"), Path("b"))

    def test_other_systems_do_not_wait(self):
        with mock.patch.object(sys, "platform", "linux"), mock.patch.object(paths.os, "replace", side_effect=PermissionError()) as rep:
            with self.assertRaises(PermissionError):
                paths.replace(Path("a"), Path("b"))
        self.assertEqual(rep.call_count, 1)


class LaunchersTest(unittest.TestCase):
    def test_batch_files_have_crlf_and_no_parenthesised_arguments(self):
        for name in ("mehter.cmd", "scripts/mehter.cmd", "Open Mehteran.bat"):
            data = (REPO / name).read_bytes()
            self.assertEqual(data.count(b"\n"), data.count(b"\r\n"), name)  # every line ends in CRLF
        text = (REPO / "scripts" / "mehter.cmd").read_text()
        for line in text.splitlines():
            if "%*" in line:
                self.assertNotIn("(", line.split("%*")[0].split("python -m mehteran")[0], line)  # no block around %*

    def test_server_does_not_reuse_a_busy_port_on_windows(self):
        self.assertEqual(web.Server.allow_reuse_address, sys.platform != "win32")

    def test_main_module_replaces_what_the_console_cannot_show(self):
        self.assertIn('reconfigure(errors="replace")', (REPO / "mehteran" / "__main__.py").read_text())


if __name__ == "__main__":
    unittest.main()
