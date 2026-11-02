"""Live same-frame station split plus native Kracko victory/reset fixtures."""

import configparser, json, os, runpy, subprocess, time
from pathlib import Path
from Xlib import X, display
from PIL import Image
from phase_state import State
from transition.router import GROUP, STAGES

ROOT = Path(__file__).resolve().parents[2]
CASE = "rebuilt-split-routes"
LAB = (
    Path("/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshySceneTests") / CASE
)
OUT = ROOT / "outputs/Fusion-Routes-20261023/live-split-kracko"
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
subprocess.run(["xdotool", "mousemove", "1910", "1040"])
rc4 = runpy.run_path(str(ROOT / "work/Boshy-Randomizer/src/shared/PY/rc4_utils.py"))[
    "rc4_crypt"
]
s = State(CASE)
report = {
    "scope": "synthetic position and HP fixtures, native victory and transition events",
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


def objs(name):
    return [o for o in s.objects() if o["name"] == name]


def obj(name):
    return objs(name)[0]


def wait_for(test, seconds=6):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if test():
            return
        time.sleep(0.15)
    raise AssertionError("Timed out waiting for runtime condition")


def station(spot):
    c = saved()
    assert c.getint(GROUP, "CurrentStage") == STAGES[spot]["id"], dict(c[GROUP])
    assert c.getint("Positions", "frame") == STAGES[spot]["frame"]
    return {k: dict(c[k]) for k in c.sections()}


def kill_kracko():
    s.position(obj("Player"), 3400, 300)
    s.set_value(obj("Active 83"), 1, 0)
    wait_for(lambda: not objs("Active 83"), 10)
    time.sleep(0.5)


def unprotect():
    s.refresh()
    bank = s.b.u32(s.run + 0x88)
    for change in list(s.writes):
        if (
            change["reason"] == "temporary zero-count Die fastloop for visual fixture"
            and bank <= change["address"] < bank + 2000000
            and s.b.u32(change["address"]) == 0
        ):
            s.cas(change["address"], 0, 1, "restore current event bank death calls")


try:
    s.protect()
    key("r")
    wait_for(lambda: bool(objs("Player")))
    s.protect()
    report["start"] = station("save2.ini")
    snap("green-greens-start")
    s.position(obj("Player"), 3300, 300)
    wait_for(lambda: saved().getint(GROUP, "CurrentStage") == STAGES["boss2.ini"]["id"])
    wait_for(lambda: bool(objs("Active 83")))
    time.sleep(0.5)
    report["kracko_arrival"] = station("boss2.ini")
    assert saved().getint(GROUP, "Done" + str(STAGES["save2.ini"]["id"])) == 1
    snap("kracko-same-frame-arrival")
    s.protect()
    s.position(obj("Player"), 3920, 200)
    time.sleep(0.5)
    station("boss2.ini")
    assert objs("Active 83")
    report["premature_exit_blocked"] = True
    snap("exit-before-win-blocked")
    kill_kracko()
    snap("kracko-native-victory")
    station("boss2.ini")
    unprotect()
    key("q")
    wait_for(lambda: not objs("Player"))
    snap("death-before-exit")
    key("r")
    wait_for(lambda: bool(objs("Player")))
    wait_for(lambda: bool(objs("Active 83")))
    s.protect()
    s.position(obj("Player"), 3920, 200)
    time.sleep(0.5)
    station("boss2.ini")
    assert objs("Active 83")
    report["death_clears_victory"] = True
    snap("reset-before-win-blocked")
    kill_kracko()
    s.position(obj("Player"), 3920, 200)
    wait_for(lambda: saved().getint(GROUP, "CurrentStage") == STAGES["save7.ini"]["id"])
    wait_for(lambda: bool(objs("Player")))
    time.sleep(0.3)
    report["castlevania_arrival"] = station("save7.ini")
    assert saved().getint(GROUP, "Done" + str(STAGES["boss2.ini"]["id"])) == 1
    snap("castlevania-arrival")
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
                "premature_exit_blocked",
                "death_clears_victory",
            ]
        }
    )
)
