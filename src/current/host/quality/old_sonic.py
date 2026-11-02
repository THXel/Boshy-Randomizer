"""Full Old Sonic attempt using ordinary movement/shooting and native God Mode."""

import json
import subprocess
import time
import uuid
from functools import partial
from pathlib import Path
from menu_host.store import Store, save
from menu_host.draft import Draft
from export_native_run import export
from native_menu.combined import CombinedController
from native_menu.observe import objects
from native_menu_probe import pump
from native_classic_live import wait
from god_mode_boss_probe import values
from transition.router import GROUP
from native_menu.builds import DYNAMIC_SHA
import god_mode_live as capture


def run(output):
    output = Path(output)
    capture.OUT = output
    report = {
        "game_sha256": DYNAMIC_SHA,
        "memory_writes": 0,
        "passed": False,
        "samples": [],
    }
    store = Store(
        output / ("oldsonic-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    with store.lock():
        d = Draft()
        d.set_mode("boss_rush")
        d.update(
            boss_pool=["oldsonic"],
            route_boss_count=1,
            level_pool=[],
            level_count=0,
            god_mode=True,
            autofire=True,
            no_mouse_ghost=True,
            sprite_scenery=True,
            sprite_backgrounds=True,
            sprite_tiles=True,
            sprite_decor=True,
            sprite_actors=True,
        )
        d.seed = "OLD-SONIC-NATURAL-39"
        store.create(1, d)
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            c.model.slot = 1
            c.model.load_slot()
            c.begin()
            wait(c, lambda: c.phase == "playing")
            subprocess.run(["wmctrl", "-ia", c.window.window], check=True)
            subprocess.run(["xdotool", "keydown", "x"], check=True)
            start = time.monotonic()
            last = -1
            while time.monotonic() - start < 360:
                pump(c, 0.25)
                cfg = save(c.folder / "SaveFile1.ini")
                if cfg.getint(GROUP, "Done14", fallback=0):
                    report["native_exit"] = True
                    report["arrival"] = dict(cfg[GROUP])
                    break
                try:
                    obs = objects(c.window.reader)
                except RuntimeError:
                    continue  # Frame structures are absent during a native jump.
                player = next((o for o in obs if o["name"] == "Player"), None)
                if player is None:
                    continue  # Read the native route receipt again after the jump.
                boss = next((o for o in obs if o["name"] == "Active 4sonic"), None)
                # Stay on the central landing area. Brief ordinary taps aim shots.
                if player["y"] < 500 and (player["x"] < 280 or player["x"] > 360):
                    c.window.key("Right" if player["x"] < 320 else "Left")
                elif boss and player["y"] < 500:
                    c.window.key("Right" if boss["x"] > player["x"] else "Left")
                second = int(time.monotonic() - start)
                if second // 15 != last:
                    last = second // 15
                    sample = {
                        "seconds": second,
                        "frame": c.window.reader.frame(),
                        "player": {"x": player["x"], "y": player["y"]},
                        "sonic": [
                            {
                                "name": o["name"],
                                "x": o["x"],
                                "y": o["y"],
                                "values": values(c.window.reader, o, 8),
                            }
                            for o in obs
                            if o["name"] == "Active 4sonic"
                        ],
                    }
                    report["samples"].append(sample)
                    print(json.dumps(sample), flush=True)
                    capture.snap(c.window, "oldsonic-" + str(last))
            subprocess.run(["xdotool", "keyup", "x"], check=True)
            if report.get("native_exit"):
                pump(c, 1)
                report["arrival_frame"] = c.window.reader.frame()
                c.window.key("q")
                pump(c, 0.8)
                assert not any(o["name"] == "Player" for o in objects(c.window.reader))
                c.window.key("r")
                pump(c, 1)
                assert any(o["name"] == "Player" for o in objects(c.window.reader))
                report["arrival_death_retry"] = True
                report["passed"] = True
            else:
                report["limitation"] = (
                    "Ordinary-input attempt did not complete within six minutes; no victory or exit was forced."
                )
        finally:
            subprocess.run(["xdotool", "keyup", "x", "Left", "Right"], check=True)
            c.close()
            (output / "old-sonic.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    import sys

    run(Path(sys.argv[1]))
