"""Capture boss audio from before entry; compare Auto versus explicit Boshy.

Read-only runtime observation, no state writes. The two isolated runs share the
same music seed and native executable so character initialization is the variable.
"""

import argparse
import json
import subprocess
import time
import uuid
from functools import partial
import numpy as np
from export_route_probe import ROOT
from export_native_run import export
from menu_host.store import Store, save
from native_rewards_live import write_save
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu_probe import pump
from native_menu_lifecycle_probe import wait_for
from music import runtime
from music.continuity import decoded, match
from blood_enemy_probe import streams
from god_mode_boss_probe import values
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-MusicFollowup-20261025"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frequency-probe", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    capture.OUT = OUT
    store = Store(
        OUT / ("timeline-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    report = {
        "scope": __doc__,
        "cases": [],
        "memory_writes": 0,
        "frequency_probe": args.frequency_probe,
    }
    with store.lock():
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            for slot, character in ((1, "Auto"), (2, "Boshy")):
                label = ("frequency-" if args.frequency_probe else "") + character
                d = Draft()
                d.set_mode("boss_rush")
                d.update(
                    boss_pool=["hellokitty"],
                    route_boss_count=1,
                    god_mode=True,
                    no_mouse_ghost=True,
                    skip_intro=True,
                    music=True,
                    start_character=character,
                )
                d.seed = "00009004"
                store.create(slot, d)
                if args.frequency_probe:
                    cfg = save(store.folder(slot) / "SaveFile1.ini")
                    cfg["MixerSecret"] = {"Freq": "1" if slot == 1 else "0"}
                    write_save(store.folder(slot) / "SaveFile1.ini", cfg)
                c.model.slot = slot
                c.model.load_slot()
                plan = json.loads((store.folder(slot) / "plan.json").read_text())
                asset = next(
                    r
                    for r in plan["runtime_music_assets"]
                    if r["cue"] == "First Boss Music"
                )
                reference = decoded(
                    (
                        store.folder(slot) / runtime.DIRECTORY / asset["file"]
                    ).read_bytes()
                )
                audio = streams()
                assert len(audio) == 1, audio
                path = OUT / (label + "-timeline.s16le")
                case = {"character": character, "asset": asset, "states": []}
                report["cases"].append(case)
                with path.open("wb") as output:
                    proc = subprocess.Popen(
                        [
                            "parec",
                            "--monitor-stream=" + str(audio[0]["index"]),
                            "--rate=22050",
                            "--channels=2",
                            "--format=s16le",
                        ],
                        stdout=output,
                        stderr=subprocess.DEVNULL,
                    )
                    try:
                        pump(c, 2)
                        case["start_sample"] = path.stat().st_size // 4
                        c.begin()
                        wait_for(c, lambda: c.phase == "playing")
                        start = time.monotonic()
                        for tick in range(6):
                            pump(c, 2)
                            obs = capture.objects(c.window.reader)
                            case["states"].append(
                                {
                                    "t": time.monotonic() - start,
                                    "actors": [
                                        dict(o, values=values(c.window.reader, o, 3))
                                        for o in obs
                                        if o["name"] in ("Player", "hellokitty")
                                    ],
                                    "fire": sum(
                                        o["name"] == "OPE_fireParticle" for o in obs
                                    ),
                                    "characters": [
                                        o["name"]
                                        for o in obs
                                        if o["name"].startswith("ON")
                                    ],
                                }
                            )
                        capture.snap(c.window, label + "-timeline")
                    finally:
                        proc.terminate()
                        proc.wait(timeout=3)
                signal = (
                    np.frombuffer(path.read_bytes(), dtype="<i2")
                    .reshape(-1, 2)
                    .mean(axis=1)[::5]
                    / 32768
                )
                case["audio"] = []
                for sec in np.arange(0, len(signal) / 4410 - 0.5, 0.5):
                    window = signal[int(sec * 4410) : int((sec + 0.5) * 4410)]
                    case["audio"].append(
                        {
                            "second": float(sec),
                            "rms": float(np.sqrt(np.mean(window**2))),
                            **match(reference, window),
                        }
                    )
                print(
                    label,
                    [
                        (r["second"], round(r["rms"], 3), round(r["correlation"], 3))
                        for r in case["audio"]
                    ],
                    flush=True,
                )
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu")
                c.enter()
        finally:
            c.close()
            (
                OUT
                / (
                    "frequency-results.json"
                    if args.frequency_probe
                    else "timeline-results.json"
                )
            ).write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
