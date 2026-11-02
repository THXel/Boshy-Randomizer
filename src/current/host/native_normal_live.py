"""Normal mode: real original pipe exit from closed-save position fixtures.

Checks explicit/automatic start, optional native character changes, death,
checkpoint rewind, F2 and reopening. No runtime memory writes or forced exits.
"""

import json, time, subprocess, uuid
from menu_host.store import Store, save
from menu_host.draft import Draft
from menu_host.runtime import Runtime
from native_rewards_live import write_save
from native_cycle_live import check, restart
from gameplay.cycle_plan import initial
from gameplay.normal_plan import choose, GROUP
from export_route_probe import ROOT
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-NativeModes-20261025"


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, memory_writes=0, cases=[])
    try:
        for enabled, char in [(False, "Kirby"), (True, "Kirby"), (True, "Auto")]:
            name = f"normal-{enabled}-{char}"
            print("START", name, flush=True)
            s = Store(OUT / (name + "-" + uuid.uuid4().hex[:6]))
            with s.lock():
                d = Draft()
                d.set_mode("normal")
                d.update(
                    characters=enabled,
                    start_character=char,
                    god_mode=True,
                    no_mouse_ghost=True,
                )
                d.seed = "DEADBEEF"
                s.create(1, d)
                folder = s.folder(1)
                r = Runtime(s)
                case = dict(name=name, folder=str(folder))
                report["cases"].append(case)
                try:
                    r.start(1)
                    first = initial(d.options, d.seed)
                    case["initial"] = check(r, folder, first)
                    r.close("normal-initial")
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
                    end = time.monotonic() + 12
                    while time.monotonic() < end:
                        try:
                            if r.reader.frame() == "Secret Level 1 - 1-1":
                                break
                        except RuntimeError:
                            pass
                        time.sleep(0.1)
                    assert r.reader.frame() == "Secret Level 1 - 1-1"
                    expected = (
                        choose(d.seed, 33, 1, {}, first["name"]) if enabled else first
                    )
                    case["arrival"] = check(r, folder, expected)
                    capture.snap(r, name + "-arrival")
                    c = save(folder / "SaveFile1.ini")
                    assert c.getint("FusionRouteV4", "Schema") == 0
                    assert c.getint("FusionRouteV4", "Done25", fallback=0) == 0
                    if enabled:
                        assert (
                            save(folder / "onlineLicense.ini").getint(GROUP, "Step")
                            == 2
                        )
                    restart(r, s, folder, expected, case)
                    case["original_exit"] = True
                    case["passed"] = True
                    print("PASS", name, expected, flush=True)
                finally:
                    if s.active:
                        r.close("normal-cleanup")
        report["passed"] = True
    except BaseException as e:
        report["error"] = repr(e)
        raise
    finally:
        (OUT / "normal-live-results.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
