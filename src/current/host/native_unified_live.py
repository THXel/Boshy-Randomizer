"""Same-process menu/run tests using native keys and read-only observation."""

import json
import time
import uuid
from functools import partial
from menu_host.store import Store, save, digest
from menu_host.draft import Draft
from export_native_run import export, ORIGINAL
from export_route_probe import ROOT
from native_menu.unified import PreparedController
from native_menu.observe import objects
from native_menu_probe import pump, snapshot, key
from gameplay.target_plan import GROUP as TARGET
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-UnifiedApp-20261025"


def until(c, predicate, timeout=20):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        c.tick()
        try:
            if predicate():
                return
        except RuntimeError:
            pass
        time.sleep(0.08)
    raise AssertionError((c.phase, "Unified transition timeout"))


def main():
    capture.OUT = OUT
    report = dict(
        scope=__doc__, cases=[], memory_writes=0, original_sha256=digest(ORIGINAL)
    )
    try:
        for mode in ("normal", "target", "randomizer"):
            store = Store(
                OUT / ("profile-" + mode + "-" + uuid.uuid4().hex[:6]),
                exporter=partial(export, unified=True),
            )
            with store.lock():
                d = Draft()
                d.set_mode(mode)
                d.update(
                    god_mode=True,
                    no_mouse_ghost=True,
                    characters=True,
                    level_pool=["save1.ini"],
                    level_count=1,
                    boss_pool=["hellokitty"],
                    route_boss_count=1,
                    sprite_scenery=False,
                    music=False,
                )
                d.seed = "0000001D"
                store.create(1, d)
                c = PreparedController(store)
                case = dict(mode=mode, folder=str(c.folder), cycles=[])
                report["cases"].append(case)
                print("START", mode, flush=True)
                try:
                    c.open()
                    c.enter()
                    pump(c, 0.3)
                    identity = (c.window.pid, c.window.window)
                    case.update(pid=identity[0], window=identity[1])
                    snapshot(c, mode + "-menu")
                    for iteration in range(2):
                        key(c, "Return")
                        until(c, lambda: c.phase == "playing")
                        assert identity == (c.window.pid, c.window.window)
                        assert c.window.owned()
                        frame = c.window.reader.frame()
                        assert frame == "First World - Prehistorik", frame
                        assert any(
                            o["name"] == "Player" for o in objects(c.window.reader)
                        )
                        capture.snap(c.window, mode + "-playing-" + str(iteration))
                        deaths = save(c.folder / "SaveFile1.ini").getint(
                            "Stats", "Deaths"
                        )
                        before_profile = save(c.folder / "onlineLicense.ini").get(
                            "License", "CharacterName"
                        )
                        c.window.key("q")
                        time.sleep(0.7)
                        assert not any(
                            o["name"] == "Player" for o in objects(c.window.reader)
                        )
                        c.window.key("r")
                        time.sleep(0.6)
                        assert any(
                            o["name"] == "Player" for o in objects(c.window.reader)
                        )
                        after = save(c.folder / "SaveFile1.ini")
                        assert after.getint("Stats", "Deaths") > deaths
                        assert (
                            save(c.folder / "onlineLicense.ini").get(
                                "License", "CharacterName"
                            )
                            == before_profile
                        )
                        if mode == "target":
                            assert after.getint(TARGET, "Visit") == 0
                        c.window.key("F2")
                        until(c, lambda: c.phase == "menu")
                        pump(c, 0.8)
                        assert c.phase == "menu" and c.window.owned()
                        assert identity == (c.window.pid, c.window.window)
                        assert c.window.reader.frame() == "Title Screen"
                        state = save(c.folder / "native-session.ini")
                        assert state.getint("Session", "Accepted") == iteration + 1
                        assert state.getint("Session", "Status") == 0
                        snapshot(c, mode + "-returned-" + str(iteration))
                        store.resume(1)
                        case["cycles"].append(
                            dict(
                                iteration=iteration,
                                frame=frame,
                                deaths=after.getint("Stats", "Deaths"),
                                native_session=dict(state["Session"]),
                                same_process=True,
                                same_window=True,
                                passed=True,
                            )
                        )
                    case["passed"] = True
                finally:
                    c.close()
        assert digest(ORIGINAL) == report["original_sha256"]
        report["passed"] = True
    except BaseException as error:
        report["error"] = repr(error)
        raise
    finally:
        (OUT / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
