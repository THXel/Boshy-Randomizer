"""Win32 window/process adapter. Controls only a verified owned game window."""

import ctypes as c
import time
from ctypes import wintypes as w
from pathlib import Path
from tracker.windows_process import inspect

kernel = c.WinDLL("kernel32", use_last_error=True)
user = c.WinDLL("user32", use_last_error=True)
psapi = c.WinDLL("psapi", use_last_error=True)
CALLBACK = c.WINFUNCTYPE(w.BOOL, w.HWND, w.LPARAM)


def signature(dll, name, result, *args):
    fn = getattr(dll, name)
    fn.restype, fn.argtypes = result, args
    return fn


signature(
    psapi, "EnumProcesses", w.BOOL, c.POINTER(w.DWORD), w.DWORD, c.POINTER(w.DWORD)
)
signature(user, "EnumWindows", w.BOOL, CALLBACK, w.LPARAM)
signature(user, "IsWindowVisible", w.BOOL, w.HWND)
signature(user, "GetWindow", w.HWND, w.HWND, w.UINT)
signature(user, "GetWindowTextW", c.c_int, w.HWND, w.LPWSTR, c.c_int)
signature(user, "GetWindowThreadProcessId", w.DWORD, w.HWND, c.POINTER(w.DWORD))
signature(user, "GetForegroundWindow", w.HWND)
signature(user, "SetForegroundWindow", w.BOOL, w.HWND)
signature(user, "ShowWindow", w.BOOL, w.HWND, c.c_int)
signature(user, "PostMessageW", w.BOOL, w.HWND, w.UINT, w.WPARAM, w.LPARAM)
signature(user, "GetWindowRect", w.BOOL, w.HWND, c.POINTER(w.RECT))
signature(user, "GetClientRect", w.BOOL, w.HWND, c.POINTER(w.RECT))
signature(user, "GetWindowLongW", w.LONG, w.HWND, c.c_int)
signature(user, "SetWindowLongW", w.LONG, w.HWND, c.c_int, w.LONG)
signature(
    user,
    "SetWindowPos",
    w.BOOL,
    w.HWND,
    w.HWND,
    c.c_int,
    c.c_int,
    c.c_int,
    c.c_int,
    w.UINT,
)
signature(user, "GetMenu", w.HMENU, w.HWND)
signature(
    user, "AdjustWindowRectEx", w.BOOL, c.POINTER(w.RECT), w.DWORD, w.BOOL, w.DWORD
)
signature(user, "MonitorFromWindow", w.HANDLE, w.HWND, w.DWORD)
signature(
    user,
    "CreateWindowExW",
    w.HWND,
    w.DWORD,
    w.LPCWSTR,
    w.LPCWSTR,
    w.DWORD,
    c.c_int,
    c.c_int,
    c.c_int,
    c.c_int,
    w.HWND,
    w.HMENU,
    w.HINSTANCE,
    w.LPVOID,
)
signature(user, "DestroyWindow", w.BOOL, w.HWND)
signature(
    user, "PeekMessageW", w.BOOL, c.POINTER(w.MSG), w.HWND, w.UINT, w.UINT, w.UINT
)
signature(user, "TranslateMessage", w.BOOL, c.POINTER(w.MSG))
signature(user, "DispatchMessageW", c.c_ssize_t, c.POINTER(w.MSG))


def dpi_aware():
    try:
        fn = signature(user, "SetProcessDpiAwarenessContext", w.BOOL, w.HANDLE)
        fn(c.c_void_p(-4))  # Physical pixels, per-monitor v2. Already-set is benign.
    except AttributeError:
        signature(user, "SetProcessDPIAware", w.BOOL)()


