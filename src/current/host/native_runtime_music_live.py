"""Real same-process music switches with game-only recorded waveform evidence."""

import argparse
import json
import subprocess
import time
import uuid
from functools import partial
import numpy as np
from export_route_probe import ROOT
from export_native_run import export
from menu_host.store import Store
from menu_host.draft import Draft
from menu_host.processes import games
from native_menu.combined import CombinedController
from native_menu.builds import DYNAMIC_SHA
from native_menu_probe import pump
from native_menu_lifecycle_probe import wait_for
from music import runtime
from music.continuity import decoded, match, match_after
from blood_enemy_probe import streams
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-RuntimeMusic-20261025"


def audio_check(c, name, expected, during=None):
    inputs = streams()
    assert len(inputs) == 1, inputs
    path = OUT / (name + ".s16le")
    with path.open("wb") as output, (OUT / (name + "-capture.log")).open("w") as errors:
        proc = subprocess.Popen(
            [
                "parec",
                "--monitor-stream=" + str(inputs[0]["index"]),
                "--rate=22050",
                "--channels=2",
                "--format=s16le",
            ],
            stdout=output,
            stderr=errors,
        )
        try:
            deadline = time.monotonic() + 15
            triggered = False
            # PipeWire/parec startup and buffering can consume wall time without
            # delivering audio yet. Require enough actual recorded samples.
            while path.stat().st_size < 5 * 22050 * 4:
                if time.monotonic() >= deadline:
                    raise AssertionError("Insufficient captured game audio")
                pump(c, 0.1)
                if during and not triggered and path.stat().st_size >= 1.8 * 22050 * 4:
                    during()
                    triggered = True
            assert not during or triggered
        finally:
            proc.terminate()
            proc.wait(timeout=3)
    signal = (
        np.frombuffer(path.read_bytes(), dtype="<i2").reshape(-1, 2).mean(axis=1)[::5]
        / 32768
    )
    reference = decoded(expected)
    width = int(0.5 * 4410)
    positions = [int(1 * 4410), int((4.2 if during else 3.5) * 4410)]
    identified = [match(reference, signal[p : p + width]) for p in positions]
    global_after = identified[1]
    identified[1] = match_after(
        reference,
        signal[positions[1] : positions[1] + width],
        identified[0],
        (positions[1] - positions[0]) / 4410,
    )
    negative = decoded(
        next(data for data in runtime.original_audio().values() if data != expected)
    )
    controls = [match(negative, signal[p : p + width]) for p in positions]
    advance = identified[1]["reference_seconds"] - identified[0]["reference_seconds"]
    if advance < 0:
        advance += len(reference) / 4410
    result = dict(
        matches=identified,
        unrestricted_after=global_after,
        unrelated_track=controls,
        advance=advance,
        elapsed=(positions[1] - positions[0]) / 4410,
        capture=path.name,
    )
    result["passed"] = (
        min(r["correlation"] for r in identified) > 0.3
        and all(
            a["correlation"] - b["correlation"] > 0.15
            for a, b in zip(identified, controls)
        )
        and abs(advance - result["elapsed"]) < 0.08
    )
    assert result["passed"], result
    return result


def main(boss_only=False, packs=None):
    OUT.mkdir(exist_ok=True)
    capture.OUT = OUT
    store = Store(
        OUT / ("profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    report = dict(scope=__doc__, memory_writes=0, cases=[], game_sha256=DYNAMIC_SHA)
    with store.lock():
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            pump(c, 0.3)
            identity = (c.window.pid, c.window.window)
            cases = [
                ("level", "original", 1, True),
                ("level", "kamilia3", 2, True),
                ("level", "wannafest22", 3, True),
                ("level", "original", 3, False),
                ("boss", "original", 1, True),
                ("boss", "kamilia3", 2, True),
                ("boss", "wannafest22", 3, True),
            ]
            for case_index, (kind, pack, slot, enabled) in enumerate(cases):
                if (boss_only and kind != "boss") or (packs and pack not in packs):
                    continue
                if store.current(slot):
                    store.archive(slot)
                draft = Draft()
                draft.set_mode("normal" if kind == "level" else "boss_rush")
                draft.update(
                    god_mode=True, no_mouse_ghost=True, skip_intro=True, music=enabled
                )
                if kind == "boss":
                    draft.update(boss_pool=["hellokitty"], route_boss_count=1)
                draft.select_pack("music_pack", pack)
                draft.seed = f"{0x9000 + case_index:08X}"
                store.create(slot, draft)
                c.model.slot = slot
                c.model.load_slot()
                assert c.compatible_draft()
                c.begin()
                wait_for(c, lambda: c.phase == "playing")
                pump(c, 3)
                assert identity == (c.window.pid, c.window.window) and len(games()) == 1
                cue = "Prehistorik2Boss (2)" if kind == "level" else "First Boss Music"
                plan = json.loads((store.folder(slot) / "plan.json").read_text())
                if enabled:
                    row = next(
                        row for row in plan["runtime_music_assets"] if row["cue"] == cue
                    )
                    expected = (c.folder / runtime.DIRECTORY / row["file"]).read_bytes()
                    target = row["target"]
                else:
                    expected = runtime.original_audio()[cue]
                    target = cue
                name = f'{len(report["cases"])+1:02d}-{kind}-{pack}-{enabled}'
                case = dict(
                    kind=kind,
                    pack=pack,
                    slot=slot,
                    enabled=enabled,
                    cue=cue,
                    target=target,
                    frame=c.window.reader.frame(),
                    pid=c.window.pid,
                )
                case["audio"] = audio_check(c, name, expected)
                capture.snap(c.window, name)
                if (kind == "level" and pack == "kamilia3") or (
                    kind == "boss" and pack == "original"
                ):
                    c.window.key("q")
                    pump(c, 0.4)
                    c.window.key("r")
                    pump(c, 1)
                    case["after_respawn"] = audio_check(c, name + "-respawn", expected)
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu")
                c.enter()
                pump(c, 0.2)
                report["cases"].append(case)
                print("PASS", kind, pack, enabled, flush=True)
            report.update(passed=True, identity=identity)
        except BaseException as error:
            report["error"] = repr(error)
            raise
        finally:
            c.close()
            (
                OUT / ("boss-live-results.json" if boss_only else "live-results.json")
            ).write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--boss-only", action="store_true")
    parser.add_argument(
        "--packs", nargs="+", choices=("original", "kamilia3", "wannafest22")
    )
    args = parser.parse_args()
    main(args.boss_only, args.packs)
