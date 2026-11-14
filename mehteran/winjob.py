"""Windows: end a child process, and everything it started, when Mehteran ends.

On macOS and Linux the worker watches its parent process (mehteran.worker). Windows has no parent watch that
survives a killed parent, and closing the console window kills Mehteran without running its exit code. A Windows
job object with the flag "kill on job close" does the work: the system closes the handle when Mehteran ends, however
it ends, and then ends every process in the job. Child processes of a job member join the job.

Only a model worker and the Ollama server that Mehteran started are put in a job. The translation app's book
jobs (pipeline) are not: they must go on when the interface window closes.
"""

from __future__ import annotations

import sys

JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
PROCESS_SET_QUOTA, PROCESS_TERMINATE = 0x0100, 0x0001


def attach(pid: int) -> int | None:
    """Puts process pid in a new job object that ends it when the handle closes. Returns the job handle (keep it until
    the process is done, then pass it to close()), or None: not Windows, or the system refused (the process is in a
    job that does not allow nesting; Windows 7)."""
    if sys.platform != "win32":
        return None
    import ctypes
    from ctypes import wintypes

    class Basic(ctypes.Structure):
        _fields_ = [("PerProcessUserTimeLimit", ctypes.c_int64), ("PerJobUserTimeLimit", ctypes.c_int64),
                    ("LimitFlags", ctypes.c_uint32), ("MinimumWorkingSetSize", ctypes.c_size_t),
                    ("MaximumWorkingSetSize", ctypes.c_size_t), ("ActiveProcessLimit", ctypes.c_uint32),
                    ("Affinity", ctypes.c_size_t), ("PriorityClass", ctypes.c_uint32),
                    ("SchedulingClass", ctypes.c_uint32)]

    class Extended(ctypes.Structure):
        _fields_ = [("BasicLimitInformation", Basic), ("IoCounters", ctypes.c_uint64 * 6),
                    ("ProcessMemoryLimit", ctypes.c_size_t), ("JobMemoryLimit", ctypes.c_size_t),
                    ("PeakProcessMemoryUsed", ctypes.c_size_t), ("PeakJobMemoryUsed", ctypes.c_size_t)]

    k = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    k.CreateJobObjectW.restype = wintypes.HANDLE
    k.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
    k.OpenProcess.restype = wintypes.HANDLE
    k.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    k.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
    k.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    job = k.CreateJobObjectW(None, None)
    if not job:
        return None
    info = Extended()
    info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    process = k.OpenProcess(PROCESS_SET_QUOTA | PROCESS_TERMINATE, False, pid)
    ok = bool(process) and k.SetInformationJobObject(job, JOB_OBJECT_EXTENDED_LIMIT_INFORMATION, ctypes.byref(info),
                                                      ctypes.sizeof(info)) and k.AssignProcessToJobObject(job, process)
    if process:
        k.CloseHandle(process)
    if not ok:
        k.CloseHandle(job)
        return None
    return int(job)


def close(job: int | None) -> None:
    """Closes the job handle; this ends any process of the job that still runs."""
    if job and sys.platform == "win32":
        import ctypes
        from ctypes import wintypes
        k = ctypes.WinDLL("kernel32")  # type: ignore[attr-defined]
        k.CloseHandle.argtypes = [wintypes.HANDLE]
        k.CloseHandle(job)
