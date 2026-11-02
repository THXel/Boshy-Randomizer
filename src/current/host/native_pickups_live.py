"""Native pickup tests using isolated save-position fixtures at real chest locations.

No runtime memory writes, reward injections or trigger patches. Verifies native
award persistence, modal dialogs, movement release and Q/R/resume retention.
"""

import io, json, time, uuid, subprocess, sys
from menu_host.store import Store, save, RC4
from menu_host.draft import Draft
from menu_host.runtime import Runtime
from export_route_probe import ROOT
from native_menu.observe import objects
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-NativePickups-20261024"
ITEMS = {
    "cd": (
        "save1.ini",
        "Active 54",
        3590,
        812,
        "Lalalalalala CD",
        "Collectables",
        "CD GET!",
    ),
    "mixer": (
        "save1.ini",
        "Active 57",
        3808,
        151,
        "Mixer",
        "Collectables",
        "MIXER GET!",
    ),
    "timer": (
        "save4.ini",
        "Active 51",
        992,
        887,
        "Timer",
        "Collectables",
        "TIMER GET!",
    ),
    "scouter": (
        "save7.ini",
        "Active 45",
        2320,
        864,
        "Scouter",
        "Collectables",
        "SCOUTER GET!",
    ),
    "luigi": ("save1.ini", "Active 65", 3680, 439, "Luigi", "Unlockables", None),
    "item": ("save1.ini", "Active 36", 128, 759, "Awesomesauce", "Collectables", None),
}


def dialogs(r):
    rows = subprocess.check_output(["wmctrl", "-lp"], text=True).splitlines()
    return [
        row.split(None, 4)
        for row in rows
        if len(row.split(None, 4)) == 5
        and row.split(None, 4)[2] == str(r.pid)
        and row.split(None, 4)[0] != r.window
    ]


def close_dialog(row):
    subprocess.run(
        ["xdotool", "windowactivate", "--sync", row[0], "keydown", "Return"], check=True
    )
    time.sleep(0.15)
    subprocess.run(["xdotool", "keyup", "Return"], check=True)


def player(r):
    o = next(o for o in objects(r.reader) if o["name"] == "Player")
    return dict(
        x=o["x"],
        y=o["y"],
        timer=r.reader.u32(r.reader.u32(o["ptr"] + o["rel"]) + 24 * 16 + 8),
        pickup_active=bool(r.reader.u32(o["ptr"] + o["rel"] + 104) & 32),
    )


def main():
    capture.OUT = OUT
    result = OUT / "live-results.json"
    report = (
        json.loads(result.read_text())
        if result.exists()
        else dict(scope=__doc__, memory_writes=0, cases=[])
    )
    cases = [
        (n, True, q) for n in ("cd", "mixer", "timer", "scouter") for q in (False, True)
    ] + [
        ("cd", False, True),
        ("luigi", False, True),
        ("luigi", True, True),
        ("item", True, True),
    ]
    for name, fast, quiet in cases:
        tag = f"{name}-fast{int(fast)}-quiet{int(quiet)}"
        if len(sys.argv) > 1 and name not in sys.argv[1:]:
            continue
        if any(c["tag"] == tag and c.get("passed") for c in report["cases"]):
            continue
        report["cases"] = [c for c in report["cases"] if c["tag"] != tag]
        level, obj, x, y, reward, group, title = ITEMS[name]
        case = dict(
            tag=tag,
            fast=fast,
            quiet=quiet,
            reward=reward,
            group=group,
            samples=[],
            dialogs=[],
        )
        report["cases"].append(case)
        s = Store(OUT / ("profile-" + tag + "-" + uuid.uuid4().hex[:6]))
        with s.lock():
            d = Draft()
            d.update(
                level_pool=[level],
                level_count=1,
                boss_pool=[],
                route_boss_count=0,
                god_mode=True,
                no_mouse_ghost=True,
                fast_chests=fast,
                quiet_pickups=quiet,
                start_character="Kirby",
            )
            s.create(1, d)
            folder = s.folder(1)
            path = folder / "SaveFile1.ini"
            c = save(path)
            c["Positions"]["xpos"] = str(x)
            c["Positions"]["ypos"] = str(y - 8)
            buf = io.StringIO()
            c.write(buf)
            path.write_bytes(RC4(b"BLOB", buf.getvalue().encode("latin1")))
            r = Runtime(s)
            try:
                case["frame"] = r.start(1)
                start = time.monotonic()
                case["initial"] = player(r)
                print("START", tag, case["initial"], flush=True)
                appeared = False
                last_capture = 0
                while time.monotonic() - start < 11:
                    t = time.monotonic() - start
                    ds = dialogs(r)
                    for row in ds:
                        case["dialogs"].append(dict(title=row[4], seconds=t))
                        capture.snap(r, tag + "-dialog-parent")
                        assert not quiet and title and row[4] == title, (tag, row)
                        appeared = True
                        close_dialog(row)
                    obs = objects(r.reader)
                    p = player(r)
                    case["samples"].append(
                        dict(
                            seconds=round(t, 3),
                            **p,
                            chest_present=any(o["name"] == obj for o in obs),
                        )
                    )
                    if t > 0.15 and last_capture == 0:
                        capture.snap(r, tag + "-pickup")
                        last_capture = 1
                    if (
                        not any(o["name"] == obj for o in obs)
                        and not p["pickup_active"]
                    ):
                        case["released_seconds"] = round(t, 3)
                        break
                    time.sleep(0.06)
                assert "released_seconds" in case, (tag, case["samples"][-1])
                assert appeared == bool(title and not quiet), (tag, appeared)
                assert (
                    case["released_seconds"] < 2
                    if fast
                    else case["released_seconds"] > 5
                ), case["released_seconds"]
                capture.snap(r, tag + "-released")
                before = player(r)
                r.key("Right")
                after = player(r)
                case["movement_after"] = dict(before=before, after=after)
                # R will always exercise native reset even when a particular chest is beside a wall.
                r.key("q")
                time.sleep(0.35)
                r.key("r")
                time.sleep(0.4)
                assert any(o["name"] == "Player" for o in objects(r.reader))
                r.close("pickup-probe")
                s.resume(1)
                receipt = save(
                    folder
                    / (
                        "onlineLicense.ini"
                        if group == "Unlockables"
                        else "SaveFile1.ini"
                    )
                )
                assert receipt.getint(group, reward, fallback=0) == 1, (
                    tag,
                    dict(receipt),
                )
                case["saved_reward"] = True
                case["resume_frame"] = r.start(1)
                time.sleep(0.25)
                assert not any(o["name"] == obj for o in objects(r.reader)), tag
                r.close("pickup-resume")
                s.resume(1)
                case["passed"] = True
                print("PASS", tag, case["released_seconds"], flush=True)
            except BaseException as e:
                case["error"] = repr(e)
                try:
                    capture.snap(r, tag + "-failure")
                except Exception:
                    pass
                raise
            finally:
                for row in dialogs(r) if r.pid else []:
                    close_dialog(row)
                if s.active:
                    r.close("pickup-cleanup")
                result.write_text(json.dumps(report, indent=2) + "\n")
    report["passed"] = len(report["cases"]) == 12 and all(
        c.get("passed") for c in report["cases"]
    )
    result.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
