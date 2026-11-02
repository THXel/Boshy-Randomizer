"""Read-only observer for one hash-verified native game process.

No write, allocation, injection, or debugger rights are requested. The retained
handle pins the process identity; a reused PID cannot redirect observations.
"""

import ctypes as c
from ctypes import wintypes as w
from pathlib import Path
from platform_support.observer import FrameObserver
from app_paths import RUNS
from platform_support.windows_api import kernel, games, signature
from tracker.windows_process import inspect


class MODULEENTRY32(c.Structure):
    _fields_ = [
        ("dwSize", w.DWORD),
        ("th32ModuleID", w.DWORD),
        ("th32ProcessID", w.DWORD),
        ("GlblcntUsage", w.DWORD),
        ("ProccntUsage", w.DWORD),
        ("modBaseAddr", c.POINTER(c.c_ubyte)),
        ("modBaseSize", w.DWORD),
        ("hModule", w.HMODULE),
        ("szModule", w.WCHAR * 256),
        ("szExePath", w.WCHAR * 260),
    ]


signature(kernel, "CreateToolhelp32Snapshot", w.HANDLE, w.DWORD, w.DWORD)
signature(kernel, "Module32FirstW", w.BOOL, w.HANDLE, c.POINTER(MODULEENTRY32))
signature(kernel, "CloseHandle", w.BOOL, w.HANDLE)
signature(kernel, "OpenProcess", w.HANDLE, w.DWORD, w.BOOL, w.DWORD)
signature(
    kernel,
    "ReadProcessMemory",
    w.BOOL,
    w.HANDLE,
    w.LPCVOID,
    w.LPVOID,
    c.c_size_t,
    c.POINTER(c.c_size_t),
)


class WindowsReader(FrameObserver):
    def __init__(self, folder, expected):
        self.handle = None
        folder = Path(folder).resolve()
        if folder.parent != RUNS.resolve() or not folder.name.startswith(
            "rebuilt-menu-"
        ):
            raise ValueError("Observer boundary")
        from menu_host.runtime import verify_engine

        verify_engine(folder / "Boshy.exe", expected)
        matches = [pid for pid, path in games(RUNS).items() if path == folder]
        if len(matches) != 1:
            raise RuntimeError("Expected exactly one owned game process")
        self.pid = matches[0]
        self.identity = inspect(self.pid)
        if (
            self.identity is None
            or Path(self.identity.image).resolve() != folder / "Boshy.exe"
        ):
            raise RuntimeError("Game identity changed")
        self.handle = kernel.OpenProcess(0x1000 | 0x10, False, self.pid)
        if not self.handle:
            raise c.WinError(c.get_last_error())
        try:
            snapshot = kernel.CreateToolhelp32Snapshot(0x8 | 0x10, self.pid)
            if snapshot == c.c_void_p(-1).value:
                raise c.WinError(c.get_last_error())
            try:
                entry = MODULEENTRY32(dwSize=c.sizeof(MODULEENTRY32))
                if not kernel.Module32FirstW(snapshot, c.byref(entry)):
                    raise c.WinError(c.get_last_error())
                if Path(entry.szExePath).resolve() != folder / "Boshy.exe":
                    raise RuntimeError("Unexpected game module")
                self.base = c.cast(entry.modBaseAddr, c.c_void_p).value
            finally:
                kernel.CloseHandle(snapshot)
            if inspect(self.pid) != self.identity:
                raise RuntimeError("Game identity changed during attachment")
        except BaseException:
            self.close()
            raise

    def read(self, address, size):
        if not 4 <= size <= 256 or not 0x10000 <= address <= 0xFFFFFFFF - size:
            raise ValueError("Observer read boundary")
        data, got = c.create_string_buffer(size), c.c_size_t()
        if (
            not self.handle
            or not kernel.ReadProcessMemory(
                self.handle, address, data, size, c.byref(got)
            )
            or got.value != size
        ):
            raise RuntimeError("Frame loading")
        return data.raw

    def close(self):
        if self.handle:
            kernel.CloseHandle(self.handle)
            self.handle = None
