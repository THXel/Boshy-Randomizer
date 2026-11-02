"""Walk into the legitimately revealed pipe; verify destination and real death."""

import json, subprocess, time, runpy, configparser
from pathlib import Path
from Xlib import X, display
from PIL import Image
from phase_state import State

R = Path(__file__).resolve().parents[2]
out = R / "outputs/Fusion-Mario-Natural-20261023"
s = State("rebuilt-mario-exit")
rows = [
    r.split(None, 4)
    for r in subprocess.check_output(["wmctrl", "-lp"], text=True).splitlines()
    if r.endswith(" I Wanna Be The Boshy")
]
assert len(rows) == 1
wid = rows[0][0]
subprocess.run(["wmctrl", "-ia", wid])
subprocess.run(["xdotool", "mousemove", "5", "5"])
w = display.Display().create_resource_object("window", int(wid, 16))
g = w.get_geometry()


def shot(n):
    im = w.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
    Image.frombytes("RGB", (g.width, g.height), im.data, "raw", "BGRX").save(
        out / (n + ".png")
    )


def key(k):
    subprocess.run(["xdotool", "keydown", k])
    time.sleep(0.2)
    subprocess.run(["xdotool", "keyup", k])


rc = runpy.run_path(str(R / "work/Boshy-Randomizer/src/shared/PY/rc4_utils.py"))[
    "rc4_crypt"
]
save = Path(
    "/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshySceneTests/rebuilt-mario-exit/SaveFile1.ini"
)


def read():
    return rc(b"BLOB", save.read_bytes()).decode("latin1")


report = {"writes": s.writes, "samples": [], "before": read()}
try:
    assert not any(
        o["name"] in ["Classic Mario", "Classic Mario 3"] for o in s.objects()
    )
    subprocess.run(["xdotool", "keydown", "Right"])
    for i in range(150):
        time.sleep(0.03)
        obs = s.objects()
        pipe = next((o for o in obs if o["name"] == "Active 27"), None)
        p = next((o for o in obs if o["name"] == "Player"), None)
        timer = s.values(pipe, 1)[0] if pipe else None
        report["samples"].append({"pipe_timer": timer, "player": p})
        if timer is None or timer > 0:
            break
    subprocess.run(["xdotool", "keyup", "Right"])
    shot("pipe-entered")
    time.sleep(1.5)
    shot("natural-arrival")
    report["arrival"] = read()
    c = configparser.ConfigParser()
    c.read_string(report["arrival"])
    assert (
        c.getint("Positions", "frame") == 11
        and c.getint("FusionRandoV3", "MarioDone") == 1
    )
    key("q")
    time.sleep(0.7)
    report["dead"] = not any(o["name"] == "Player" for o in s.objects())
    shot("natural-death")
    assert report["dead"]
    key("r")
    time.sleep(0.7)
    report["alive_after_restart"] = any(o["name"] == "Player" for o in s.objects())
    shot("natural-restart")
    report["restart"] = read()
    assert report["alive_after_restart"]
    report["same_process"] = s.b.read(s.b.ready["base"], 2) == b"MZ"
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in ["samples", "before", "arrival", "restart"]
            }
        )
    )
finally:
    subprocess.run(["xdotool", "keyup", "Right"])
    (out / "exit-result.json").write_text(json.dumps(report, indent=2))
    s.close()
