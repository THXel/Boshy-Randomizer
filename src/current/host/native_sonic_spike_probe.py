"""Natural Sonic death without God Mode after platform knockback; no memory writes."""

import json
import time
import uuid
import subprocess
from functools import partial
from native_menu import builds
from menu_host.store import digest

builds.DYNAMIC_BASE = builds.PREFIX / "drive_c/BoshyTransitions/Boshy-dynamic-v16.exe"
builds.DYNAMIC_SHA = digest(builds.DYNAMIC_BASE)
from export_native_run import export
from export_route_probe import ROOT
from menu_host.store import Store
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu_probe import pump
from native_menu_lifecycle_probe import wait_for
import native_death_visual_probe as screenshots
import god_mode_live as capture


def main():
    out = ROOT / "outputs/Fusion-SonicFollowup-20261025/no-god"
    out.mkdir(parents=True, exist_ok=True)
    screenshots.OUT = capture.OUT = out
    store = Store(
        out / ("profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    report = dict(
        memory_writes=0, god_mode=False, game_sha256=builds.DYNAMIC_SHA, samples=[]
    )
    with store.lock():
        draft = Draft()
        draft.set_mode("boss_rush")
        draft.update(
            boss_pool=["sonic"],
            route_boss_count=1,
            skip_intro=True,
            god_mode=False,
            no_mouse_ghost=True,
            start_character="Boshy",
            sprite_scenery=True,
            sprite_backgrounds=True,
            sprite_decor=True,
            sprite_tiles=True,
            sprite_actors=True,
        )
        draft.seed = "SHAKE025"
        store.create(1, draft)
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            c.model.slot = 1
            c.model.load_slot()
            c.begin()
            wait_for(c, lambda: c.phase == "playing", seconds=35)
            pump(c, 0.6)
            subprocess.run(["xdotool", "keydown", "Right"], check=True)
            try:
                wait_for(
                    c,
                    lambda: next(
                        o
                        for o in capture.objects(c.window.reader)
                        if o["name"] == "Player"
                    )["x"]
                    >= 310,
                    seconds=5,
                )
            finally:
                subprocess.run(["xdotool", "keyup", "Right"], check=True)
            start = time.monotonic()
            died = False
            while time.monotonic() - start < 70:
                pump(c, 0.05)
                players = [
                    o for o in capture.objects(c.window.reader) if o["name"] == "Player"
                ]
                if not players:
                    died = True
                    break
                player = players[0]
                report["samples"].append(
                    dict(
                        t=round(time.monotonic() - start, 3),
                        x=player["x"],
                        y=player["y"],
                    )
                )
            assert died, "No natural death observed"
            report["minimum_y"] = min(s["y"] for s in report["samples"])
            report["death_after_seconds"] = round(time.monotonic() - start, 3)
            pump(c, 0.5)
            screenshots.snapshot(c, "sonic-natural-death")
            c.window.key("r")
            pump(c, 0.7)
            assert any(o["name"] == "Player" for o in capture.objects(c.window.reader))
            screenshots.snapshot(c, "sonic-respawn")
            c.window.key("F2")
            wait_for(c, lambda: c.phase == "menu", seconds=30)
            report["death_retry_menu"] = True
            report["completed"] = True
            print(
                "NATURAL DEATH",
                report["minimum_y"],
                report["death_after_seconds"],
                flush=True,
            )
        except BaseException as e:
            report["error"] = repr(e)
            raise
        finally:
            c.close()
            (out / "results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
