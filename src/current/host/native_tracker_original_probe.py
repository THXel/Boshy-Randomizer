"""Original unmodified Boshy menu detection; never starts or resets a speedrun."""

import json
import os
import subprocess
import time
import urllib.request
from pathlib import Path
from native_tracker_probe import status
from native_tracker_pickup_probe import obs_capture, OUT
from menu_host.processes import games


def main():
    assert not games()
    cfg = json.load(urllib.request.urlopen("http://127.0.0.1:8801/boshy/status"))[
        "config"
    ]
    folder = Path(cfg["game_dir"])
    exe = folder / "I Wanna Be The Boshy.exe"
    report = dict(scope=__doc__, game=str(exe), before=status(), keys_sent=[])
    assert not report["before"]["game_running"] and not report["before"].get(
        "native_tracker"
    )
    before = set(subprocess.check_output(["wmctrl", "-lp"], text=True).splitlines())
    log = (OUT / "original-runtime.log").open("w")
    proc = subprocess.Popen(
        [cfg["wine_executable"], str(exe)],
        cwd=folder,
        env={**os.environ, "WINEPREFIX": cfg["wine_prefix"], "WINEDEBUG": "-all"},
        stdout=log,
        stderr=log,
        start_new_session=True,
    )
    windows = []
    try:
        end = time.monotonic() + 35
        while time.monotonic() < end:
            s = status()
            rows = subprocess.check_output(["wmctrl", "-lp"], text=True).splitlines()
            windows = [
                r.split()[0]
                for r in rows
                if r not in before and r.endswith("I Wanna Be The Boshy")
            ]
            if s["game_running"] and s["reader_ok"] and windows:
                break
            time.sleep(0.3)
        else:
            raise AssertionError("Original process was not detected")
        assert not s.get("native_tracker") and s["display_mode"] != "randomizer", s
        assert s["run_status"] == "idle", s
        report["original_detected"] = s
        time.sleep(2)
        obs_capture("obs-original-speedrun")
        report["passed"] = True
    except BaseException as exc:
        report["error"] = repr(exc)
        raise
    finally:
        for w in windows:
            subprocess.run(["wmctrl", "-ic", w], check=True)
        if not windows and proc.poll() is None:
            proc.terminate()
        end = time.monotonic() + 10
        while time.monotonic() < end:
            if not status()["game_running"]:
                break
            time.sleep(0.2)
        report["after_close"] = status()
        log.close()
        (OUT / "original-live-results.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    assert not report["after_close"]["game_running"]
    print("PASS original Boshy automatic detection, no run started", flush=True)


if __name__ == "__main__":
    main()
