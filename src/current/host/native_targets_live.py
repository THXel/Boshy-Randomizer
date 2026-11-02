"""Native Target tests with closed-save position fixtures and ordinary input.

No live memory writes. Tests genuine exits, chest contact, goal gating, native
character cycling and Q/R/F2/resume. Collect finale uses clearly labelled prior
progress fixtures; it is not a complete 19-item/22-boss playthrough.
"""

import json, time, uuid, subprocess, sys
from menu_host.store import Store, save
from menu_host.draft import Draft
from menu_host.runtime import Runtime
from native_rewards_live import write_save
from native_cycle_live import check, restart
from gameplay import target_plan as target, normal_plan, cycle_plan
from transition.router import STAGES, GROUP as ROUTE
from export_route_probe import ROOT
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-NativeTargets-20261025"


def wait(predicate, seconds=15):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            if predicate():
                return
        except (RuntimeError, ValueError):
            pass
        time.sleep(0.1)
    raise AssertionError("Native transition timeout")


def hold(r, key, seconds):
    subprocess.run(["wmctrl", "-ia", r.window], check=True)
    subprocess.run(["xdotool", "keydown", key], check=True)
    try:
        time.sleep(seconds)
    finally:
        subprocess.run(["xdotool", "keyup", key], check=True)


def state(folder):
    c = save(folder / "SaveFile1.ini")
    return dict(
        visit=c.getint(target.GROUP, "Visit"),
        ready=c.getint(target.GROUP, "Ready"),
        stage=c.getint(ROUTE, "CurrentStage"),
        done={k: v for k, v in c[ROUTE].items() if k.startswith("done")},
        items=dict(c["Collectables"]),
        deaths=c.getint("Stats", "Deaths"),
        completed=c.getint(ROUTE, "Completed"),
    )


