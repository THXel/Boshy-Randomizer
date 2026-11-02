"""Display preference survives the standard menu-to-game process handoff."""

import json
import time
import uuid
from Xlib import display
from native_menu.classic import ClassicController
from native_menu.display import Settings, save as save_display
from native_menu_probe import pump
from native_menu.observe import objects
from menu_host.store import Store, digest, save
from menu_host.draft import Draft
from export_route_probe import ROOT
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-Modernization-20261025"


def main():
    capture.OUT = OUT
    store = Store(OUT / ("display-run-profile-" + uuid.uuid4().hex[:8]))
    report = {"memory_writes": 0}
    with store.lock():
        draft = Draft()
        draft.set_mode("normal")
        draft.update(god_mode=True, no_mouse_ghost=True)
        draft.select_pack("blood_pack", "wannafest22")
        store.create(1, draft)
        save_display(store.root, Settings("16:9", 720))
        c = ClassicController(store)
        try:
            c.open()
            c.enter()
            c.window.key("Return")
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                c.tick()
                if store.active and c.runtime.owned():
                    break
                time.sleep(0.05)
            else:
                raise AssertionError("Native save confirmation did not start game")
            pump(c, 0.6)
            runtime = c.runtime
            connection = display.Display()
            try:
                window = connection.create_resource_object(
                    "window", int(runtime.window, 16)
                )
                geometry = window.get_geometry()
                position = connection.screen().root.translate_coords(window, 0, 0)
            finally:
                connection.close()
            assert (geometry.width, geometry.height) == (1280, 720)
            assert runtime.reader.frame() == "First World - Prehistorik"
            assert (
                save(runtime.folder / "SaveFile1.ini").getint(
                    "FusionBloodV1", "Animation"
                )
                == 17
            )
            report.update(
                frame=runtime.reader.frame(),
                size=[geometry.width, geometry.height],
                position=[position.x, position.y],
                sha256=digest(runtime.folder / "Boshy.exe"),
            )
            capture.snap(runtime, "display-run-16-9")
            runtime.key("q")
            time.sleep(0.2)
            particles = [
                o
                for o in objects(runtime.reader)
                if o["name"] == "Active 2" and (o["w"], o["h"]) == (20, 20)
            ]
            assert particles
            capture.snap(runtime, "display-run-wannafest-blood")
            runtime.key("r")
            pump(c, 0.5)
            runtime.key("F2")
            deadline = time.monotonic() + 25
            while time.monotonic() < deadline:
                c.tick()
                if not store.active and c.window.owned():
                    break
                time.sleep(0.05)
            else:
                raise AssertionError("Return to menu timed out")
            assert c.model.display == Settings("16:9", 720)
            report.update(
                passed=True,
                native_save_confirmation=True,
                player_blood=True,
                return_to_menu=True,
            )
        except BaseException as error:
            report["error"] = repr(error)
            raise
        finally:
            c.close()
            (OUT / "display-run-live-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
