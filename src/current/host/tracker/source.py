"""Read-only schema-2 source. A stopped or expired game is never a live run."""

import json
import math
import os
import time
from pathlib import Path

MODES = {"randomizer", "target", "normal", "boss_rush", "level_rush", "menu"}
ROWS = ("items", "characters", "bosses", "goals", "route_stages")


def feed_path():
    base = (
        Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        if os.name == "nt"
        else Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    )
    return base / "boshy-randomizer/live.json"


def process(pid, start):
    if type(pid) is not int or pid <= 0 or not start:
        return None
    proc = Path("/proc") / str(pid)
    if proc.stat().st_uid != os.getuid():
        return None
    fields = (proc / "stat").read_text().rsplit(")", 1)[1].split()
    return proc if fields[0] not in ("Z", "X") and fields[19] == str(start) else None


def alive(data):
    if os.name == "nt":
        from tracker.windows_process import alive as windows_alive

        return windows_alive(data)
    host = process(data.get("host_pid"), data.get("host_start"))
    game = process(data.get("game_pid"), data.get("game_start"))
    if (
        not host
        or not game
        or (game / "cwd").resolve() != Path(data["game_dir"]).resolve()
    ):
        return False
    names = [
        arg.replace(b"\\", b"/").rsplit(b"/", 1)[-1].lower()
        for arg in (game / "cmdline").read_bytes().split(b"\0")
    ]
    return b"boshy.exe" in names


def read_feed(path=None, *, now=None, check_process=True):
    try:
        path = Path(path) if path is not None else feed_path()
        with path.open("rb") as stream:
            raw = stream.read(262145)
        if len(raw) > 262144:
            return None
        data = json.loads(raw)
        if not isinstance(data, dict):
            return None
        age = (time.time() if now is None else now) - float(data["updated_at"])
        if (
            data.get("schema") != 2
            or data.get("producer") != "boshy-fusion"
            or data.get("application") != "boshy-randomizer"
            or not 0 <= age <= 8
            or data.get("game_running") is not True
            or data.get("mode") not in ("menu", "randomizer", "target")
            or data.get("play_mode") not in MODES
        ):
            return None
        if data["mode"] != "menu":
            run = data.get("run_id")
            if (
                not isinstance(run, str)
                or len(run) != 32
                or any(c not in "0123456789abcdef" for c in run)
                or type(data.get("slot")) is not int
                or data["slot"] not in (1, 2, 3)
            ):
                return None
        for key in ROWS:
            rows = data.get(key, [])
            if (
                not isinstance(rows, list)
                or len(rows) > 64
                or any(
                    not isinstance(row, dict)
                    or not isinstance(row.get("name"), str)
                    or len(row["name"]) > 200
                    or type(row.get("done")) is not bool
                    for row in rows
                )
            ):
                return None
        for key in ("elapsed", "deaths", "route_index", "checks_done", "checks_total"):
            if (
                not math.isfinite(float(data.get(key, 0)))
                or float(data.get(key, 0)) < 0
            ):
                return None
        if check_process and not alive(data):
            return None
        return data
    except (OSError, ValueError, KeyError, TypeError, OverflowError, IndexError):
        return None
