"""Check the actual main-menu X icon and its native author-profile click."""

import json
import subprocess
import uuid
from export_route_probe import ROOT
from menu_host.store import Store, digest
from native_menu.classic import ClassicController
from native_menu.observe import objects
from native_menu_probe import pump
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-Social-20261025"


def main():
    OUT.mkdir(exist_ok=True)
    capture.OUT = OUT
    report = dict(scope=__doc__, memory_writes=0)
    store = Store(OUT / ("profile-" + uuid.uuid4().hex[:8]))
    with store.lock():
        c = ClassicController(store)
        try:
            c.open()
            c.enter()
            pump(c, 0.5)
            icon = next(o for o in objects(c.window.reader) if o["name"] == "Active 11")
            assert (icon["w"], icon["h"]) == (32, 32)
            assert (icon["x"], icon["y"]) == (107, 448)
            before = (c.model.slot, c.model.draft.shared(), c.model.page)
            capture.point(c.window, 600, 50)
            capture.snap(c.window, "main-menu-x-link")
            report["game_sha256"] = digest(c.folder / "Boshy.exe")
            capture.point(c.window, 170, 448)
            subprocess.run(["xdotool", "click", "1"], check=True)
            titles = []
            for _ in range(20):
                pump(c, 0.25)
                titles = subprocess.check_output(
                    ["wmctrl", "-l"], text=True
                ).splitlines()
                if any("Soulgryn" in title and "Firefox" in title for title in titles):
                    break
            report["browser_titles"] = [title for title in titles if "Firefox" in title]
            report["profile_link_verified"] = any(
                "Soulgryn" in title and "Firefox" in title for title in titles
            )
            report["clicked_menu_coordinate"] = [170, 448]
            assert (c.model.slot, c.model.draft.shared(), c.model.page) == before
            report.update(
                native_icon=icon,
                native_click=True,
                menu_unchanged=True,
                visual_and_browser_verification="pending",
            )
        except BaseException as error:
            report["error"] = repr(error)
            raise
        finally:
            c.close()
            (OUT / "label-live-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(json.dumps(report))


if __name__ == "__main__":
    main()
