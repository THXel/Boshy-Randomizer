"""Bounded live comparison runs; synthetic starting save, real runtime afterwards."""

from pathlib import Path
import argparse, os, subprocess, time, runpy, json, hashlib
from Xlib import display, X
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PREFIX = Path("/home/thxel/Games/clickteam-fusion-developer")
WINE = "/home/thxel/.local/share/lutris/runners/wine/wine-staging-11.2-x86_64/bin/wine"
EXES = {
    "original": Path(
        "/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe"
    ),
    "rebuilt": PREFIX / "drive_c/BoshyGraphics/Boshy-alpha-fixed.exe",
}
SCENES = {
    "mario-routes": (10, 1400, 400),
    "kracko-routes": (5, 3400, 300),
    "split-routes": (5, 30, 1850),
    "prehistorik": (3, 200, 226),
    "sonic": (14, 100, 100),
    "old-sonic": (60, 100, 100),
    "solgryn": (46, 100, 100),
    "castlevania": (15, 30, 1300),
    "cheetah": (54, 100, 100),
    "cheetah-seed": (54, 100, 100),
    "kracko-exit": (5, 3400, 300),
    "kracko-links": (5, 3400, 300),
    "cheetah-links": (54, 100, 100),
    "mario-links": (10, 1400, 400),
    "mario-exit": (10, 1400, 400),
    "cheetah-exit": (54, 100, 100),
}
from route_cases import CASES
from build_profiles import BUILDS, executable
from transition.router import STAGES

SCENES.update(
    {
        name: tuple(STAGES[spot][k] for k in ("frame", "x", "y"))
        for name, spot in CASES.items()
    }
)
p = argparse.ArgumentParser()
p.add_argument("--route-build", choices=BUILDS, default="base")
p.add_argument("variant", choices=EXES)
p.add_argument("scene", choices=SCENES)
p.add_argument("--shoot", action="store_true")
p.add_argument("--seconds", type=float, default=12)
p.add_argument("--leave-open", action="store_true")
p.add_argument("--output-group", default="Fusion-Graphics-20261023")
p.add_argument("--route", type=int, default=1)
p.add_argument("--keep-save", action="store_true")
p.add_argument("--save-fixture", type=Path)
a = p.parse_args()
if a.route_build != "base" and (
    a.variant != "rebuilt" or not a.scene.endswith("-routes")
):
    p.error("Guard build requires a rebuilt route scene")
case_name = f"{a.variant}-{a.scene}" + BUILDS[a.route_build][2]
if a.keep_save and a.save_fixture:
    p.error("Choose keep-save OR save-fixture")


def windows():
    return [
        l.split(None, 4)
        for l in subprocess.check_output(["wmctrl", "-lp"], text=True).splitlines()
        if l.endswith(" I Wanna Be The Boshy")
    ]


if windows():
    raise SystemExit("Close prior Boshy test before starting this isolated run")
assert "/" not in a.output_group and ".." not in a.output_group
out = ROOT / "outputs" / a.output_group / case_name
out.mkdir(parents=True, exist_ok=False)
lab = PREFIX / "drive_c/BoshySceneTests" / case_name
lab.mkdir(parents=True, exist_ok=True)
if a.scene == "cheetah":
    EXES["rebuilt"] = PREFIX / "drive_c/BoshyTransitions/Boshy-transition.exe"
if a.scene == "cheetah-seed":
    EXES["rebuilt"] = PREFIX / "drive_c/BoshyTransitions/Boshy-seed.exe"
if a.scene.endswith("-exit"):
    EXES["rebuilt"] = PREFIX / "drive_c/BoshyTransitions/Boshy-boss-exits.exe"
if a.scene.endswith("-links"):
    EXES["rebuilt"] = PREFIX / "drive_c/BoshyTransitions/Boshy-frame-links.exe"
if a.scene.endswith("-routes"):
    EXES["rebuilt"] = PREFIX / "drive_c/BoshyTransitions/Boshy-routes.exe"
if a.scene.endswith("-routes"):
    EXES["rebuilt"] = executable(a.route_build)
exe = lab / "Boshy.exe"
if not exe.exists():
    os.link(EXES[a.variant], exe)
assert (
    hashlib.sha256(exe.read_bytes()).digest()
    == hashlib.sha256(EXES[a.variant].read_bytes()).digest()
), "Stale test executable"
rc = runpy.run_path(str(ROOT / "work/Boshy-Randomizer/src/shared/PY/rc4_utils.py"))[
    "rc4_crypt"
]
frame, x, y = SCENES[a.scene]
fixture = f"[Check]\r\nSaveVersion=1\r\n[Stats]\r\nDeaths=0\r\nDifficulty=0\r\nTimeSeconds=0\r\n[Collectables]\r\nAwesomesauce=0\r\n[Positions]\r\nframe={frame}\r\nxPos={x}\r\nyPos={y}\r\n"
if a.scene == "cheetah":
    fixture += f"[FusionRandoV1]\r\nCheetahRoute={a.route}\r\n" if a.route >= 0 else ""
