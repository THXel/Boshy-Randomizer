"""Owned Unicode Windows name dialog; the caller runs it off the game pump."""

import ctypes as C
from ctypes import wintypes as W
import struct


def ask(owner, title, prompt, accept, cancel, invalid, existing):
    from native_menu.presets import name, LIMIT

    user = C.WinDLL("user32", use_last_error=True)
    PROC = C.WINFUNCTYPE(C.c_ssize_t, W.HWND, W.UINT, W.WPARAM, W.LPARAM)
    user.DialogBoxIndirectParamW.argtypes = [
        W.HINSTANCE,
        C.c_void_p,
        W.HWND,
        PROC,
        W.LPARAM,
    ]
    user.DialogBoxIndirectParamW.restype = C.c_ssize_t
    user.EndDialog.argtypes = [W.HWND, C.c_ssize_t]
    user.GetDlgItem.argtypes = [W.HWND, C.c_int]
    user.GetDlgItem.restype = W.HWND
    user.GetDlgItemTextW.argtypes = [W.HWND, C.c_int, W.LPWSTR, C.c_int]
    user.SetDlgItemTextW.argtypes = [W.HWND, C.c_int, W.LPCWSTR]
    user.SendMessageW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user.SetFocus.argtypes = [W.HWND]
    result = []
    errors = []

    def wide(s):
        return (s + "\0").encode("utf-16le")

    # Modal dialog with a native edit field: IME, clipboard, Tab, Enter and Esc
    # are handled by Windows. No seed or run mutation happens in this thread.
    data = (
        struct.pack("<IIHhhhh", 0x80C808C0, 0, 4, 0, 0, 250, 91)
        + b"\0\0\0\0"
        + wide(title)
        + struct.pack("<H", 9)
        + wide("Segoe UI")
    )

    def item(style, x, y, w, h, ident, kind, label):
        nonlocal data
        data += bytes((-len(data)) % 4)
        data += (
            struct.pack("<IIhhhhH", style, 0, x, y, w, h, ident)
            + struct.pack("<HH", 0xFFFF, kind)
            + wide(label)
            + b"\0\0"
        )

    item(0x50000000, 10, 8, 230, 22, 101, 0x82, prompt)
    item(0x50810080, 10, 32, 230, 16, 100, 0x81, "")
    item(0x50010001, 106, 62, 64, 18, 1, 0x80, accept)
    item(0x50010000, 176, 62, 64, 18, 2, 0x80, cancel)

    @PROC
    def callback(hwnd, msg, wp, lp):
        try:
            if msg == 0x110:
                edit = user.GetDlgItem(hwnd, 100)
                user.SendMessageW(edit, 0xC5, LIMIT, 0)
                user.SetFocus(edit)
                return 0
            if msg == 0x10 or msg == 0x111 and wp & 0xFFFF == 2:
                user.EndDialog(hwnd, 0)
                return 1
            if msg == 0x111 and wp & 0xFFFF == 1:
                buf = C.create_unicode_buffer(LIMIT + 2)
                user.GetDlgItemTextW(hwnd, 100, buf, len(buf))
                try:
                    candidate = name(buf.value)
                    if candidate.casefold() in existing:
                        raise ValueError("Duplicate name")
                except ValueError:
                    user.SetDlgItemTextW(hwnd, 101, invalid)
                    user.SetFocus(user.GetDlgItem(hwnd, 100))
                    return 1
                result.append(candidate)
                user.EndDialog(hwnd, 1)
                return 1
        except BaseException as error:
            errors.append(error)
            user.EndDialog(hwnd, 0)
        return 0

    template = C.create_string_buffer(data)
    handle = int(owner, 0) if isinstance(owner, str) else owner
    status = user.DialogBoxIndirectParamW(None, template, handle, callback, 0)
    if errors:
        raise errors[0]
    if status == -1:
        raise C.WinError(C.get_last_error())
    return result[0] if result else None
