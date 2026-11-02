"""Real Hello Kitty fight after a genuinely collected Target item.

Only the closed save's boss entry position/station is staged. The fight uses
native God Mode, one-hit phases, autofire and ordinary input. No boss HP, phase,
receipt, projectile or runtime position writes are performed.
"""

import json, time
from menu_host.store import Store, save
from menu_host.runtime import Runtime
from native_targets_live import OUT, hold, state, wait
from native_rewards_live import write_save
from native_menu.observe import objects
from gameplay import target_plan as target
from transition.router import STAGES, GROUP as ROUTE
from god_mode_boss_probe import values
import god_mode_live as capture

capture.OUT = OUT


def main():
    reports = json.loads(
        (OUT / "live-pickup-gated-pickup-finale-collect-finale.json").read_text()
    )
    source = next(c for c in reports["cases"] if c["name"] == "pickup-gated")
    folder = __import__("pathlib").Path(source["folder"])
    roots = [
        p.parent
        for p in OUT.glob("pickup-gated-*/slot-1.json")
        if json.loads(p.read_text())["run"] == folder.name
    ]
    assert len(roots) == 1
    s = Store(roots[0])
    case = dict(scope=__doc__, folder=str(folder), memory_writes=0, samples=[])
    with s.lock():
        r = Runtime(s)
        try:
            c = save(folder / "SaveFile1.ini")
            stage = STAGES["boss1.ini"]
            assert c.getint("Collectables", "Lalalalalala CD") == 1
            assert c.getint(ROUTE, "Done1") == 0
            c[ROUTE]["CurrentStage"] = str(stage["id"])
            for key, f in [("frame", "frame"), ("xpos", "x"), ("ypos", "y")]:
                c["Positions"][key] = str(stage[f])
            write_save(folder / "SaveFile1.ini", c)
            r.start(1)
            time.sleep(0.5)
            capture.snap(r, "target-kitty-entry")
            r.key("s")
            hold(r, "Right", 0.08)
            # Autofire is already a seed option; X is held for the actual fight.
            import subprocess

            subprocess.run(["xdotool", "keydown", "x"], check=True)
            start = time.monotonic()
            seen = False
            dead = False
            while time.monotonic() - start < 95:
                obs = objects(r.reader)
                boss = next((o for o in obs if o["name"] == "hellokitty"), None)
                if boss:
                    seen = True
                    hp = values(r.reader, boss, 3)[1]
                    case["samples"].append(
                        dict(
                            t=round(time.monotonic() - start, 2),
                            hp=hp,
                            x=boss["x"],
                            y=boss["y"],
                        )
                    )
                    if hp <= 0:
                        dead = True
                        break
                elif seen:
                    dead = True
                    break
                time.sleep(0.2)
            subprocess.run(["xdotool", "keyup", "x"], check=True)
            assert seen and dead, case["samples"][-4:]
            case["boss_defeated"] = True
            capture.snap(r, "target-kitty-defeated")
            # Remain on the starting platform until the native bridge has formed.
            # God Mode cannot land a player who walked off before its creation.
            time.sleep(30)
            capture.snap(r, "target-kitty-bridge-ready")
            print(
                "BRIDGE",
                [
                    dict(x=o["x"], y=o["y"])
                    for o in objects(r.reader)
                    if o["name"] == "Player"
                ],
                flush=True,
            )
            # Walk through the normal exit after the native victory animation.
            for attempt in range(12):
                if state(folder)["ready"]:
                    break
                subprocess.run(["xdotool", "keydown", "Right"], check=True)
                try:
                    r.key("Shift_L")
                    r.key("z")
                    time.sleep(0.45)
                finally:
                    subprocess.run(["xdotool", "keyup", "Right"], check=True)
                case.setdefault("walk", []).append(
                    [
                        dict(name=o["name"], x=o["x"], y=o["y"])
                        for o in objects(r.reader)
                        if o["name"] == "Player"
                    ]
                )
                time.sleep(0.3)
            wait(lambda: state(folder)["ready"] == 1)
            wait(lambda: r.reader.frame() == "Eleventh Boss - Solgryn")
            case["arrival"] = state(folder)
            assert case["arrival"]["done"]["done1"] == "1"
            assert case["arrival"]["stage"] == STAGES[target.FINAL]["id"]
            assert case["arrival"]["visit"] == 1 and not case["arrival"]["completed"]
            capture.snap(r, "target-last-boss-solgryn")
            r.key("q")
            time.sleep(0.6)
            r.key("r")
            time.sleep(0.5)
            r.close("target-boss-death")
            r.start(1)
            time.sleep(0.4)
            case["resume"] = state(folder)
            for key in ("ready", "visit", "stage", "done", "items", "completed"):
                assert case["resume"][key] == case["arrival"][key]
            r.close("target-boss-finished")
            case["passed"] = True
            print("PASS target real boss", flush=True)
        except BaseException as error:
            case["error"] = repr(error)
            try:
                capture.snap(r, "target-boss-failure")
            except Exception:
                pass
            raise
        finally:
            import subprocess

            subprocess.run(["xdotool", "keyup", "x", "Left", "Right"])
            if s.active:
                r.close("target-boss-cleanup")
            (OUT / "boss-live-results.json").write_text(
                json.dumps(case, indent=2) + "\n"
            )


if __name__ == "__main__":
    main()
