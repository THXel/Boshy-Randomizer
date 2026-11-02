"""Mario fight using ordinary input plus a private-process death-loop guard.

No boss HP, timers, phase flags, scale, or positions are written.
"""

import json, os, subprocess, time
from pathlib import Path
from Xlib import X, display
from PIL import Image
from phase_state import State

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "outputs/Fusion-Mario-Natural-20261023"
rows = [
    r.split(None, 4)
    for r in subprocess.check_output(["wmctrl", "-lp"], text=True).splitlines()
    if r.endswith(" I Wanna Be The Boshy")
]
assert len(rows) == 1
wid, pid = rows[0][0], rows[0][2]
assert Path(os.readlink("/proc/" + pid + "/cwd")).name == "rebuilt-mario-exit"
d = display.Display()
w = d.create_resource_object("window", int(wid, 16))
g = w.get_geometry()
s = State("rebuilt-mario-exit")
report = {
    "pid": pid,
    "scope": "normal input, godmode only; no boss or position writes",
    "samples": [],
    "writes": s.writes,
}


def key(k, duration=0.2):
    subprocess.run(["xdotool", "keydown", k], check=True)
    time.sleep(duration)
    subprocess.run(["xdotool", "keyup", k], check=True)


def shot(name):
    im = w.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
    Image.frombytes("RGB", (g.width, g.height), im.data, "raw", "BGRX").save(
        OUT / (name + ".png")
    )


try:
    subprocess.run(["wmctrl", "-ia", wid], check=True)
    subprocess.run(["xdotool", "mousemove", "5", "5"])
    s.protect()
    key("r")
    time.sleep(0.4)
    s.protect()
    key("Left", 3)
    key("Right", 0.08)
    subprocess.run(["xdotool", "keydown", "x"], check=True)
    start = time.monotonic()
    for tick in range(600):
        time.sleep(0.5)
        obs = s.objects()
        interesting = [
            dict(o, values=s.values(o, 8))
            for o in obs
            if o["name"]
            in [
                "Player",
                "Classic Mario",
                "Classic Mario 2",
                "Classic Mario 3",
                "Active 27",
            ]
        ]
        report["samples"].append(
            {"seconds": round(time.monotonic() - start, 2), "objects": interesting}
        )
        if tick % 20 == 0:
            shot("fight-" + str(tick))
            (OUT / "natural-result.json").write_text(json.dumps(report, indent=2))
            print(json.dumps(report["samples"][-1]), flush=True)
        pipe = next((o for o in obs if o["name"] == "Active 27"), None)
        if pipe and pipe["x"] <= 604:
            report["pipe_revealed"] = True
            shot("pipe-revealed")
            break
        if not any(o["name"] == "Player" for o in obs):
            report["unexpected_player_absent"] = True
            shot("player-absent")
            break
finally:
    subprocess.run(["xdotool", "keyup", "x", "Left", "Right"])
    (OUT / "natural-result.json").write_text(json.dumps(report, indent=2))
    s.close()
