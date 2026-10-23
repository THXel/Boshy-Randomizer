"""Typed Win32 calls used by the native Windows transport."""

import ctypes as c
from ctypes import wintypes as w

user = c.WinDLL('user32', use_last_error=True)
kernel = c.WinDLL('kernel32', use_last_error=True)
for name, restype, args in [
    ('GetForegroundWindow', w.HWND, []),
    ('GetAncestor', w.HWND, [w.HWND, w.UINT]),
    ('GetWindowThreadProcessId', w.DWORD, [w.HWND, c.POINTER(w.DWORD)]),
    ('IsWindow', w.BOOL, [w.HWND]),
    ('IsWindowVisible', w.BOOL, [w.HWND]),
    ('PostMessageW', w.BOOL, [w.HWND, w.UINT, w.WPARAM, w.LPARAM]),
    ('GetClientRect', w.BOOL, [w.HWND, c.POINTER(w.RECT)]),
    ('ClientToScreen', w.BOOL, [w.HWND, c.POINTER(w.POINT)]),
    (
        'SetWindowPos',
        w.BOOL,
        [w.HWND, w.HWND, c.c_int, c.c_int, c.c_int, c.c_int, w.UINT],
    ),
    ('GetAsyncKeyState', c.c_short, [c.c_int]),
    ('GetWindowLongW', w.LONG, [w.HWND, c.c_int]),
    ('SetWindowLongW', w.LONG, [w.HWND, c.c_int, w.LONG]),
]:
    f = getattr(user, name)
    f.restype = restype
    f.argtypes = args


def pid(hwnd):
    value = w.DWORD()
    user.GetWindowThreadProcessId(hwnd, c.byref(value))
    return value.value


def client_rect(hwnd):
    rect = w.RECT()
    point = w.POINT()
    if not user.GetClientRect(hwnd, c.byref(rect)) or not user.ClientToScreen(
        hwnd, c.byref(point)
    ):
        raise RuntimeError('Game rectangle unavailable')
    return point.x, point.y, rect.right, rect.bottom


_KEYS = {
    'Return': 13,
    'Escape': 27,
    'Left': 37,
    'Up': 38,
    'Right': 39,
    'Down': 40,
    'space': 32,
    'Tab': 9,
    'BackSpace': 8,
    'Delete': 46,
    'Control_L': 17,
    'Control_R': 17,
    'Alt_L': 18,
    'Alt_R': 18,
    'Shift_L': 16,
}


def vk(name):
    if name in _KEYS:
        return _KEYS[name]
    if name.startswith('F') and name[1:].isdigit():
        return 111 + int(name[1:])
    if len(name) == 1:
        return ord(name.upper())
    raise ValueError('Unknown key ' + name)


def key_down(name):
    return bool(user.GetAsyncKeyState(vk(name)) & 0x8000)


class KEYBDINPUT(c.Structure):
    _fields_ = [
        ('wVk', w.WORD),
        ('wScan', w.WORD),
        ('dwFlags', w.DWORD),
        ('time', w.DWORD),
        ('dwExtraInfo', c.c_size_t),
    ]


class MOUSEINPUT(c.Structure):
    _fields_ = [
        ('dx', w.LONG),
        ('dy', w.LONG),
        ('mouseData', w.DWORD),
        ('dwFlags', w.DWORD),
        ('time', w.DWORD),
        ('dwExtraInfo', c.c_size_t),
    ]


class UNION(c.Union):
    _fields_ = [('ki', KEYBDINPUT), ('mi', MOUSEINPUT)]


class INPUT(c.Structure):
    _anonymous_ = ('u',)
    _fields_ = [('type', w.DWORD), ('u', UNION)]


user.SendInput.argtypes = [w.UINT, c.POINTER(INPUT), c.c_int]
user.SendInput.restype = w.UINT


def send_key(name, down):
    key = vk(name)
    flags = (0 if down else 2) | (1 if key in (37, 38, 39, 40, 46) else 0)
    event = INPUT(type=1, ki=KEYBDINPUT(key, 0, flags, 0, 0))
    if user.SendInput(1, c.byref(event), c.sizeof(INPUT)) != 1:
        raise RuntimeError('Windows input rejected')


def module_base(process_id, name):
    class MODULE(c.Structure):
        _fields_ = [
            ('dwSize', w.DWORD),
            ('th32ModuleID', w.DWORD),
            ('th32ProcessID', w.DWORD),
            ('GlblcntUsage', w.DWORD),
            ('ProccntUsage', w.DWORD),
            ('modBaseAddr', c.c_void_p),
            ('modBaseSize', w.DWORD),
            ('hModule', w.HMODULE),
            ('szModule', w.WCHAR * 256),
            ('szExePath', w.WCHAR * 260),
        ]

    kernel.CreateToolhelp32Snapshot.argtypes = [w.DWORD, w.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = w.HANDLE
    kernel.Module32FirstW.argtypes = kernel.Module32NextW.argtypes = [
        w.HANDLE,
        c.POINTER(MODULE),
    ]
    kernel.CloseHandle.argtypes = [w.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(0x18, process_id)
    if handle == c.c_void_p(-1).value:
        raise OSError(c.get_last_error(), 'Module snapshot failed')
    try:
        row = MODULE()
        row.dwSize = c.sizeof(row)
        ok = kernel.Module32FirstW(handle, c.byref(row))
        while ok:
            if row.szModule.casefold() == name.casefold():
                return row.modBaseAddr
            ok = kernel.Module32NextW(handle, c.byref(row))
    finally:
        kernel.CloseHandle(handle)
    return None
