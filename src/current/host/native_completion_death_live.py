"""Candidate gameplay checks: real Q/R, pack changes, post-credit save fixture.

Fixture modifies only an isolated test save for the Prize Room screen check.
No process-memory writes, forced kills, or desktop-wide captures are used.
"""

import io
import json
import subprocess
import time
import uuid
from functools import partial
from pathlib import Path
from native_menu import builds
from menu_host.store import Store, digest, save, RC4


def main():
    exe = builds.PREFIX / "drive_c/BoshyTransitions/Boshy-dynamic-v29.exe"
    builds.DYNAMIC_BASE, builds.DYNAMIC_SHA = exe, digest(exe)
    from export_native_run import export
    from export_route_probe import ROOT
    from menu_host.draft import Draft
    from native_menu.combined import CombinedController
    from native_menu_probe import pump
    from native_menu_lifecycle_probe import wait_for
    from native_menu.observe import objects
    from god_mode_boss_probe import values
    from blood_enemy_probe import streams
    from visuals.death_screen import NAME
    from transition.router import GROUP
    import god_mode_live as capture

    out = ROOT / "outputs/Fusion-Completion-20261026"
    capture.OUT = out
    report = dict(build=str(exe), sha256=builds.DYNAMIC_SHA, memory_writes=0, cases=[])
    store = Store(
        out / ("death-" + uuid.uuid4().hex[:8]), exporter=partial(export, dynamic=True)
    )
    with store.lock():
        for slot, pack in enumerate(("kamilia3", "wannafest22", "original"), 1):
            d = Draft()
            d.set_mode("normal")
            d.update(
                god_mode=True,
                no_mouse_ghost=True,
                start_character="Boshy",
                characters=False,
                sprite_actors=True,
                sprite_scenery=True,
                sprite_backgrounds=True,
                sprite_tiles=True,
                sprite_decor=True,
            )
            d.select_pack("blood_pack", pack)
            d.seed = "DEATH027"
            store.create(slot, d)
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            for slot, pack in enumerate(("kamilia3", "wannafest22", "original"), 1):
                c.model.slot = slot
                c.model.load_slot()
                c.begin()
                wait_for(c, lambda: c.phase == "playing", seconds=25)
                pump(c, 0.6)
                obs = objects(c.window.reader)
                assert sum(o["name"] == "Player" for o in obs) == 1
                panel = next(o for o in obs if o["name"] == NAME)
                assert values(c.window.reader, panel, 1) == [0]
                case = dict(pack=pack, samples=[])
                report["cases"].append(case)
                audio = streams()
                assert len(audio) == 1, audio
                path = out / (pack + "-death.s16le")
                with path.open("wb") as target:
                    recorder = subprocess.Popen(
                        [
                            "parec",
                            "--monitor-stream=" + str(audio[0]["index"]),
                            "--rate=22050",
                            "--channels=2",
                            "--format=s16le",
                        ],
                        stdout=target,
                        stderr=subprocess.DEVNULL,
                    )
                    try:
                        pump(c, 0.5)
                        case["death_sample"] = path.stat().st_size // 4
                        c.window.key("q")
                        for delay in (0.15, 0.6, 1.2, 3):
                            pump(c, delay)
                            obs = objects(c.window.reader)
                            assert not any(o["name"] == "Player" for o in obs)
                            panel = next(o for o in obs if o["name"] == NAME)
                            state = values(c.window.reader, panel, 1)[0]
                            assert state == (pack != "original"), (pack, state)
                            case["samples"].append(
                                dict(delay=delay, screen=panel, active=state)
                            )
                            capture.snap(c.window, pack + "-death-" + str(delay))
                    finally:
                        recorder.terminate()
                        recorder.wait(timeout=3)
                c.window.key("r")
                pump(c, 1)
                obs = objects(c.window.reader)
                assert sum(o["name"] == "Player" for o in obs) == 1
                panel = next(o for o in obs if o["name"] == NAME)
                assert values(c.window.reader, panel, 1) == [0]
                capture.snap(c.window, pack + "-retry")
                # Immediate retry interrupts even the long WannaFest sequence.
                c.window.key("q")
                pump(c, 0.05)
                c.window.key("r")
                pump(c, 0.5)
                assert sum(o["name"] == "Player" for o in objects(c.window.reader)) == 1
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu")
                c.enter()
                case["retry_passed"] = True
                print("PASS death", pack, flush=True)
            # Prepared completed save checks rendering/input, not a claim of a natural full run.
            path = store.folder(3) / "SaveFile1.ini"
            cfg = save(path)
            cfg["Positions"].update(frame="49", xpos="320", ypos="240")
            cfg[GROUP]["Completed"] = "1"
            buf = io.StringIO()
            cfg.write(buf)
            path.write_bytes(RC4(b"BLOB", buf.getvalue().encode("latin1")))
            c.model.slot = 3
            c.model.load_slot()
            c.begin()
            wait_for(c, lambda: c.phase == "playing", seconds=25)
            pump(c, 1)
            assert c.window.reader.frame() == "Prize Room", c.window.reader.frame()
            assert c.completion.data is not None, c.completion.last_error
            for lang in ("de", "en", "es", "ru", "ja"):
                c.model.language = lang
                c.completion.publish()
                pump(c, 0.3)
                capture.snap(c.window, "result-" + lang)
            c.window.key("F6")
            pump(c, 0.5)
            assert c.completion.copy_sequence == 1, c.completion.last_error
            capture.snap(c.window, "result-seed-copied")
            report["result_fixture"] = dict(
                post_credits_room=True,
                languages=5,
                copy_sequence=1,
                data=c.completion.data,
            )
            c.window.key("F2")
            wait_for(c, lambda: c.phase == "menu")
            report["passed"] = True
            print("PASS result screen", flush=True)
        except BaseException as err:
            report["error"] = repr(err)
            raise
        finally:
            try:
                c.close()
            finally:
                (out / "death-result-v29-live.json").write_text(
                    json.dumps(report, indent=2) + "\n"
                )


if __name__ == "__main__":
    main()
