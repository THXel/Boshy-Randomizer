"""Real chest collisions across two seeds in one game process.

Only save-position fixtures are set before launch. Native pickup, image loading,
death, respawn and save writes run normally; process memory is read-only.
"""

import json, time, uuid
from functools import partial
from export_route_probe import ROOT
from export_native_run import export
from menu_host.store import Store, save, digest
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu.builds import DYNAMIC_SHA
from native_menu_probe import key, pump
from native_menu_lifecycle_probe import wait_for
from native_pickups_live import player
from native_rewards_live import write_save, chest_ids
from gameplay.runtime_reward_icons import icons
from menu_host.processes import games
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-DynamicAssets-20261025"


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, memory_writes=0, cases=[])
    s = Store(
        OUT / ("profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    with s.lock():
        for slot, seed in [(1, "0000001D"), (2, "ABCDEF12")]:
            d = Draft()
            d.update(
                level_pool=["save1.ini"],
                level_count=1,
                boss_pool=[],
                route_boss_count=0,
                items=True,
                god_mode=True,
                no_mouse_ghost=True,
                quiet_pickups=True,
                fast_chests=False,
                start_character="Kirby",
            )
            d.seed = seed
            s.create(slot, d)
            cfg = save(s.folder(slot) / "SaveFile1.ini")
            cfg["Positions"]["xpos"] = "3590"
            cfg["Positions"]["ypos"] = "804"
            write_save(s.folder(slot) / "SaveFile1.ini", cfg)
        original = {slot: digest(s.folder(slot) / "SaveFile1.ini") for slot in (1, 2)}
        c = CombinedController(s, dynamic=True)
        try:
            c.open()
            c.enter()
            pump(c, 0.5)
            identity = (c.window.pid, c.window.window)
            for slot in (1, 2):
                while c.model.slot < slot:
                    key(c, "Right")
                    pump(c, 0.2)
                plan = json.loads((s.folder(slot) / "plan.json").read_text())
                reward = plan["rewards"]["I00A4"]
                case = dict(slot=slot, seed=plan["seed"], reward=reward, screenshots=[])
                report["cases"].append(case)
                expected = icons()[reward["name"]][0]
                expected.save(OUT / f"slot-{slot}-expected-icon.png")
                key(c, "Return")
                wait_for(c, lambda: c.phase == "playing")
                assert identity == (c.window.pid, c.window.window) and len(games()) == 1
                started = time.monotonic()
                next_capture = 230
                while time.monotonic() - started < 15:
                    pump(c, 0.04)
                    obs = player(c.window)
                    if obs["timer"] >= next_capture:
                        name = f"slot-{slot}-reveal-{next_capture}"
                        capture.snap(c.window, name)
                        case["screenshots"].append(name + ".png")
                        next_capture += 15
                    if (
                        "Active 54" not in chest_ids(c.window)
                        and not obs["pickup_active"]
                    ):
                        case["released"] = True
                        break
                assert case.get("released"), player(c.window)
                assert case["screenshots"], case
                c.window.key("q")
                pump(c, 0.8)
                c.window.key("r")
                pump(c, 0.7)
                assert "Active 54" not in chest_ids(c.window)
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu" and not s.active)
                cfg = save(s.folder(slot) / "SaveFile1.ini")
                assert cfg.getint("RandoChecks", "I00A4") == 1
                profile = save(
                    s.folder(slot)
                    / (
                        "onlineLicense.ini"
                        if reward["kind"] == "character"
                        else "SaveFile1.ini"
                    )
                )
                assert (
                    profile.getint(
                        (
                            "Unlockables"
                            if reward["kind"] == "character"
                            else "Collectables"
                        ),
                        reward["name"],
                    )
                    == 1
                )
                if slot == 1:
                    assert digest(s.folder(2) / "SaveFile1.ini") == original[2]
                c.enter()
                pump(c, 0.5)
                key(c, "Return")
                wait_for(c, lambda: c.phase == "playing")
                pump(c, 0.8)
                assert "Active 54" not in chest_ids(c.window)
                assert identity == (c.window.pid, c.window.window)
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu" and not s.active)
                c.enter()
                pump(c, 0.5)
                assert digest(s.folder(slot) / "Boshy.exe") == DYNAMIC_SHA
                case.update(
                    receipt=True,
                    reward_saved=True,
                    death_respawn=True,
                    resume_without_duplicate=True,
                    same_process=True,
                )
                print("PASS", slot, reward, flush=True)
            assert report["cases"][0]["reward"] != report["cases"][1]["reward"]
            report.update(
                passed=True, identity=identity, events=c.events, exe_sha256=DYNAMIC_SHA
            )
        except BaseException as error:
            report["error"] = repr(error)
            try:
                capture.snap(c.window, "failure")
            except Exception:
                pass
            raise
        finally:
            try:
                c.close()
            finally:
                (OUT / "live-results.json").write_text(
                    json.dumps(report, indent=2) + "\n"
                )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
