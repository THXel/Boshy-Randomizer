"""Identify private native games even before they create an X11 window.

This is an observation boundary, never a prefix-wide process termination list.
Only Boshy.exe processes whose working directory is a direct lab run are included.
"""

import os
from pathlib import Path
from menu_host.store import RUNS


def games(runs=RUNS, proc=Path("/proc")):
    if os.name == "nt":
        from platform_support.windows_api import games as native_games

        return native_games(runs)
    runs = Path(runs).resolve()
    found = {}
    for entry in proc.iterdir():
        if not entry.name.isdecimal():
            continue
        try:
            folder = Path(os.readlink(entry / "cwd")).resolve()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        if folder.parent != runs:
            continue
        try:
            # The final ')' handles spaces and parentheses in Linux process names.
            state = (entry / "stat").read_text().rsplit(")", 1)[1].split()[0]
            if state in ("Z", "X"):
                continue
            args = (entry / "cmdline").read_bytes().split(b"\0")
            names = [
                arg.replace(b"\\", b"/").rsplit(b"/", 1)[-1].lower() for arg in args
            ]
            if b"boshy.exe" in names:
                found[int(entry.name)] = folder
        except (FileNotFoundError, ProcessLookupError):
            continue
    return found
