"""Original intro/menu/1-2-3 selector through real keyboard and mouse input."""

import json, time, uuid, subprocess
from native_menu.classic import ClassicController
from native_menu_probe import pump, key, snapshot
from native_menu.observe import objects
from god_mode_boss_probe import values
from menu_host.store import Store
from native_menu.unified import read_session
from export_route_probe import ROOT
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-ClassicMenu-20261025"


def trigger(c):
    obj = next(o for o in objects(c.window.reader) if o["name"] == "MenuTrigger")
    return values(c.window.reader, obj, 2)


def wait(c, predicate, seconds=20, poll=True):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if poll:
            c.tick()
        try:
            if predicate():
                return
        except (RuntimeError, StopIteration):
            pass
        time.sleep(0.1)
    raise AssertionError("Classic menu wait timed out")


def enter_title(c):
    deadline = time.monotonic() + 25
    while time.monotonic() < deadline:
        try:
            frame = c.window.reader.frame()
        except RuntimeError:
            time.sleep(0.1)
            continue
        if frame == "Title Screen":
            return
        if frame == "JAE Intro":
            c.window.key("Return")
        time.sleep(0.2)
    raise AssertionError("Title Screen not reached")


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, memory_writes=0)
    store = Store(OUT / ("profile-" + uuid.uuid4().hex[:6]))
    with store.lock():
        c = ClassicController(store)
        report["folder"] = str(c.folder)
        try:
            c.open()
            enter_title(c)
            wait(c, lambda: c.window.reader.frame() == "Title Screen", poll=False)
            pump(c, 2)
            capture.snap(c.window, "classic-intro-first")
            pump(c, 6)
            capture.snap(c.window, "classic-intro-first-8s")
            pump(c, 6)
            capture.snap(c.window, "classic-intro-first-14s")
            initial = read_session(c.folder).getint("Session", "Intro")
            if trigger(c)[1] != -1:
                c.window.key("Return")
                wait(c, lambda: trigger(c)[1] == -1, poll=False)
            time.sleep(0.3)
            capture.snap(c.window, "classic-game-options")
            assert not any(
                o["name"] == "MenuButton 10" for o in objects(c.window.reader)
            )
            for _ in range(3):
                c.window.key("Down")
                time.sleep(0.15)
                assert trigger(c)[0] in (0, 1)
            c.window.key("Up")
            time.sleep(0.2)
            assert trigger(c)[0] == 0
            c.window.key("Return")
            pump(c, 0.5)
            assert c.model.page == "home", c.model.page
            report["slots"] = []
            for slot in (1, 2, 3):
                if slot > 1:
                    key(c, "Right")
                wait(c, lambda: c.model.slot == slot)
                assert trigger(c) == [slot - 1, 0], trigger(c)
                snapshot(c, "classic-slot-" + str(slot))
                report["slots"].append(dict(slot=slot, native=trigger(c)))
            subprocess.run(
                [
                    "xdotool",
                    "mousemove",
                    "--window",
                    c.window.window,
                    "246",
                    "351",
                    "click",
                    "1",
                ],
                check=True,
            )
            wait(c, lambda: c.model.slot == 1)
            assert trigger(c) == [0, 0]
            key(c, "Return")
            assert c.model.page == "settings"
            snapshot(c, "classic-options-de")
            seed = c.model.draft.seed
            # Existing native menu pages and translations remain available.
            report["languages"] = []
            for lang in ("de", "en", "es", "ru", "ja"):
                c.model.language = lang
                c.mail.publish()
                pump(c, 0.2)
                snapshot(c, "classic-options-" + lang)
                report["languages"].append(lang)
            assert c.model.draft.seed == seed
            c.model.language = "de"
            c.model.go("home")
            c.mail.publish()
            pump(c, 0.2)
            c.window.key("F2")
            wait(
                c,
                lambda: c.window.reader.frame() in ("JAE Intro", "Title Screen"),
                poll=False,
            )
            enter_title(c)
            wait(
                c,
                lambda: read_session(c.folder).getint("Session", "Intro") != initial,
                poll=False,
            )
            pump(c, 14)
            second = read_session(c.folder).getint("Session", "Intro")
            capture.snap(c.window, "classic-intro-second")
            art = json.loads((c.folder / "classic-intro/manifest.json").read_text())
            assert all(
                a != b for a, b in zip(art["casts"][initial], art["casts"][second])
            )
            assert c.model.draft.seed == seed
            report.update(
                first_cast=art["names"][initial],
                second_cast=art["names"][second],
                first_intro=initial,
                second_intro=second,
                seed_unchanged=True,
                online_removed=True,
                mouse_slot_selection=True,
                passed=True,
            )
        except BaseException as error:
            report["error"] = repr(error)
            raise
        finally:
            c.close()
            (OUT / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
