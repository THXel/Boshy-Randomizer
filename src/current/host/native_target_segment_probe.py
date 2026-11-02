"""Target same-frame routing and character changes at the genuine Kracko entry.

A closed-save entry fixture places the player before the native region trigger.
No victory is fabricated: this checks entry, station identity and death/resume.
"""

import json, uuid, time
from menu_host.store import Store, save
from menu_host.runtime import Runtime
from menu_host.draft import Draft
from native_rewards_live import write_save
from native_targets_live import OUT, hold, state, wait
from native_cycle_live import check, restart
from gameplay import target_plan as target, normal_plan, cycle_plan
from transition.router import STAGES, GROUP as ROUTE
import god_mode_live as capture

capture.OUT = OUT


def main():
    s = Store(OUT / ("same-frame-" + uuid.uuid4().hex[:6]))
    case = dict(scope=__doc__, memory_writes=0)
    with s.lock():
        d = Draft()
        d.set_mode("target")
        d.update(
            characters=True,
            target_count=19,
            boss_count=22,
            god_mode=True,
            no_mouse_ghost=True,
        )
        d.seed = next(
            f"{i:08X}"
            for i in range(1000)
            if target.choose(
                f"{i:08X}", "save2.ini", dict(CursorRooms=1, CursorBosses=1), {35}
            )
            == "boss2.ini"
        )
        s.create(1, d)
        folder = s.folder(1)
        case.update(folder=str(folder), seed=d.seed)
        c = save(folder / "SaveFile1.ini")
        c[ROUTE]["CurrentStage"] = "35"
        c["Positions"].update(frame="5", xpos="3170", ypos="400")
        write_save(folder / "SaveFile1.ini", c)
        r = Runtime(s)
        try:
            r.start(1)
            first = cycle_plan.initial(d.options, d.seed)
            case["initial_character"] = check(r, folder, first)
            hold(r, "Right", 0.55)
            wait(lambda: state(folder)["visit"] == 1)
            time.sleep(0.4)
            expected = normal_plan.choose(d.seed, 5, 1, {}, first["name"])
            case["arrival_character"] = check(r, folder, expected)
            case["arrival"] = state(folder)
            assert case["arrival"]["stage"] == STAGES["boss2.ini"]["id"]
            assert case["arrival"]["done"]["done35"] == "1"
            assert case["arrival"]["done"]["done10"] == "0"
            capture.snap(r, "target-same-frame-kracko")
            restart(r, s, folder, expected, case)
            assert state(folder)["visit"] == 1
            assert state(folder)["done"] == case["arrival"]["done"]
            case["passed"] = True
            print("PASS Target same-frame entry", flush=True)
        except BaseException as error:
            case["error"] = repr(error)
            raise
        finally:
            if s.active:
                r.close("target-segment-cleanup")
            (OUT / "segment-live-results.json").write_text(
                json.dumps(case, indent=2) + "\n"
            )


if __name__ == "__main__":
    main()
