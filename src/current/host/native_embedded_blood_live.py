"""Real Q deaths across three blood packs in one persistent native process."""

import json
import time
import uuid
from functools import partial
from export_route_probe import ROOT
from export_native_run import export
from menu_host.store import Store, digest
from menu_host.draft import Draft
from menu_host.processes import games
from native_menu.combined import CombinedController
from native_menu.builds import DYNAMIC_SHA
from native_menu_probe import pump
from native_menu_lifecycle_probe import wait_for
from god_mode_boss_probe import values
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-Modernization-20261025"


def particles(c):
    result = []
    for o in capture.objects(c.window.reader):
        if o["name"] in ("Active 2", "blood"):
            try:
                v = values(c.window.reader, o, 7)
            except RuntimeError:
                continue  # Native particle expired between the two read-only samples.
            if len(v) == 7:
                result.append(dict(width=o["w"], height=o["h"], life=v[6]))
    return result


def main():
    capture.OUT = OUT
    s = Store(
        OUT / ("blood-profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    report = dict(scope=__doc__, memory_writes=0, cases=[])
    with s.lock():
        for slot, pack in enumerate(("original", "kamilia3", "wannafest22"), 1):
            d = Draft()
            d.set_mode("normal")
            d.update(god_mode=True, no_mouse_ghost=True)
            d.select_pack("blood_pack", pack)
            s.create(slot, d)
            assert digest(s.folder(slot) / "Boshy.exe") == DYNAMIC_SHA
        c = CombinedController(s, dynamic=True)
        try:
            c.open()
            c.enter()
            pump(c, 0.3)
            identity = (c.window.pid, c.window.window)
            for slot, pack in [
                (1, "original"),
                (2, "kamilia3"),
                (3, "wannafest22"),
                (1, "original"),
            ]:
                c.model.slot = slot
                c.model.load_slot()
                c.begin()
                wait_for(c, lambda: c.phase == "playing")
                pump(c, 0.25)
                assert identity == (c.window.pid, c.window.window) and len(games()) == 1
                c.window.key("q")
                observed = []
                for i in range(4):
                    observed += particles(c)
                    if i == 0:
                        capture.snap(c.window, "blood-" + pack + "-death")
                    pump(c, 0.08)
                owned = [p for p in observed if p["life"] > 0]
                if pack == "original":
                    assert observed and not owned, observed
                else:
                    expected = (32, 31) if pack == "kamilia3" else (20, 20)
                    assert owned and any(
                        (p["width"], p["height"]) == expected for p in owned
                    ), (pack, observed)
                pump(c, 2.5)
                assert not any(p["life"] > 0 for p in particles(c))
                c.window.key("r")
                pump(c, 0.5)
                assert any(
                    o["name"] == "Player" for o in capture.objects(c.window.reader)
                )
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu")
                c.enter()
                pump(c, 0.2)
                report["cases"].append(
                    dict(
                        slot=slot,
                        pack=pack,
                        observed=observed,
                        same_process=True,
                        expired=True,
                        respawn=True,
                    )
                )
                print("PASS", slot, pack, flush=True)
            report.update(passed=True, identity=identity, exe_sha256=DYNAMIC_SHA)
        except BaseException as e:
            report["error"] = repr(e)
            raise
        finally:
            try:
                c.close()
            finally:
                (OUT / "blood-live-results.json").write_text(
                    json.dumps(report, indent=2) + "\n"
                )
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
