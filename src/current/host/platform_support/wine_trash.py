"""Wine path translation for the Linux desktop trash; no Unix command runner."""

import ctypes
import os
from pathlib import Path, PurePosixPath
from platform_support.trash_files import move_to_home_trash


def is_wine():
    try:
        return hasattr(ctypes.CDLL("ntdll.dll"), "wine_get_version")
    except OSError:
        return False


class Paths:
    def __init__(self):
        # Wine's two path helpers use CDECL and return process-heap buffers.
        self.api = ctypes.CDLL("kernel32.dll", use_last_error=True)
        self.heap = ctypes.WinDLL("kernel32.dll", use_last_error=True)
        self.heap.GetProcessHeap.argtypes = ()
        self.heap.GetProcessHeap.restype = ctypes.c_void_p
        self.heap.HeapFree.argtypes = (
            ctypes.c_void_p,
            ctypes.c_uint32,
            ctypes.c_void_p,
        )
        self.heap.HeapFree.restype = ctypes.c_int
        self.api.wine_get_unix_file_name.argtypes = (ctypes.c_wchar_p,)
        self.api.wine_get_unix_file_name.restype = ctypes.c_void_p
        self.api.wine_get_dos_file_name.argtypes = (ctypes.c_char_p,)
        self.api.wine_get_dos_file_name.restype = ctypes.c_void_p

    def translated(self, function, value, read):
        pointer = function(value)
        if not pointer:
            raise OSError("Wine could not translate the trash path")
        try:
            return read(pointer)
        finally:
            self.heap.HeapFree(self.heap.GetProcessHeap(), 0, pointer)

    def unix(self, path):
        return self.translated(
            self.api.wine_get_unix_file_name, str(path), ctypes.string_at
        )

    def windows(self, path):
        return self.translated(
            self.api.wine_get_dos_file_name,
            str(path).encode("utf-8"),
            ctypes.wstring_at,
        )


def trash_location(paths, environ):
    # Wine 11 exposes host XDG values under WINE_HOST_*; HOME is removed.
    data = environ.get("WINE_HOST_XDG_DATA_HOME") or environ.get("XDG_DATA_HOME", "")
    if not data.startswith("/"):
        home = environ.get("HOME", "")
        if not home.startswith("/"):
            wine_home = environ.get("WINEHOMEDIR", "")
            if not wine_home:
                raise OSError("Linux home directory unavailable; working copy retained")
            if wine_home.startswith("\\??\\"):
                wine_home = "\\\\?\\" + wine_home[4:]
            home = paths.unix(wine_home).decode("utf-8")
        if not home.startswith("/"):
            raise OSError("Invalid Linux home directory; working copy retained")
        data = home.rstrip("/") + "/.local/share"
    trash = PurePosixPath(data) / "Trash"
    if ".." in trash.parts:
        raise OSError("Ambiguous trash path; working copy retained")
    return trash


def recycle(path):
    paths = Paths()
    trash = trash_location(paths, os.environ)
    return move_to_home_trash(Path(path), Path(paths.windows(trash)), paths.unix(path))
