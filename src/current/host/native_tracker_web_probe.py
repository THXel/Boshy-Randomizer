"""Native CD pickup -> standalone HTTP; position-only closed-save fixture."""

import io
import json
import time
import uuid
from functools import partial
from urllib.request import urlopen
from export_route_probe import ROOT
from export_native_run import export
from menu_host.store import Store, save, RC4, atomic
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu_probe import pump
from native_menu_lifecycle_probe import wait_for
from tracker.server import URL, start, stop

OUT = ROOT / "outputs/Fusion-StandaloneTracker-20261025"


def status():
    with urlopen(URL + "state", timeout=3) as response:
        return json.load(response)


def mark(name, c):
    c.tracker.tick(c, force=True)
    data = status()
    (OUT / (name + ".json")).write_text(json.dumps(data, indent=2))
    print(name, flush=True)
    return data


def main():
    server = start()
    report = dict(
        fixture="Closed-save original CD chest position only", memory_writes=0
    )
    store = Store(
        OUT / ("live-profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    with store.lock():
        d = Draft()
        d.set_mode("target")
        d.update(
            target_count=19,
            boss_count=22,
            god_mode=True,
            fast_chests=True,
            no_mouse_ghost=True,
        )
        d.seed = "WEBTRACKER"
        store.create(1, d)
        p = store.folder(1) / "SaveFile1.ini"
        cfg = save(p)
        cfg["Positions"]["xpos"] = "3590"
        cfg["Positions"]["ypos"] = "804"
        buf = io.StringIO()
        cfg.write(buf)
        atomic(p, RC4(b"BLOB", buf.getvalue().encode("latin1")))
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            pump(c, 1)
            mark("live-menu", c)
            # Give the already open browser a menu baseline before entering.
            pump(c, 3)
            c.model.slot = 1
            c.model.load_slot()
            c.begin()
            wait_for(c, lambda: c.phase == "playing", seconds=35)
            wait_for(
                c,
                lambda: save(c.folder / "SaveFile1.ini").getint(
                    "Collectables", "Lalalalalala CD", fallback=0
                )
                == 1,
                seconds=15,
            )
            pump(c, 0.6)
            got = mark("live-pickup", c)
            assert got["connected"] and sum(r["done"] for r in got["goals"]) == 1
            assert (
                len(got["events"]) == 1
                and got["events"][0]["name"] == "Lalalalalala CD"
            )
            report["pickup"] = got
            # User-visible browser checks happen during this bounded live hold.
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline and not (OUT / "continue-live").exists():
                pump(c, 0.2)
            c.window.key("q")
            pump(c, 1)
            c.window.key("r")
            pump(c, 1)
            assert len(mark("live-respawn", c)["events"]) == 1
            c.window.key("F2")
            wait_for(c, lambda: c.phase == "menu", seconds=30)
            c.enter()
            pump(c, 1)
            c.model.slot = 1
            c.model.load_slot()
            c.begin()
            wait_for(c, lambda: c.phase == "playing", seconds=35)
            pump(c, 1)
            resumed = mark("live-resumed", c)
            assert len(resumed["events"]) == 1 and resumed["run_id"] == got["run_id"]
            assert sum(r["done"] for r in resumed["goals"]) == 1
            report["resumed"] = resumed
            report["passed"] = True
        finally:
            c.close()
            report["closed"] = status()
            assert not report["closed"]["connected"]
            (OUT / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")
    stop(server)
    print("PASS", flush=True)


if __name__ == "__main__":
    main()