def seed_for(options, items, bosses=None):
    for i in range(10000):
        seed = f"{i:08X}"
        g = target.goals(seed, options)
        if g["items"] == items and (bosses is None or g["bosses"] == bosses):
            return seed
    raise AssertionError("No fixture seed")


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, memory_writes=0, cases=[])
    wanted = sys.argv[1:] or [
        "pipe-off",
        "pipe-on",
        "pickup-gated",
        "pickup-finale",
        "collect-finale",
    ]
    try:
        for name in wanted:
            s = Store(OUT / (name + "-" + uuid.uuid4().hex[:6]))
            with s.lock():
                d = Draft()
                d.set_mode("target")
                enabled = name == "pipe-on"
                d.update(
                    characters=enabled,
                    god_mode=True,
                    no_mouse_ghost=True,
                    fast_chests=True,
                    one_hp=True,
                    skip_intro=True,
                    autofire=True,
                )
                if name.startswith("pipe"):
                    d.update(target_count=19, boss_count=22)
                    d.seed = "DEADBEEF"
                elif name == "collect-finale":
                    d.update(target_count=19, boss_count=22)
                    d.seed = "DEADBEEF"
                else:
                    d.update(
                        target_count=1, boss_count=1 if name == "pickup-gated" else 0
                    )
                    d.seed = seed_for(
                        d.options,
                        ["Lalalalalala CD"],
                        ["hellokitty"] if name == "pickup-gated" else [],
                    )
                s.create(1, d)
                folder = s.folder(1)
                r = Runtime(s)
                case = dict(
                    name=name,
                    folder=str(folder),
                    seed=d.seed,
                    prior_progress_fixture=name in ("collect-finale", "pipe-exhausted"),
                )
                report["cases"].append(case)
                print("START", name, flush=True)
                try:
                    c = save(folder / "SaveFile1.ini")
                    if name.startswith("pipe"):
                        c["Positions"]["xpos"] = "4415"
                        c["Positions"]["ypos"] = "400"
                        if name == "pipe-exhausted":
                            for sid in target.BOSS_STAGES.values():
                                c[ROUTE]["Done" + str(sid)] = "1"
                    else:
                        c["Positions"]["xpos"] = "3590"
                        c["Positions"]["ypos"] = "804"
                        if name == "collect-finale":
                            for item in target.ITEMS:
                                if item != "Lalalalalala CD":
                                    c["Collectables"][item] = "1"
                            for sid in target.BOSS_STAGES.values():
                                c[ROUTE]["Done" + str(sid)] = "1"
                    write_save(folder / "SaveFile1.ini", c)
                    case["initial"] = state(folder)
                    r.start(1)
                    if name.startswith("pipe"):
                        hold(r, "Right", 0.3)
                        wait(lambda: state(folder)["visit"] == 1)
                        expected_spot = target.choose(
                            d.seed,
                            "save1.ini",
                            dict(CursorRooms=1, CursorBosses=1),
                            {25}
                            | (
                                set(target.BOSS_STAGES.values())
                                if name == "pipe-exhausted"
                                else set()
                            ),
                        )
                        wait(
                            lambda: r.reader.frame()
                            not in ("First World - Prehistorik", "Title Screen")
                        )
                        time.sleep(0.4)
                        case["arrival"] = state(folder)
                        assert (
                            case["arrival"]["stage"] == STAGES[expected_spot]["id"]
                        ), (expected_spot, case)
                        assert (
                            not case["arrival"]["ready"]
                            and case["arrival"]["done"]["done25"] == "1"
                        )
                        case["destination"] = expected_spot
                        if enabled:
                            first = cycle_plan.initial(d.options, d.seed)
                            expected = normal_plan.choose(
                                d.seed,
                                STAGES[expected_spot]["frame"],
                                1,
                                {},
                                first["name"],
                            )
                            case["character"] = check(r, folder, expected)
                            restart(r, s, folder, expected, case)
                        else:
                            r.key("q")
                            time.sleep(0.6)
                            r.key("r")
                            time.sleep(0.5)
                            r.close("target-pipe-restart")
                            r.start(1)
                            r.close("target-pipe-resume")
                        assert state(folder)["visit"] == 1
                        assert state(folder)["done"] == case["arrival"]["done"]
                    else:
                        wait(
                            lambda: save(folder / "SaveFile1.ini").getint(
                                "Collectables", "Lalalalalala CD", fallback=0
                            )
                            == 1
                        )
                        if name == "pickup-gated":
                            time.sleep(1)
                            case["after_pickup"] = state(folder)
                            assert (
                                case["after_pickup"]["ready"] == 0
                                and case["after_pickup"]["visit"] == 0
                            )
                            assert case["after_pickup"]["done"]["done1"] == "0"
                        else:
                            wait(
                                lambda: state(folder)["stage"]
                                == STAGES[target.FINAL]["id"]
                            )
                            time.sleep(0.8)
                            case["arrival"] = state(folder)
                            assert r.reader.frame() == "Eleventh Boss - Solgryn", (
                                r.reader.frame()
                            )
                            assert (
                                case["arrival"]["ready"] == 1
                                and case["arrival"]["visit"] == 1
                            )
                            assert case["arrival"]["completed"] == 0
                            assert case["arrival"]["done"]["done25"] == "0"
                        capture.snap(r, name + "-native")
                        before = state(folder)
                        r.key("q")
                        time.sleep(0.6)
                        r.key("r")
                        time.sleep(0.5)
                        r.key("F2")
                        wait(lambda: r.poll() == "menu" or not s.active)
                        r.start(1)
                        time.sleep(0.4)
                        case["after_resume"] = state(folder)
                        for key in (
                            "visit",
                            "ready",
                            "stage",
                            "done",
                            "items",
                            "completed",
                        ):
                            assert case["after_resume"][key] == before[key], (
                                key,
                                before,
                                case["after_resume"],
                            )
                        r.close("target-pickup-resume")
                    s.resume(1)
                    case["passed"] = True
                    print("PASS", name, flush=True)
                except BaseException as error:
                    case["error"] = repr(error)
                    try:
                        capture.snap(r, name + "-failure")
                    except Exception:
                        pass
                    raise
                finally:
                    if s.active:
                        r.close("target-test-cleanup")
        report["passed"] = True
    finally:
        (OUT / ("live-" + "-".join(wanted) + ".json")).write_text(
            json.dumps(report, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