def process_ids():
    count = 1024
    while count <= 65536:
        data, used = (w.DWORD * count)(), w.DWORD()
        if not psapi.EnumProcesses(data, c.sizeof(data), c.byref(used)):
            raise c.WinError(c.get_last_error())
        if used.value < c.sizeof(data):
            return data[: used.value // c.sizeof(w.DWORD)]
        count *= 2
    raise RuntimeError("Process inventory exceeded supported bound")


def games(runs):
    runs = Path(runs).resolve()
    found = {}
    for pid in process_ids():
        identity = inspect(pid)
        if identity is None:
            continue
        image = Path(identity.image)
        if image.name.lower() == "boshy.exe" and image.parent.parent.resolve() == runs:
            found[pid] = image.parent.resolve()
    return found


def windows():
    result = []

    @CALLBACK
    def visit(hwnd, _):
        if user.IsWindowVisible(hwnd) and not user.GetWindow(hwnd, 4):
            title = c.create_unicode_buffer(256)
            user.GetWindowTextW(hwnd, title, len(title))
            if title.value == "I Wanna Be The Boshy":
                pid = w.DWORD()
                user.GetWindowThreadProcessId(hwnd, c.byref(pid))
                result.append(
                    [hex(hwnd), "0", str(pid.value), "localhost", title.value]
                )
        return True

    if not user.EnumWindows(visit, 0):
        raise c.WinError(c.get_last_error())
    return result


def hwnd(value):
    return int(value, 16) if isinstance(value, str) else value


def owns_window(window, pid):
    """Validate the retained window directly, without scanning every process."""
    found = w.DWORD()
    return bool(user.GetWindowThreadProcessId(hwnd(window), c.byref(found))) and found.value == pid


def close_window(window):
    # Keep the system-menu path used by the game's own title-bar close button.
    # Direct WM_CLOSE can fail during Wine graphics teardown.
    if not user.PostMessageW(hwnd(window), 0x112, 0xF060, 0):
        raise c.WinError(c.get_last_error())


class KEYBDINPUT(c.Structure):
    _fields_ = [
        ("wVk", w.WORD),
        ("wScan", w.WORD),
        ("dwFlags", w.DWORD),
        ("time", w.DWORD),
        ("dwExtraInfo", c.c_size_t),
    ]


class MOUSEINPUT(c.Structure):
    _fields_ = [
        ("dx", w.LONG),
        ("dy", w.LONG),
        ("mouseData", w.DWORD),
        ("dwFlags", w.DWORD),
        ("time", w.DWORD),
        ("dwExtraInfo", c.c_size_t),
    ]


class INPUTDATA(c.Union):
    _fields_ = [("ki", KEYBDINPUT), ("mi", MOUSEINPUT)]


class INPUT(c.Structure):
    _anonymous_ = ("data",)
    _fields_ = [("type", w.DWORD), ("data", INPUTDATA)]


signature(user, "SendInput", w.UINT, w.UINT, c.POINTER(INPUT), c.c_int)
KEYS = {
    "Return": 13,
    "Escape": 27,
    "space": 32,
    "Left": 37,
    "Up": 38,
    "Right": 39,
    "Down": 40,
    "F2": 113,
    "F4": 115,
    "Shift_L": 16,
    "Control_L": 17,
    "q": 81,
    "r": 82,
    "z": 90,
}


def key(window, name):
    target = hwnd(window)
    code = KEYS[name]
    user.ShowWindow(target, 9)
    user.SetForegroundWindow(target)
    time.sleep(0.1)
    # SetForegroundWindow can return zero with last-error zero when focus is
    # denied. Check the actual foreground; never interpret that as a crash.
    if user.GetForegroundWindow() != target:
        raise RuntimeError("Please focus the Boshy game window")
    down = INPUT(type=1, ki=KEYBDINPUT(wVk=code))
    up = INPUT(type=1, ki=KEYBDINPUT(wVk=code, dwFlags=2))
    if user.SendInput(1, c.byref(down), c.sizeof(INPUT)) != 1:
        raise c.WinError(c.get_last_error())
    try:
        time.sleep(0.13)
    finally:
        if user.SendInput(1, c.byref(up), c.sizeof(INPUT)) != 1:
            raise c.WinError(c.get_last_error())


class MONITORINFO(c.Structure):
    _fields_ = [
        ("cbSize", w.DWORD),
        ("rcMonitor", w.RECT),
        ("rcWork", w.RECT),
        ("dwFlags", w.DWORD),
    ]


signature(user, "GetMonitorInfoW", w.BOOL, w.HANDLE, c.POINTER(MONITORINFO))


def monitor(window):
    info = MONITORINFO(cbSize=c.sizeof(MONITORINFO))
    handle = user.MonitorFromWindow(hwnd(window), 2)
    if not user.GetMonitorInfoW(handle, c.byref(info)):
        raise c.WinError(c.get_last_error())

    def rect(r):
        return (r.left, r.top, r.right - r.left, r.bottom - r.top)

    return rect(info.rcMonitor), rect(info.rcWork)


def geometry(window, x, y, width, height, fullscreen):
    target = hwnd(window.window)
    style = user.GetWindowLongW(target, -16)
    ex = user.GetWindowLongW(target, -20)
    if not hasattr(window, "original_styles"):
        window.original_styles = (style, ex)
    style, ex = window.original_styles
    if fullscreen:
        style &= ~(0x00C00000 | 0x00040000)  # caption / thick frame
        ex &= ~(0x100 | 0x200 | 0x1)
    for index, value in ((-16, style), (-20, ex)):
        c.set_last_error(0)
        user.SetWindowLongW(target, index, value)
        if c.get_last_error():
            raise c.WinError(c.get_last_error())
    rect = w.RECT(0, 0, width, height)
    if not user.AdjustWindowRectEx(
        c.byref(rect), style, bool(user.GetMenu(target)), ex
    ):
        raise c.WinError(c.get_last_error())
    if not user.SetWindowPos(
        target,
        None,
        x,
        y,
        rect.right - rect.left,
        rect.bottom - rect.top,
        0x20 | 0x4 | 0x10,
    ):
        raise c.WinError(c.get_last_error())


class Backing:
    def __init__(self, window, rect):
        self.target = hwnd(window.window)
        self.handle = user.CreateWindowExW(
            0x08000080,
            "STATIC",
            "Boshy Randomizer presentation backing",
            0x80000000 | 4,
            *rect,
            None,
            None,
            None,
            None,
        )
        if not self.handle:
            raise c.WinError(c.get_last_error())
        self.shown = False

    def tick(self):
        msg = w.MSG()
        while user.PeekMessageW(c.byref(msg), self.handle, 0, 0, 1):
            user.TranslateMessage(c.byref(msg))
            user.DispatchMessageW(c.byref(msg))
        focused = user.GetForegroundWindow() == self.target
        if focused:
            user.SetWindowPos(
                self.handle, self.target, 0, 0, 0, 0, 0x1 | 0x2 | 0x10 | 0x40
            )
        elif self.shown:
            user.ShowWindow(self.handle, 0)
        self.shown = focused

    def close(self):
        if self.handle:
            user.DestroyWindow(self.handle)
            self.handle = None
