"""Exclusive process locks and durable writes on Linux and Windows."""

import os
import time
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def lock_file(path):
    path = Path(path)
    if path.is_symlink():
        raise ValueError("Linked lock file")
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt

            stream.seek(0, os.SEEK_END)
            if stream.tell() == 0:
                stream.write(b"0")
                stream.flush()
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield stream
        finally:
            if os.name == "nt":
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def sync_directory(path):
    # Windows does not expose directories through os.open/fsync. File contents
    # are flushed before replacement; use the native write-through move below.
    if os.name != "nt":
        fd = os.open(path, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)


def _retry_windows_move(move, source, destination, *, timeout=2.0):
    """Keep the old file intact while a native reader briefly holds it open."""
    end = time.monotonic() + timeout
    while True:
        try:
            move(source, destination)
            return
        except OSError as error:
            if (
                getattr(error, "winerror", None) not in (5, 32, 33)
                or time.monotonic() >= end
            ):
                raise
            time.sleep(0.02)


def replace(source, destination):
    if os.name != "nt":
        os.replace(source, destination)
    else:
        import ctypes
        from ctypes import wintypes as w

        api = ctypes.WinDLL("kernel32", use_last_error=True)
        api.MoveFileExW.argtypes = (w.LPCWSTR, w.LPCWSTR, w.DWORD)
        api.MoveFileExW.restype = w.BOOL

        def move(source, destination):
            if not api.MoveFileExW(str(source), str(destination), 0x1 | 0x8):
                raise ctypes.WinError(ctypes.get_last_error())

        _retry_windows_move(move, source, destination)
    sync_directory(Path(destination).parent)
