"""Read-only Windows process identities for the portable tracker.

PID plus creation time prevents stale feeds attaching to a reused PID. The game
image must be Boshy.exe in the exact run directory recorded by the publisher.
"""

from dataclasses import dataclass
from pathlib import PureWindowsPath
import os


@dataclass(frozen=True)
class Identity:
    start: str
    image: str


def inspect(pid):
    if os.name != "nt":
        raise OSError("Windows process inspection requires Windows")
    if type(pid) is not int or not 0 < pid <= 0xFFFFFFFF:
        return None
    import ctypes
    from ctypes import wintypes as w

    api = ctypes.WinDLL("kernel32", use_last_error=True)
    api.OpenProcess.argtypes = (w.DWORD, w.BOOL, w.DWORD)
    api.OpenProcess.restype = w.HANDLE
    api.CloseHandle.argtypes = (w.HANDLE,)
    api.CloseHandle.restype = w.BOOL
    api.GetExitCodeProcess.argtypes = (w.HANDLE, ctypes.POINTER(w.DWORD))
    api.GetExitCodeProcess.restype = w.BOOL
    api.GetProcessTimes.argtypes = (w.HANDLE, *([ctypes.POINTER(w.FILETIME)] * 4))
    api.GetProcessTimes.restype = w.BOOL
    api.QueryFullProcessImageNameW.argtypes = (
        w.HANDLE,
        w.DWORD,
        w.LPWSTR,
        ctypes.POINTER(w.DWORD),
    )
    api.QueryFullProcessImageNameW.restype = w.BOOL
    handle = api.OpenProcess(0x1000, False, pid)  # QUERY_LIMITED_INFORMATION only
    if not handle:
        return None
    try:
        code = w.DWORD()
        if not api.GetExitCodeProcess(handle, ctypes.byref(code)) or code.value != 259:
            return None
        created, exited, kernel, user = (w.FILETIME() for _ in range(4))
        if not api.GetProcessTimes(
            handle, *(ctypes.byref(x) for x in (created, exited, kernel, user))
        ):
            return None
        size = w.DWORD(32768)
        name = ctypes.create_unicode_buffer(size.value)
        if not api.QueryFullProcessImageNameW(handle, 0, name, ctypes.byref(size)):
            return None
        return Identity(
            str((created.dwHighDateTime << 32) | created.dwLowDateTime), name.value
        )
    finally:
        api.CloseHandle(handle)


def alive(data, query=inspect):
    expected = PureWindowsPath(data["game_dir"]) / "Boshy.exe"
    if not expected.is_absolute() or ".." in expected.parts:
        return False
    for kind in ("host", "game"):
        pid, start = data.get(kind + "_pid"), data.get(kind + "_start")
        if (
            type(pid) is not int
            or not 0 < pid <= 0xFFFFFFFF
            or not isinstance(start, str)
            or not start.isdecimal()
        ):
            return False
        found = query(pid)
        if found is None or found.start != start:
            return False
        if kind == "game" and PureWindowsPath(found.image) != expected:
            return False
    return True
