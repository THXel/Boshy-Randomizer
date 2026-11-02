"""Shared bounded controls for one hash-checked, path-scoped live route test."""

import configparser
import json
import os
from pathlib import Path
import runpy
import subprocess
import time
from Xlib import X, display
from PIL import Image
from phase_state import State, RuntimeNotReady
from phase_inspect import MemoryReadUnavailable
from transition.router import GROUP, STAGES
from build_profiles import BUILDS, case_name

ROOT = Path(__file__).resolve().parents[2]
PREFIX = Path("/home/thxel/Games/clickteam-fusion-developer")


class LiveRouteSession:
    def __init__(self, scene, out, build="base"):
        assert build in BUILDS
        self.case = case_name(scene, build)
        self.lab = PREFIX / "drive_c/BoshySceneTests" / self.case
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=False)
        rows = [
            r.split(None, 4)
            for r in subprocess.check_output(["wmctrl", "-lp"], text=True).splitlines()
            if r.endswith(" I Wanna Be The Boshy")
        ]
        assert len(rows) == 1
        self.window, self.pid = rows[0][0], rows[0][2]
        assert Path(os.readlink("/proc/" + self.pid + "/cwd")) == self.lab
        self.display = display.Display()
        self.drawable = self.display.create_resource_object(
            "window", int(self.window, 16)
        )
        self.size = self.drawable.get_geometry()
        self.state = State(self.case)
        self.rc4 = runpy.run_path(
            str(ROOT / "work/Boshy-Randomizer/src/shared/PY/rc4_utils.py")
        )["rc4_crypt"]
        self.report = {
            "scope": "isolated synthetic input fixtures; original engine events",
            "case": self.case,
            "pid": self.pid,
            "writes": self.state.writes,
        }
        subprocess.run(["wmctrl", "-ia", self.window], check=True)
        subprocess.run(["xdotool", "mousemove", "1910", "1040"], check=True)

    def key(self, key, seconds=0.25):
        subprocess.run(["wmctrl", "-ia", self.window], check=True)
        time.sleep(0.1)
        subprocess.run(["xdotool", "keydown", key], check=True)
        try:
            time.sleep(seconds)
        finally:
            subprocess.run(["xdotool", "keyup", key], check=True)

    def objects(self, name):
        return [o for o in self.state.objects() if o["name"] == name]

    def obj(self, name):
        found = self.objects(name)
        assert len(found) == 1, (name, found)
        return found[0]

    def wait(self, predicate, seconds=8):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            try:
                if predicate():
                    return
            except (RuntimeNotReady, MemoryReadUnavailable):
                pass
            time.sleep(0.15)
        raise AssertionError("Timed out waiting for runtime condition")

    def saved(self):
        # INI++ rewrites in place. A short empty/partial read during that write
        # must not be mistaken for permanently lost route data.
        for attempt in range(10):
            c = configparser.ConfigParser()
            try:
                c.read_string(
                    self.rc4(b"BLOB", (self.lab / "SaveFile1.ini").read_bytes()).decode(
                        "latin1"
                    )
                )
                if c.has_section(GROUP):
                    return c
            except configparser.Error:
                if attempt == 9:
                    raise
            if attempt < 9:
                self.report["save_read_retries"] = (
                    self.report.get("save_read_retries", 0) + 1
                )
                time.sleep(0.03)
        raise AssertionError(
            "Route section still absent after bounded save-read retries"
        )

    def station(self, spot):
        c = self.saved()
        assert c.getint(GROUP, "CurrentStage") == STAGES[spot]["id"], dict(c[GROUP])
        assert c.getint("Positions", "frame") == STAGES[spot]["frame"], dict(
            c["Positions"]
        )
        expected_names = json.loads(
            (ROOT / "work/fusion-lab/transition/frame_names.json").read_text()
        )
        actual_name = self.state.frame_name()
        assert actual_name == expected_names[str(STAGES[spot]["frame"])], (
            spot,
            actual_name,
        )
        return {
            **{k: dict(c[k]) for k in c.sections()},
            "_runtime": {"frame_name": actual_name},
        }

    def arrival(self, spot, label):
        self.wait(
            lambda: self.saved().getint(GROUP, "CurrentStage") == STAGES[spot]["id"]
        )
        self.wait(lambda: bool(self.objects("Player")))
        time.sleep(0.3)
        self.report[label] = self.station(spot)
        self.snap(label)

    def snap(self, label):
        g = self.size
        im = self.drawable.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
        Image.frombytes("RGB", (g.width, g.height), im.data, "raw", "BGRX").save(
            self.out / (label + ".png")
        )

    def position(self, x, y):
        self.state.position(self.obj("Player"), x, y)

    def protect(self):
        self.state.protect()

    def unprotect(self):
        self.state.refresh()
        bank = self.state.b.u32(self.state.run + 0x88)
        for change in list(self.state.writes):
            if (
                change["reason"]
                == "temporary zero-count Die fastloop for visual fixture"
                and bank <= change["address"] < bank + 2000000
                and self.state.b.u32(change["address"]) == 0
            ):
                self.state.cas(
                    change["address"], 0, 1, "restore current test death calls"
                )

    def restart(self, spot):
        self.key("r")
        self.wait(lambda: bool(self.objects("Player")))
        time.sleep(0.4)
        self.station(spot)

    def death_restart(self, spot, label):
        self.unprotect()
        self.key("q")
        self.wait(lambda: not self.objects("Player"))
        self.snap(label + "-death")
        self.restart(spot)
        self.report[label + "-restart"] = self.station(spot)
        self.snap(label + "-restart")

    def finish(self, error=None):
        if error is not None:
            self.report["error"] = repr(error)
            try:
                self.snap("failure")
            except Exception:
                pass
        self.report["same_process"] = (
            self.state.b.read(self.state.b.ready["base"], 2) == b"MZ"
        )
        self.report["passed"] = error is None
        (self.out / "result.json").write_text(json.dumps(self.report, indent=2))
        self.state.close()
        subprocess.run(["wmctrl", "-ic", self.window], check=True)
        time.sleep(0.8)
