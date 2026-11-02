"""Native cycle tests: disk position fixtures, real pipe contact, death and resume.

No game memory writes. Fixtures move only the closed test run to a chest/exit;
the native engine triggers rewards, routing, character selection and saves.
"""

import json, time, uuid, subprocess
from menu_host.store import Store, save
from menu_host.draft import Draft
from menu_host.runtime import Runtime
from native_menu.observe import objects
from native_rewards_live import write_save, run_case
from gameplay.cycle_plan import choose, GROUP
from transition.router import GROUP as ROUTE, STAGES
from export_route_probe import ROOT
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-NativeCycle-20261025"


def observe(r, folder):
    time.sleep(0.35)
    p = save(folder / "onlineLicense.ini")
    names = [o["name"] for o in objects(r.reader) if o["name"].startswith("ON")]
    return dict(
        name=p.get("License", "CharacterName"),
        id=p.getint("License", "Character"),
        sprites=names,
        frame=r.reader.frame(),
        history=dict(p[GROUP]) if p.has_section(GROUP) else {},
    )


def check(r, folder, expected):
    state = observe(r, folder)
    assert state["name"] == expected["name"] and state["id"] == expected["id"], (
        expected,
        state,
    )
    # Name-to-sprite spelling comes from the original object catalogue.
    required = {"Kirby": "ONKirby", "Luigi": "ONLuigi"}.get(expected["name"])
    if required:
        assert required in state["sprites"], state
    assert any(o["name"] == "Player" for o in objects(r.reader)), state
    return state


def restart(r, s, folder, expected, case):
    before = s.summary(1)["deaths"]
    r.key("q")
    time.sleep(0.65)
    assert not any(o["name"] == "Player" for o in objects(r.reader))
    r.key("r")
    time.sleep(0.4)
    case["after_death"] = check(r, folder, expected)
    r.key("F2")
    deadline = time.monotonic() + 12
    while s.active and time.monotonic() < deadline:
        r.poll()
        time.sleep(0.1)
    assert not s.active
    assert s.summary(1)["deaths"] > before
    r.start(1)
    case["after_resume"] = check(r, folder, expected)
    r.close("cycle-resume")


def main(cases=None):
    capture.OUT = OUT
    report = dict(scope=__doc__, memory_writes=0, cases=[], chest_cases=[])
    try:
        for enabled, unlock in (
            cases
            if cases is not None
            else [(False, False), (True, False), (True, True)]
        ):
            name = "cycle-" + ("unlock" if unlock else "on" if enabled else "off")
            print("START", name, flush=True)
            s = Store(OUT / (name + "-" + uuid.uuid4().hex[:6]))
            with s.lock():
                d = Draft()
                d.update(
                    level_pool=["save1.ini"],
                    level_count=1,
                    boss_pool=["hellokitty"],
                    route_boss_count=1,
                    characters=enabled,
                    items=unlock,
                    start_character="Kirby",
                    god_mode=True,
                    no_mouse_ghost=True,
                    fast_chests=True,
                )
                d.seed = "0000001D"
                s.create(1, d)
                folder = s.folder(1)
                p = json.loads((folder / "plan.json").read_text())
                assert p["route"][:2] == ["save1.ini", "boss1.ini"], p["route"]
                case = dict(
                    name=name,
                    folder=str(folder),
                    route=p["route"],
                    seed=d.seed,
                    enabled=enabled,
                    unlock=unlock,
                )
                report["cases"].append(case)
                r = Runtime(s)
                try:
                    r.start(1)
                    case["initial"] = check(r, folder, dict(name="Kirby", id=20))
                    r.close("cycle-initial")
                    if unlock:
                        chest_report = {"cases": report["chest_cases"]}
                        run_case(s, r, folder, "cd", True, True, chest_report)
                        assert (
                            save(folder / "onlineLicense.ini").getint(
                                "Unlockables", "Luigi"
                            )
                            == 1
                        )
                        case["new_unlock"] = "Luigi"
                    c = save(folder / "SaveFile1.ini")
                    c["Positions"]["xpos"] = "4415"
                    c["Positions"]["ypos"] = "400"
                    write_save(folder / "SaveFile1.ini", c)
                    r.start(1)
                    subprocess.run(["wmctrl", "-ia", r.window], check=True)
                    subprocess.run(["xdotool", "keydown", "Right"], check=True)
                    try:
                        time.sleep(0.3)
                    finally:
                        subprocess.run(["xdotool", "keyup", "Right"], check=True)
                    end = time.monotonic() + 10
                    while time.monotonic() < end:
                        c = save(folder / "SaveFile1.ini")
                        if c.getint(ROUTE, "CurrentStage") == STAGES["boss1.ini"]["id"]:
                            break
                        time.sleep(0.1)
                    assert (
                        c.getint(ROUTE, "CurrentStage") == STAGES["boss1.ini"]["id"]
                    ), dict(c[ROUTE])
                    assert c.getint(ROUTE, "Done25") == 1
                    expected = (
                        choose(d.seed, 1, {"luigi": 1} if unlock else {}, "Kirby")
                        if enabled
                        else dict(name="Kirby", id=20)
                    )
                    case["expected"] = expected
                    case["arrival"] = check(r, folder, expected)
                    capture.snap(r, name + "-arrival")
                    restart(r, s, folder, expected, case)
                    case["passed"] = True
                    print("PASS", name, expected, flush=True)
                finally:
                    if s.active:
                        r.close("cycle-cleanup")
        report["passed"] = True
    except BaseException as e:
        report["error"] = repr(e)
        raise
    finally:
        (OUT / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
