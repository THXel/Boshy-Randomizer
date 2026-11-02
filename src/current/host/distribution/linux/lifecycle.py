"""Wait for real Lutris registration and the owned game's X11 window."""

import fcntl
import os
import sqlite3
import subprocess
import time
from pathlib import Path


def wait_registration(lookup, progress, timeout=900):
    deadline = time.monotonic() + timeout
    while True:
        progress("registration", 0, 0)
        game_id = lookup()
        if game_id is not None:
            return str(game_id)
        if time.monotonic() >= deadline:
            raise TimeoutError("registration")
        time.sleep(0.4)


def game_prefix(data, game_id):
    """Respect the selected Lutris entry, including a user's custom prefix."""
    import yaml

    with sqlite3.connect(
        (data / "lutris/pga.db").as_uri() + "?mode=ro", uri=True
    ) as db:
        row = db.execute(
            "SELECT configpath FROM games WHERE id=? AND installed=1", (int(game_id),)
        ).fetchone()
    if not row or not row[0] or Path(row[0]).name != row[0]:
        raise ValueError("Invalid Lutris configuration")
    config_home = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    config = yaml.safe_load(
        (config_home / "lutris/games" / (row[0] + ".yml")).read_text()
    )
    return Path(config["game"]["prefix"]).expanduser().resolve(strict=True)


def owned_window(prefix, *, proc=Path("/proc")):
    try:
        result = subprocess.run(
            ["wmctrl", "-lp"], capture_output=True, text=True, timeout=5
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode:
        return None  # Window-manager snapshots can fail briefly during startup.
    for line in result.stdout.splitlines():
        fields = line.split(None, 4)
        if len(fields) < 5 or "boshy" not in fields[4].lower():
            continue
        try:
            process = proc / str(int(fields[2]))
            cwd = (process / "cwd").resolve(strict=True)
            relative = cwd.relative_to(prefix)
            # Original Boshy and the setup dialog are not a ready Randomizer.
            if "BoshyRandomizer" in relative.parts and "runs" in relative.parts:
                return fields[0]
        except (OSError, ValueError):
            continue  # A window/process may disappear between both snapshots.
    return None


def launch_game(data, base, game_id, progress, timeout=90):
    prefix = game_prefix(data, game_id)
    base.mkdir(parents=True, exist_ok=True)
    deadline = time.monotonic() + timeout
    # Serialize concurrent shortcuts until the first game window is available.
    with (base / ".launch.lock").open("a") as lock:
        while True:
            progress("launching", 0, 0)
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("launching")
                time.sleep(0.2)
        child = None
        (base / "evidence").mkdir(exist_ok=True)
        with (base / "evidence/game-launch.log").open("a") as log:
            while True:
                progress("launching", 0, 0)
                window = owned_window(prefix)
                if window:
                    subprocess.run(["wmctrl", "-ia", window], check=False, timeout=5)
                    return
                if child is None:
                    child = subprocess.Popen(
                        ["lutris", "lutris:rungameid/" + str(game_id)],
                        stdout=log,
                        stderr=log,
                        start_new_session=True,
                    )
                code = child.poll()
                if code not in (None, 0):
                    raise RuntimeError("Lutris exited: " + str(code))
                if time.monotonic() >= deadline:
                    raise TimeoutError("launching")
                time.sleep(0.3)
