"""Real Target pickup; only closed-save entry coordinates are staged."""

import io
import json
import subprocess
import time
import uuid
from functools import partial
from pathlib import Path
from export_route_probe import ROOT
from export_native_run import export
from menu_host.store import Store, save, RC4, atomic
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu_probe import pump
from native_menu_lifecycle_probe import wait_for
from native_tracker_probe import status, current
from native_menu import builds

OUT = ROOT / "outputs/Fusion-Tracker-20261025"
PINGU = Path("/home/thxel/StreamStuff/PinguLexa")


def obs_capture(label):
    code = """import asyncio,base64,sys
from pathlib import Path
from pingulexa_runtime.pingulexa_obs_websocket import ObsWebSocketClient
async def main():
 r=await ObsWebSocketClient().request('GetSourceScreenshot',{'sourceName':'Boshy Overlay','imageFormat':'png','imageWidth':640,'imageHeight':485})
 Path(sys.argv[1]).write_bytes(base64.b64decode(r['imageData'].split(',',1)[1]))
asyncio.run(main())
"""
    subprocess.run(
        [str(PINGU / ".venv/bin/python"), "-c", code, str(OUT / (label + ".png"))],
        cwd=PINGU,
        check=True,
    )


def main():
    store = Store(
        OUT / ("pickup-profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    report = dict(
        build_sha256=builds.DYNAMIC_SHA,
        memory_writes=0,
        fixture="Closed-save position near original CD chest; no inventory, achievement or live memory writes.",
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
        d.seed = "TRACKERPICKUP"
        store.create(1, d)
        p = store.folder(1) / "SaveFile1.ini"
        cfg = save(p)
        cfg["Positions"]["xpos"] = "3590"
        cfg["Positions"]["ypos"] = "804"
        buf = io.StringIO()
        cfg.write(buf)
        atomic(p, RC4(b"BLOB", buf.getvalue().encode("latin1")))
        report["profile"] = str(store.root)
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            pump(c, 1)
            c.model.slot = 1
            c.model.load_slot()
            c.begin()
            report["loading"] = status()
            assert report["loading"]["native_tracker"]["phase"] == "loading"
            assert report["loading"]["goals_done"] == 0
            wait_for(c, lambda: c.phase == "playing", seconds=35)
            pump(c, 0.4)
            report["entry"] = current(c)
            from native_menu.observe import objects

            report["player_entry"] = [
                o for o in objects(c.window.reader) if o["name"] == "Player"
            ]
            if report["entry"]["goals_done"] == 0:
                for _ in range(8):
                    subprocess.run(["xdotool", "keydown", "Right"], check=True)
                    try:
                        pump(c, 0.1)
                    finally:
                        subprocess.run(["xdotool", "keyup", "Right"], check=True)
                    if current(c)["goals_done"]:
                        break
            wait_for(
                c,
                lambda: save(c.folder / "SaveFile1.ini").getint(
                    "Collectables", "Lalalalalala CD", fallback=0
                )
                == 1,
                seconds=15,
            )
            pump(c, 1.6)
            report["pickup"] = current(c)
            assert (
                report["pickup"]["goals_done"] == 1
                and report["pickup"]["goals_total"] == 41
            )
            assert (
                sum(r["done"] for r in report["pickup"]["native_tracker"]["items"]) == 1
            )
            assert not any(
                r["done"] for r in report["pickup"]["native_tracker"]["bosses"]
            )
            obs_capture("obs-target-pickup")
            c.window.key("q")
            pump(c, 1)
            c.window.key("r")
            pump(c, 1)
            assert current(c)["goals_done"] == 1
            c.window.key("F2")
            wait_for(c, lambda: c.phase == "menu", seconds=30)
            c.enter()
            pump(c, 1)
            c.model.slot = 1
            c.model.load_slot()
            c.begin()
            wait_for(c, lambda: c.phase == "playing", seconds=35)
            pump(c, 2)
            report["resumed"] = current(c)
            assert report["resumed"]["goals_done"] == 1
            assert (
                report["resumed"]["native_tracker"]["run_id"]
                == report["pickup"]["native_tracker"]["run_id"]
            )
            obs_capture("obs-target-resumed")
            report["passed"] = True
        except BaseException as exc:
            report["error"] = repr(exc)
            raise
        finally:
            subprocess.run(["xdotool", "keyup", "Right"], check=False)
            c.close()
            time.sleep(2)
            report["closed"] = status()
            assert not report["closed"].get("native_tracker")
            (OUT / "pickup-live-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print("PASS target pickup, Q/R, resume, actual OBS source", flush=True)


if __name__ == "__main__":
    main()