save = lab / "SaveFile1.ini"
if a.save_fixture:
    save.write_bytes(a.save_fixture.read_bytes())
if not a.keep_save and not a.save_fixture:
    save.write_bytes(rc(b"BLOB", fixture.encode("latin1")))
else:
    assert save.exists()
    fixture = rc(b"BLOB", save.read_bytes()).decode("latin1")
    import configparser

    loaded = configparser.ConfigParser()
    loaded.read_string(fixture)
    frame = loaded.getint("Positions", "frame")
    x = loaded.getint("Positions", "xPos")
    y = loaded.getint("Positions", "yPos")
(out / "fixture.txt").write_text(fixture)
env = os.environ.copy()
env.update(WINEPREFIX=str(PREFIX), WINEDEBUG="-all")
log = (out / "runtime.log").open("w")
proc = subprocess.Popen(
    [WINE, str(exe)],
    cwd=lab,
    env=env,
    stdout=log,
    stderr=subprocess.STDOUT,
    start_new_session=True,
)
start = time.monotonic()
row = None
while time.monotonic() - start < 20:
    rows = windows()
    if rows:
        row = rows[0]
        break
    time.sleep(0.25)
if row is None:
    raise SystemExit("No game window")
wid = row[0]
D = display.Display()
w = D.create_resource_object("window", int(wid, 16))
g = w.get_geometry()
root = D.screen().root.get_geometry()
r = D.screen().root.translate_coords(w, 0, 0)
park = max(
    [
        (5, 5),
        (root.width - 5, 5),
        (5, root.height - 5),
        (root.width - 5, root.height - 5),
    ],
    key=lambda p: (p[0] - r.x - g.width / 2) ** 2 + (p[1] - r.y - g.height / 2) ** 2,
)
subprocess.run(["wmctrl", "-ia", wid], check=True)
subprocess.run(["xdotool", "mousemove", *map(str, park)], check=True)


def key(k, seconds=0.25):
    subprocess.run(["wmctrl", "-ia", wid], check=True)
    time.sleep(0.1)
    subprocess.run(["xdotool", "keydown", k], check=True)
    time.sleep(seconds)
    subprocess.run(["xdotool", "keyup", k], check=True)


def grab():
    i = w.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
    return Image.frombytes("RGB", (g.width, g.height), i.data, "raw", "BGRX")


def snap(name):
    im = grab()
    im.save(out / (name + ".png"))
    return im


reference = Image.open(
    ROOT / "outputs/Fusion-Baseline-20261023/original-checkpoint-slot.png"
).convert("RGB")
from scene_detection import is_slot_menu


def is_menu():
    return is_slot_menu(grab(), reference)


time.sleep(4)
snap("title")
for _ in range(2):
    key("Return")
    time.sleep(2)
snap("slot")
key("Return")
time.sleep(1)
for attempt in range(15):
    if not is_menu():
        break
    key("Return")
    time.sleep(2)
if is_menu():
    raise SystemExit("Scene did not leave menu; no gameplay verdict")
snap("entry")
if a.shoot:
    subprocess.run(["xdotool", "keydown", "x"], check=True)
try:
    for n in range(int(a.seconds * 2)):
        time.sleep(0.5)
        snap(f"frame-{n:03}")
finally:
    if a.shoot:
        subprocess.run(["xdotool", "keyup", "x"])
snap("end")
key("r")
time.sleep(0.5)
snap("restart")
result = {
    "variant": a.variant,
    "scene": a.scene,
    "frame": frame,
    "start": [x, y],
    "synthetic_start": not a.keep_save,
    "reused_save": a.keep_save,
    "imported_fixture": str(a.save_fixture) if a.save_fixture else None,
    "shoot": a.shoot,
    "duration": a.seconds,
    "window": wid,
    "pid": row[2],
    "exe_sha256": hashlib.file_digest(exe.open("rb"), "sha256").hexdigest(),
    "save_after": rc(b"BLOB", save.read_bytes()).decode("latin1"),
}
(out / "result.json").write_text(json.dumps(result, indent=2))
if not a.leave_open:
    subprocess.run(["wmctrl", "-ic", wid])
    time.sleep(0.7)
print(json.dumps(result), flush=True)
