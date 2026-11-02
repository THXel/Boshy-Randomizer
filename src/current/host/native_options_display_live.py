"""Exercise the original Options room using real keys and read-only observation."""

import json
import time
import configparser
import uuid
from Xlib import display
from native_menu.classic import ClassicController
from native_classic_live import enter_title, trigger, wait
from native_menu_probe import pump
from menu_host.store import Store, save
from native_menu.display import Settings, load
from export_route_probe import ROOT
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-Modernization-20261025"


def main():
    capture.OUT = OUT
    store = Store(OUT / ("options-profile-" + uuid.uuid4().hex[:8]))
    c = ClassicController(store)
    report = {"checks": [], "folder": str(c.folder), "memory_writes": 0}
    seed = c.model.draft.shared()

    def state(label, expected):
        connection = display.Display()
        try:
            window = connection.create_resource_object(
                "window", int(c.window.window, 16)
            )
            geometry = window.get_geometry()
        finally:
            connection.close()
        deadline = time.monotonic() + 2
        while True:
            try:
                cfg = save(c.folder / "options.ini")
                if not cfg.has_section("Options"):
                    raise ValueError("Native write still in progress")
                break
            except (ValueError, OSError, configparser.Error):
                if time.monotonic() >= deadline:
                    raise
                time.sleep(0.03)
        data = {
            "label": label,
            "frame": c.window.reader.frame(),
            "size": [geometry.width, geometry.height],
            "options": dict(cfg.items("Options")),
            "preference": str(c.model.display),
        }
        report["checks"].append(data)
        print(json.dumps(data), flush=True)
        capture.snap(c.window, label)
        assert c.model.display == expected, data
        assert (geometry.width, geometry.height) == expected.size, data
        assert c.model.draft.shared() == seed

    try:
        c.open()
        enter_title(c)
        pump(c, 1)
        if trigger(c)[1] != -1:
            c.window.key("Return")
            wait(c, lambda: trigger(c)[1] == -1)
        capture.snap(c.window, "initial-menu-x-link")
        c.window.key("Down")
        pump(c, 0.2)
        c.window.key("Return")
        wait(c, lambda: c.window.reader.frame() == "Options")
        pump(c, 0.5)
        state("original-options-before", Settings())
        for _ in range(2):
            c.window.key("Down")
            pump(c, 0.3)
        capture.snap(c.window, "original-display-selected")
        for key, label, expected in (
            ("Right", "original-display-720-4-3", Settings("4:3", 720)),
            ("Return", "original-display-720-16-9", Settings("16:9", 720)),
            ("Right", "original-display-1080-16-9", Settings("16:9", 1080)),
            ("Left", "original-display-720-restored", Settings("16:9", 720)),
        ):
            c.window.key(key)
            pump(c, 0.7)
            state(label, expected)
        c.window.key("Escape")
        wait(c, lambda: c.window.reader.frame() == "Title Screen")
        pump(c, 0.5)
        state("menu-display-after-options", Settings("16:9", 720))
        c.close()
        assert load(store.root) == Settings("16:9", 720)
        c = ClassicController(store)
        # A new empty draft intentionally receives a new seed on app restart.
        # Display operations must preserve that draft's own seed.
        seed = c.model.draft.shared()
        c.open()
        enter_title(c)
        pump(c, 0.5)
        state("menu-display-after-restart", Settings("16:9", 720))
        report["passed"] = True
    except BaseException as error:
        report["error"] = repr(error)
        raise
    finally:
        c.close()
        (OUT / "original-options-live-results.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )


if __name__ == "__main__":
    main()
