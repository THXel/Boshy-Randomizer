"""Native rejection and mouse/real-pipe checks in private unified run fixtures."""

import json
import time
import uuid
import subprocess
from functools import partial
from menu_host.store import Store, save
from menu_host.draft import Draft
from export_native_run import export
from native_menu.unified import PreparedController, read_session
from native_menu_probe import pump, key
from native_unified_live import OUT, until
from native_rewards_live import write_save
from native_menu.observe import objects
from native_menu.transport import read, write
from gameplay.target_plan import GROUP as TARGET
from transition.router import GROUP as ROUTE, STAGES
import god_mode_live as capture


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, cases=[], memory_writes=0)
    try:
        for name in (
            "bad-frame",
            "bad-difficulty",
            "bad-version",
            "missing-save",
            "target-pipe",
        ):
            s = Store(
                OUT / (name + "-" + uuid.uuid4().hex[:6]),
                exporter=partial(export, unified=True),
            )
            with s.lock():
                d = Draft()
                d.set_mode("target" if name == "target-pipe" else "normal")
                d.update(god_mode=True, no_mouse_ghost=True, characters=True)
                d.seed = "DEADBEEF"
                s.create(1, d)
                c = PreparedController(s)
                save_path = c.folder / "SaveFile1.ini"
                backup = save_path.read_bytes()
                fixture = save(save_path)
                if name == "bad-frame":
                    fixture["Positions"]["frame"] = "2"
                if name == "bad-difficulty":
                    fixture["Stats"]["Difficulty"] = "4"
                if name == "bad-version":
                    fixture["Check"]["SaveVersion"] = "999"
                if name == "target-pipe":
                    fixture["Positions"]["xpos"] = "4415"
                    fixture["Positions"]["ypos"] = "400"
                if name == "missing-save":
                    save_path.unlink()
                else:
                    write_save(save_path, fixture)
                case = dict(name=name, folder=str(c.folder))
                report["cases"].append(case)
                print("START", name, flush=True)
                try:
                    c.open()
                    c.enter()
                    pump(c, 0.3)
                    identity = (c.window.pid, c.window.window)
                    if name != "target-pipe":
                        # Bypass only the host validator to test Fusion's own refusal.
                        view = read(c.folder / "native-view.ini")
                        view["begin"] += 1
                        write(c.folder / "native-view.ini", view)
                        deadline = time.monotonic() + 5
                        while time.monotonic() < deadline:
                            state = read_session(c.folder)
                            if state.getint("Session", "Status", fallback=0) == 3:
                                break
                            time.sleep(0.1)
                        assert state.getint("Session", "Status") == 3, dict(
                            state["Session"]
                        )
                        assert c.window.reader.frame() == "Title Screen"
                        time.sleep(0.4)
                        assert c.window.reader.frame() == "Title Screen"
                        case["native_rejected"] = dict(state["Session"])
                    else:
                        # Real click on the displayed Resume button.
                        subprocess.run(["wmctrl", "-ia", c.window.window], check=True)
                        subprocess.run(
                            [
                                "xdotool",
                                "mousemove",
                                "--window",
                                c.window.window,
                                "495",
                                "349",
                                "click",
                                "1",
                            ],
                            check=True,
                        )
                        until(c, lambda: c.phase == "playing")
                        subprocess.run(["xdotool", "keydown", "Right"], check=True)
                        try:
                            time.sleep(0.35)
                        finally:
                            subprocess.run(["xdotool", "keyup", "Right"], check=True)
                        until(
                            c,
                            lambda: c.window.reader.frame()
                            != "First World - Prehistorik",
                        )
                        time.sleep(0.4)
                        state = save(save_path)
                        assert state.getint(TARGET, "Visit") == 1
                        assert (
                            state.getint(ROUTE, "Done" + str(STAGES["save1.ini"]["id"]))
                            == 1
                        )
                        assert any(
                            o["name"] == "Player" for o in objects(c.window.reader)
                        )
                        case.update(
                            destination=c.window.reader.frame(),
                            visit=1,
                            real_pipe=True,
                            mouse_start=True,
                        )
                        capture.snap(c.window, "unified-target-real-pipe")
                        c.window.key("F2")
                        until(c, lambda: c.phase == "menu")
                        key(c, "Return")
                        until(c, lambda: c.phase == "playing")
                        assert c.window.reader.frame() == case["destination"]
                        assert save(save_path).getint(TARGET, "Visit") == 1
                        case["resume_preserved_destination"] = True
                    assert (
                        identity == (c.window.pid, c.window.window) and c.window.owned()
                    )
                    case.update(same_process=True, passed=True)
                finally:
                    c.window.close()
                    s.active = None
                    if name != "target-pipe":
                        save_path.write_bytes(backup)
                    if c.clipboard:
                        c.clipboard.close()
                    s.resume(1)
        report["passed"] = True
    except BaseException as error:
        report["error"] = repr(error)
        raise
    finally:
        (OUT / "edge-results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
