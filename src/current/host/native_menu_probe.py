"""Real native-menu keys/clicks; read-only engine observation, no injected hooks."""

import json, time, subprocess
from export_route_probe import ROOT
from menu_host.store import Store
from native_menu.controller import Controller
import god_mode_live as capture
from native_menu.observe import objects
from native_menu.model import RULES
from god_mode_boss_probe import values

OUT = ROOT / "outputs/Fusion-NativeMenu-20261024"
capture.OUT = OUT


def pump(c, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        c.tick()
        time.sleep(0.04)


def key(c, value):
    before = c.mail.sequence
    c.window.key(value)
    end = time.monotonic() + 4
    while time.monotonic() < end:
        c.tick()
        if c.mail.sequence > before:
            return
        time.sleep(0.04)
    raise AssertionError("No native input: " + value)


def snapshot(c, name):
    """Wait for the native image-load event, then capture the displayed panel."""
    end = time.monotonic() + 5
    while time.monotonic() < end:
        c.tick()
        panel = next(
            o for o in objects(c.window.reader) if o["name"] == "Randomizer Panel"
        )
        if values(c.window.reader, panel, 2) == [c.mail.generation, 1]:
            pump(c, 0.12)
            capture.snap(c.window, name)
            return
        time.sleep(0.04)
    raise AssertionError(
        "Native panel did not load generation " + str(c.mail.generation)
    )


def main():
    report = {"scope": __doc__, "events": [], "memory_writes": 0}
    store = Store(OUT / "native-probe-profile")
    with store.lock():
        c = Controller(store)
        (OUT / "native-current-folder.txt").write_text(str(c.folder))
        try:
            c.open()
            c.enter()
            pump(c, 1)
            capture.snap(c.window, "native-home")
            report["folder"] = str(c.folder)
            report["window"] = c.window.window
            report["pid"] = c.window.pid
            panel = next(
                o for o in objects(c.window.reader) if o["name"] == "Randomizer Panel"
            )
            report["native_panel"] = dict(
                panel, values=values(c.window.reader, panel, 2)
            )
            assert panel["w"] == 640 and panel["h"] == 480, report["native_panel"]
            cast = [
                o
                for o in objects(c.window.reader)
                if o["name"].startswith("Randomizer Cast")
            ]
            assert len(cast) == 3 and all(
                (o["w"], o["h"]) == (192, 192) for o in cast
            ), cast
            report["native_cast"] = cast
            assert c.model.page == "home"
            report["events"].append("Native Active object renders the main menu")
            # Six native Down presses select Settings; Enter opens it.
            for i in range(6):
                key(c, "Down")
            key(c, "Return")
            assert c.model.page == "settings"
            for i in range(3):
                key(c, "Down")
            key(c, "Return")
            assert c.model.page == "gameplay"
            original = c.model.draft.seed
            key(c, "Return")
            assert (
                c.model.draft.options["extras"]["god_mode"]
                and c.model.draft.seed != original
            )
            for option in RULES[1:]:
                key(c, "Down")
                old = c.model.draft.seed
                previous = c.model.draft.options["extras"][option]
                key(c, "Return")
                assert (
                    c.model.draft.options["extras"][option] is not previous
                    and c.model.draft.seed != old
                )
            pump(c, 0.4)
            capture.snap(c.window, "native-gameplay")
            report["events"].append(
                "All gameplay toggles change options and seed through native keyboard events"
            )
            # Native click: first visible checkbox, not a host callback.
            subprocess.run(
                [
                    "xdotool",
                    "mousemove",
                    "--window",
                    c.window.window,
                    "300",
                    "250",
                    "click",
                    "1",
                ],
                check=True,
            )
            pump(c, 0.8)
            assert not c.model.draft.options["extras"]["god_mode"]
            report["events"].append(
                "Native mouse click changes the first gameplay toggle"
            )
            key(c, "Escape")
            key(c, "Down")
            key(c, "Return")
            assert c.model.page == "levels"
            assert len(c.model.rows()) == 21
            key(c, "Next")
            pump(c, 0.3)
            capture.snap(c.window, "native-levels-page2")
            key(c, "Escape")
            key(c, "Down")
            key(c, "Down")
            key(c, "Return")
            assert c.model.page == "bosses"
            assert len(c.model.rows()) == 22
            old = c.model.draft.seed
            key(c, "Return")
            assert c.model.draft.seed != old
            pump(c, 0.3)
            capture.snap(c.window, "native-bosses")
            report["events"].append(
                "Complete level and boss pools accessible with native paging"
            )
            # Language changes are preferences and retain the run seed.
            key(c, "Escape")
            for i in range(6):
                key(c, "Down")
            for expected in ("en", "es", "ru", "ja", "de"):
                old = c.model.draft.seed
                key(c, "Return")
                assert c.model.language == expected and c.model.draft.seed == old
                pump(c, 0.2)
                capture.snap(c.window, "native-language-" + expected)
            report["events"].append(
                "Five languages switch in the same native window without renewing the run seed"
            )
            report["passed"] = True
        except BaseException as e:
            report["error"] = repr(e)
            try:
                capture.snap(c.window, "native-failure")
            except Exception:
                pass
            raise
        finally:
            c.close()
            (OUT / "native-live-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
