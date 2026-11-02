"""Same-frame route entry and rush resumes using closed-run save fixtures."""

import json, time, uuid, subprocess
from native_cycle_live import OUT, check, restart
from native_rewards_live import write_save
from menu_host.store import Store, save
from menu_host.draft import Draft
from menu_host.runtime import Runtime
from gameplay.cycle_plan import choose, initial
from transition.router import GROUP, STAGES
import god_mode_live as capture


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, memory_writes=0, cases=[])
    try:
        for mode in ("randomizer", "boss_rush", "level_rush"):
            s = Store(OUT / ("extra-" + mode + "-" + uuid.uuid4().hex[:6]))
            with s.lock():
                d = Draft()
                d.update(
                    level_pool=(
                        ["save2.ini", "save1.ini"]
                        if mode == "level_rush"
                        else ["save2.ini"]
                    ),
                    level_count=2 if mode == "level_rush" else 1,
                    boss_pool=(
                        ["kracko", "hellokitty"] if mode == "boss_rush" else ["kracko"]
                    ),
                    route_boss_count=2 if mode == "boss_rush" else 1,
                    characters=True,
                    god_mode=True,
                    no_mouse_ghost=True,
                )
                if mode != "randomizer":
                    d.set_mode(mode)
                d.seed = "12345678"
                s.create(1, d)
                folder = s.folder(1)
                p = json.loads((folder / "plan.json").read_text())
                case = dict(mode=mode, route=p["route"], folder=str(folder))
                report["cases"].append(case)
                r = Runtime(s)
                try:
                    first = initial(d.options, d.seed)
                    r.start(1)
                    case["initial"] = check(r, folder, first)
                    r.close("cycle-extra-initial")
                    c = save(folder / "SaveFile1.ini")
                    if mode == "randomizer":
                        assert (
                            STAGES[p["route"][0]]["frame"]
                            == STAGES[p["route"][1]]["frame"]
                            == 5
                        )
                        c["Positions"]["xpos"] = "3170"
                        c["Positions"]["ypos"] = "400"
                        write_save(folder / "SaveFile1.ini", c)
                        r.start(1)
                        subprocess.run(["wmctrl", "-ia", r.window], check=True)
                        subprocess.run(["xdotool", "keydown", "Right"], check=True)
                        try:
                            time.sleep(0.55)
                        finally:
                            subprocess.run(["xdotool", "keyup", "Right"], check=True)
                        end = time.monotonic() + 10
                        while time.monotonic() < end:
                            c = save(folder / "SaveFile1.ini")
                            if (
                                c.getint(GROUP, "CurrentStage")
                                == STAGES[p["route"][1]]["id"]
                            ):
                                break
                            time.sleep(0.1)
                        assert (
                            c.getint(GROUP, "CurrentStage")
                            == STAGES[p["route"][1]]["id"]
                        ), dict(c[GROUP])
                        case["entry"] = (
                            "real Kracko region crossing from position fixture"
                        )
                    else:
                        dest = STAGES[p["route"][1]]
                        c[GROUP]["CurrentStage"] = str(dest["id"])
                        for k, v in [
                            ("frame", dest["frame"]),
                            ("xpos", dest["x"]),
                            ("ypos", dest["y"]),
                        ]:
                            c["Positions"][k] = str(v)
                        write_save(folder / "SaveFile1.ini", c)
                        r.start(1)
                        case["entry"] = (
                            "synthetic saved destination, native choice on frame entry"
                        )
                    expected = choose(d.seed, 1, {}, first["name"])
                    case["arrival"] = check(r, folder, expected)
                    capture.snap(r, "extra-" + mode)
                    restart(r, s, folder, expected, case)
                    case["passed"] = True
                    print("PASS", mode, expected, flush=True)
                finally:
                    if s.active:
                        r.close("cycle-extra-cleanup")
        report["passed"] = True
    except BaseException as e:
        report["error"] = repr(e)
        raise
    finally:
        (OUT / "extra-live-results.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
