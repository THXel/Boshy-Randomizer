"""Bounded real lifecycle endurance: three slots, native deaths/retries/F2.

Only initial run options are fixtures. The observer never writes game memory.
All sampled PIDs belong to the one controller's process; global processes are
counted only to detect duplicate game instances.
"""

import argparse
import json
import time
import uuid
from functools import partial
from pathlib import Path
import psutil
from menu_host.store import Store, digest
from menu_host.draft import Draft
from menu_host.processes import games
from export_native_run import export
from native_menu.combined import CombinedController
from native_menu.observe import objects
from native_menu.diagnostics import snapshot
from native_menu_probe import pump
from native_classic_live import wait
from native_menu_lifecycle_probe import pulse_inputs
from native_menu.builds import DYNAMIC_SHA


def run(output, cycles=18, dwell=10):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": 1,
        "game_sha256": DYNAMIC_SHA,
        "memory_writes": 0,
        "cycles": [],
        "requested_cycles": cycles,
        "passed": False,
        "scope": "bounded lifecycle endurance, not a complete game run",
    }
    started = time.monotonic()
    store = Store(
        output / ("soak-profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    with store.lock():
        for slot in (1, 2, 3):
            draft = Draft()
            draft.update(
                level_pool=["save1.ini"],
                level_count=1,
                boss_pool=[],
                route_boss_count=0,
                god_mode=True,
                no_mouse_ghost=True,
                sprite_scenery=True,
                sprite_backgrounds=True,
                sprite_decor=True,
                sprite_tiles=True,
                sprite_actors=True,
                music=True,
            )
            draft.seed = "ENDURANCE-" + str(slot)
            draft.blood_pack = draft.music_pack = (
                "original",
                "kamilia3",
                "wannafest22",
            )[slot - 1]
            store.create(slot, draft)
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            pid = c.window.pid
            for number in range(cycles):
                slot = number % 3 + 1
                c.model.slot = slot
                c.model.load_slot()
                c.begin()
                wait(c, lambda: c.phase == "playing")
                pump(c, dwell)
                assert len(games()) == 1 and c.window.pid == pid, (
                    "Duplicate or replaced game process"
                )
                assert any(o["name"] == "Player" for o in objects(c.window.reader))
                c.window.key("q")
                pump(c, 0.8)
                assert not any(o["name"] == "Player" for o in objects(c.window.reader))
                c.window.key("r")
                pump(c, 1)
                assert any(o["name"] == "Player" for o in objects(c.window.reader))
                diag = snapshot(c)
                assert diag["seed"] == "ENDURANCE-" + str(slot)
                streams = pulse_inputs(pid)
                assert len(streams) <= 1, ("Duplicate audio streams", streams)
                c.window.key("F2")
                wait(c, lambda: c.phase == "menu" and not store.active)
                c.enter()
                pump(c, 0.3)
                assert digest(c.folder / "Boshy.exe") == DYNAMIC_SHA
                sample = {
                    "cycle": number + 1,
                    "slot": slot,
                    "seconds": round(time.monotonic() - started, 1),
                    "game_rss_mb": round(
                        psutil.Process(pid).memory_info().rss / 1048576, 1
                    ),
                    "host_rss_mb": round(
                        psutil.Process().memory_info().rss / 1048576, 1
                    ),
                    "game_processes": len(games()),
                    "audio_streams": len(streams),
                    "seed": diag["seed"],
                }
                report["cycles"].append(sample)
                print(json.dumps(sample), flush=True)
            # Ignore cache warm-up across the first complete pass through slots.
            warm = report["cycles"][2:]
            if warm:
                report["game_rss_growth_mb"] = round(
                    warm[-1]["game_rss_mb"] - warm[0]["game_rss_mb"], 1
                )
                report["host_rss_growth_mb"] = round(
                    warm[-1]["host_rss_mb"] - warm[0]["host_rss_mb"], 1
                )
                assert report["game_rss_growth_mb"] < 128, (
                    "Game memory keeps growing beyond the bounded allowance"
                )
                assert report["host_rss_growth_mb"] < 128, (
                    "Host memory keeps growing beyond the bounded allowance"
                )
            report["passed"] = True
        finally:
            c.close()
            report["remaining_game_processes"] = len(games())
            report["elapsed_seconds"] = round(time.monotonic() - started, 1)
            (output / "soak.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("output", type=Path)
    p.add_argument("--cycles", type=int, default=18)
    p.add_argument("--dwell", type=float, default=10)
    args = p.parse_args()
    run(args.output, args.cycles, args.dwell)
