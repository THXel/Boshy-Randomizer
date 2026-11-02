"""Live V4 chained transition fixture; no claim of full-level completion."""

import configparser, json, os, runpy, subprocess, time
from pathlib import Path
from Xlib import X, display
from PIL import Image
from phase_state import State
from transition.router import GROUP, STAGES

ROOT = Path(__file__).resolve().parents[2]
CASE = "rebuilt-mario-routes"
LAB = (
    Path("/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshySceneTests") / CASE
)
OUT = ROOT / "outputs/Fusion-Routes-20261023/live-mario-chain-confirmed"
OUT.mkdir(exist_ok=False)
rows = [
    r.split(None, 4)
    for r in subprocess.check_output(["wmctrl", "-lp"], text=True).splitlines()
    if r.endswith(" I Wanna Be The Boshy")
]
assert len(rows) == 1
wid = rows[0][0]
pid = rows[0][2]
assert Path(os.readlink("/proc/" + pid + "/cwd")) == LAB
D = display.Display()
w = D.create_resource_object("window", int(wid, 16))
g = w.get_geometry()
rc4 = runpy.run_path(str(ROOT / "work/Boshy-Randomizer/src/shared/PY/rc4_utils.py"))[
    "rc4_crypt"
]
s = State(CASE)
report = {
    "scope": "synthetic outgoing-event and region fixtures, real engine transitions",
    "pid": pid,
    "writes": s.writes,
}


def snap(name):
    im = w.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
    Image.frombytes("RGB", (g.width, g.height), im.data, "raw", "BGRX").save(
        OUT / (name + ".png")
    )


def key(k):
    subprocess.run(["wmctrl", "-ia", wid])
    time.sleep(0.1)
    subprocess.run(["xdotool", "keydown", k])
    time.sleep(0.3)
    subprocess.run(["xdotool", "keyup", k])


def saved():
    c = configparser.ConfigParser()
    c.read_string(rc4(b"BLOB", (LAB / "SaveFile1.ini").read_bytes()).decode("latin1"))
    return c


def obj(name):
    return next(o for o in s.objects() if o["name"] == name)


def wait_player(timeout=6):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if any(o["name"] == "Player" for o in s.objects()):
            return True
        time.sleep(0.15)
    return False


def station(spot, done):
    c = saved()
    assert c.getint(GROUP, "CurrentStage") == STAGES[spot]["id"], dict(c[GROUP])
    assert c.getint("Positions", "frame") == STAGES[spot]["frame"]
    for d in done:
        assert c.getint(GROUP, "Done" + str(STAGES[d]["id"])) == 1
    return {k: dict(c[k]) for k in c.sections()}


try:
    s.protect()
    key("r")
    time.sleep(0.8)
    s.protect()
    station("boss6.ini", [])
    snap("mario-start")
    s.set_value(obj("Active 27"), 0, 50)
    time.sleep(1.2)
    snap("vvvvvv-arrival")
    report["after_mario"] = station("save4.ini", ["boss6.ini"])
    key("q")
    time.sleep(0.7)
    report["death_in_vvvvvv"] = not any(o["name"] == "Player" for o in s.objects())
    assert report["death_in_vvvvvv"]
    snap("vvvvvv-death")
    key("r")
    time.sleep(0.8)
    s.protect()
    station("save4.ini", ["boss6.ini"])
    snap("vvvvvv-restart")
    # Native region gate must first see player outside, then inside Gravitron's room.
    s.position(obj("Player"), 2400, 1500)
    time.sleep(0.3)
    station("save4.ini", ["boss6.ini"])
    s.position(obj("Player"), 2680, 1600)
    time.sleep(1.2)
    snap("castlevania-arrival")
    report["after_vvvvvv"] = station("save7.ini", ["boss6.ini", "save4.ini"])
    key("q")
    time.sleep(0.7)
    report["death_in_castlevania"] = not any(o["name"] == "Player" for o in s.objects())
    assert report["death_in_castlevania"]
    key("r")
    time.sleep(0.8)
    report["after_restart"] = station("save7.ini", ["boss6.ini", "save4.ini"])
    report["alive_after_restart"] = wait_player()
    assert report["alive_after_restart"]
    snap("castlevania-restart")
    report["same_process"] = s.b.read(s.b.ready["base"], 2) == b"MZ"
    assert report["same_process"]
    report["passed"] = True
finally:
    (OUT / "result.json").write_text(json.dumps(report, indent=2))
    s.close()
print(
    json.dumps(
        {
            k: report[k]
            for k in [
                "passed",
                "same_process",
                "death_in_vvvvvv",
                "death_in_castlevania",
                "alive_after_restart",
            ]
        }
    )
)
