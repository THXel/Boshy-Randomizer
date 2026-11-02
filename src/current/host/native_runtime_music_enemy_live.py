"""Native Ninja Gaiden enemy kill with continuous music; closed-save position fixture.

Only an isolated save's checkpoint is positioned before launch. Movement, shots,
enemy death and audio are native; no process-memory writes or forced kills.
"""

import json
import subprocess
import uuid
from functools import partial
from export_route_probe import ROOT
from export_native_run import export
from menu_host.store import Store, save
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu_probe import pump
from native_menu_lifecycle_probe import wait_for
from native_rewards_live import write_save
from native_runtime_music_live import audio_check
from native_embedded_blood_live import particles
from music import runtime
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-MusicFollowup-20261025"


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, memory_writes=0, checkpoint_fixture=dict(x=970, y=30))
    store = Store(
        OUT / ("enemy-profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    with store.lock():
        draft = Draft()
        draft.set_mode("level_rush")
        draft.update(
            level_pool=["save13.ini"],
            level_count=1,
            music=True,
            god_mode=True,
            autofire=True,
            no_mouse_ghost=True,
        )
        draft.select_pack("music_pack", "wannafest22")
        draft.select_pack("blood_pack", "kamilia3")
        draft.seed = "00009111"
        store.create(1, draft)
        cfg = save(store.folder(1) / "SaveFile1.ini")
        cfg["Positions"]["xpos"] = "970"
        cfg["Positions"]["ypos"] = "30"
        write_save(store.folder(1) / "SaveFile1.ini", cfg)
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            c.begin()
            wait_for(c, lambda: c.phase == "playing")
            pump(c, 1)
            rows = capture.objects(c.window.reader)
            player = next(o for o in rows if o["name"] == "Player")
            enemies = [
                o
                for o in rows
                if o["name"] == "Active 14"
                and 0 < player["x"] - o["x"] < 350
                and abs(o["y"] - player["y"]) < 75
            ]
            report["player"] = player
            report["enemies"] = enemies
            assert enemies, (player, [o for o in rows if o["name"] == "Active 14"])
            target = min(enemies, key=lambda o: abs(o["x"] - player["x"]))
            capture.snap(c.window, "ninja-enemy-before")
            plan = json.loads((store.folder(1) / "plan.json").read_text())
            track = next(
                row
                for row in plan["runtime_music_assets"]
                if row["cue"] == "NinjaGaiden (2)"
            )
            expected = (c.folder / runtime.DIRECTORY / track["file"]).read_bytes()

            def shoot():
                c.window.key("Left")
                subprocess.run(["wmctrl", "-ia", c.window.window], check=True)
                subprocess.run(["xdotool", "keydown", "x"], check=True)
                try:
                    pump(c, 1.2)
                finally:
                    subprocess.run(["xdotool", "keyup", "x"], check=True)
                now = capture.objects(c.window.reader)
                assert not any(
                    o["slot"] == target["slot"] and o["ptr"] == target["ptr"]
                    for o in now
                ), "Enemy survived shots"
                assert any(
                    o["name"] == "Player" and o["ptr"] == player["ptr"] for o in now
                ), "Player died"
                assert not any(
                    p["life"] > 0 for p in particles(c)
                ), "Enemy used player blood pack"
                report["native_kill"] = True
                capture.snap(c.window, "ninja-enemy-after")

            report["audio"] = audio_check(
                c, "ninja-enemy-continuity", expected, during=shoot
            )
            report.update(passed=True, track=track)
            print(
                json.dumps(
                    {"passed": True, "native_kill": True, "audio": report["audio"]}
                ),
                flush=True,
            )
        except BaseException as error:
            report["error"] = repr(error)
            raise
        finally:
            c.close()
            (OUT / "enemy-live-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )


if __name__ == "__main__":
    main()
