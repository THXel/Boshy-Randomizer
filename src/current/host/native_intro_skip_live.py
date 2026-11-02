"""Isolated native boss-entry comparisons: auto-skip versus manual S, no memory writes.

Uses normal route starts, except the Solgryn finale selected in the private save.
Only the intro transition is verified here; these are not full boss victories.
"""

import io
import json
import time
import uuid
import sys
from menu_host.draft import Draft
from menu_host.store import Store, save, RC4
from menu_host.runtime import Runtime
from transition.router import STAGES, GROUP
from export_route_probe import ROOT
from native_menu.observe import objects
from god_mode_boss_probe import values
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-NativeIntroSkip-20261024"
CASES = (
    ("hellokitty", "hellokitty", 0, 1499),
    ("ryu", "Ryu", 0, 1079),
    ("mario", "Classic Mario", 0, 400),
    ("biollante", "Classic Mario", 0, 830),
    ("megaman", "Active 4", 0, 149),
    ("shangtsung", "Active 4", 0, 489),
    ("missingno", "randomness", 0, 680),
    ("questionmark", "randomness", 0, 779),
    ("ridley", "randomness", 0, 779),
    ("solgryn", "randomness", 0, 2080),
    ("ganon", "Ganon", 1, 349),
)


def state(runtime, name):
    obj = next(o for o in objects(runtime.reader) if o["name"] == name)
    return dict(
        values=values(runtime.reader, obj),
        flags=runtime.reader.u32(obj["ptr"] + obj["rel"] + 104),
        x=obj["x"],
        y=obj["y"],
    )


def reached(name, sample, index, target):
    # Kitty resets her phase timer to zero as she enters combat; flag 1 records it.
    return (
        bool(sample["flags"] & 2)
        if name == "hellokitty"
        else sample["values"][index] >= target
    )


def main():
    capture.OUT = OUT
    result = OUT / "live-results.json"
    report = (
        json.loads(result.read_text())
        if result.exists()
        else dict(scope=__doc__, memory_writes=0, cases=[])
    )
    for name, obj, index, target in CASES:
        if len(sys.argv) > 1 and name not in sys.argv[1:]:
            continue
        for enabled in (False, True):
            if any(
                c["name"] == name and c["enabled"] == enabled and c.get("passed")
                for c in report["cases"]
            ):
                continue
            report["cases"] = [
                c
                for c in report["cases"]
                if not (c["name"] == name and c["enabled"] == enabled)
            ]
            case = dict(name=name, enabled=enabled, target=target, samples=[])
            report["cases"].append(case)
            s = Store(
                OUT
                / ("profile-" + name + "-" + str(enabled) + "-" + uuid.uuid4().hex[:6])
            )
            with s.lock():
                d = Draft()
                d.update(
                    level_pool=[],
                    level_count=0,
                    boss_pool=[name if name != "solgryn" else "hellokitty"],
                    route_boss_count=1,
                    difficulty=1,
                    god_mode=True,
                    no_mouse_ghost=True,
                    skip_intro=enabled,
                    start_character="Kirby",
                    sprite_scenery=name in ("hellokitty", "mario", "solgryn"),
                    sprite_actors=True,
                )
                s.create(1, d)
                if name == "solgryn":
                    path = s.folder(1) / "SaveFile1.ini"
                    c = save(path)
                    stage = STAGES["boss_solgryn.ini"]
                    c[GROUP]["CurrentStage"] = str(stage["id"])
                    for a, b in [("frame", "frame"), ("xpos", "x"), ("ypos", "y")]:
                        c["Positions"][a] = str(stage[b])
                    buf = io.StringIO()
                    c.write(buf)
                    path.write_bytes(RC4(b"BLOB", buf.getvalue().encode("latin1")))
                    case["save_fixture"] = "Solgryn finale entry"
                r = Runtime(s)
                try:
                    case["frame"] = r.start(1)
                    initial = state(r, obj)
                    case["initial"] = initial
                    print("START", name, enabled, initial, flush=True)
                    if not enabled:
                        assert not reached(name, initial, index, target), (
                            name,
                            initial,
                        )
                        r.key("s")
                    start = time.monotonic()
                    while time.monotonic() - start < 7:
                        sample = state(r, obj)
                        sample["seconds"] = round(time.monotonic() - start, 3)
                        case["samples"].append(sample)
                        if reached(name, sample, index, target):
                            break
                        time.sleep(0.15)
                    assert any(
                        reached(name, v, index, target) for v in case["samples"]
                    ), (name, enabled, case["samples"][-1])
                    capture.snap(r, name + "-" + ("auto" if enabled else "manual"))
                    assert any(o["name"] == "ONKirby" for o in objects(r.reader))
                    if name in ("mario", "solgryn") and enabled:
                        r.key("q")
                        time.sleep(0.5)
                        assert not any(o["name"] == "Player" for o in objects(r.reader))
                        r.key("r")
                        time.sleep(0.8)
                        case["after_restart"] = state(r, obj)
                        assert reached(name, case["after_restart"], index, target), (
                            name,
                            case["after_restart"],
                        )
                    r.close("intro-skip-probe")
                    s.resume(1)
                    case["passed"] = True
                    print("PASS", name, enabled, case["samples"][-1], flush=True)
                except BaseException as error:
                    case["error"] = repr(error)
                    try:
                        capture.snap(r, name + "-failure")
                    except Exception:
                        pass
                    raise
                finally:
                    if s.active:
                        r.close("intro-skip-cleanup")
                    result.write_text(json.dumps(report, indent=2) + "\n")
    report["passed"] = len(report["cases"]) == 22 and all(
        c.get("passed") for c in report["cases"]
    )
    result.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
