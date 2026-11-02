"""Private game-only audio and focus checks for the native spider."""

import argparse
import io
import json
import math
import struct
import subprocess
import time
import uuid
from functools import partial

from export_route_probe import ROOT
from export_native_run import export
from menu_host.store import Store, save, RC4, atomic
from menu_host.draft import Draft
from native_menu import builds
from native_menu.combined import CombinedController
from native_menu_probe import pump
from native_menu_lifecycle_probe import wait_for
from native_menu.observe import objects
from god_mode_boss_probe import values
from gameplay import spider_plan as plan, spider_events as event
from gameplay.spider_object import NAME
from blood_enemy_probe import streams

OUT = ROOT / "outputs/Fusion-Spider-20261025"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep-focus", action="store_true")
    args = parser.parse_args()
    label = "audio-focused" if args.keep_focus else "focus-audio"
    store = Store(
        OUT / ("focus-profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    report = dict(
        build_sha256=builds.DYNAMIC_SHA,
        memory_writes=0,
        fixture="Remaining=1 before launch; native grace unchanged",
        samples=[],
    )
    recorder = audio_file = None
    with store.lock():
        d = Draft()
        d.set_mode("normal")
        d.update(
            spider=True,
            god_mode=True,
            no_mouse_ghost=True,
            start_character="Auto",
            characters=False,
            sprite_scenery=True,
            sprite_actors=True,
        )
        d.seed = "SPDR0000"
        store.create(1, d)
        p = store.folder(1) / "onlineLicense.ini"
        cfg = save(p)
        cfg[plan.STATE]["Remaining"] = "1"
        buf = io.StringIO()
        cfg.write(buf)
        atomic(p, RC4(b"BLOB", buf.getvalue().encode("latin1")))
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            c.model.slot = 1
            c.model.load_slot()
            c.begin()
            wait_for(c, lambda: c.phase == "playing", seconds=35)
            obs = objects(c.window.reader)
            spider = next(o for o in obs if o["name"] == NAME)
            player = next(o for o in obs if o["name"] == "Player")

            def state():
                return dict(save(c.folder / "onlineLicense.ini")[plan.STATE])

            def other_focus():
                rows = subprocess.check_output(["wmctrl", "-l"], text=True).splitlines()
                target = next(
                    row.split()[0] for row in rows if row.endswith(" ChatGPT")
                )
                subprocess.run(["wmctrl", "-ia", target], check=True)

            pump(c, 1)
            other_focus()
            pump(c, 0.3)
            before = values(c.window.reader, spider, 12)
            saved = state()
            pump(c, 2)
            after = values(c.window.reader, spider, 12)
            report["unfocused_countdown"] = dict(
                before=before, after=after, saved_before=saved, saved_after=state()
            )
            assert (
                before[event.GRACE : event.CLOCK + 1]
                == after[event.GRACE : event.CLOCK + 1]
            )
            assert saved == state()
            subprocess.run(["wmctrl", "-ia", c.window.window], check=True)
            audio = streams()
            assert len(audio) == 1
            report["audio_stream"] = audio[0]
            audio_path = OUT / (label + ".s16le")
            audio_file = audio_path.open("wb")
            recorder = subprocess.Popen(
                [
                    "parec",
                    "--monitor-stream=" + str(audio[0]["index"]),
                    "--rate=22050",
                    "--channels=2",
                    "--format=s16le",
                ],
                stdout=audio_file,
                stderr=subprocess.DEVNULL,
            )
            started = time.monotonic()
            cancelled = False
            while time.monotonic() - started < 25:
                pump(c, 0.06)
                v = values(c.window.reader, spider, 12)
                if v[event.ACTIVE]:
                    px, py = (
                        struct.unpack(
                            "<i", c.window.reader.read(player["ptr"] + offset, 4)
                        )[0]
                        for offset in (76, 84)
                    )
                    raw = c.window.reader.read(spider["ptr"] + 232, 4)
                    actual = struct.unpack("<f", raw)[0]
                    expected = (
                        math.degrees(math.atan2(v[event.Y] - py, px - v[event.X])) + 90
                    ) % 360
                    report["samples"].append(
                        dict(
                            values=v,
                            player=[px, py],
                            angle_float=actual,
                            angle_int=struct.unpack("<i", raw)[0],
                            expected_angle=expected,
                        )
                    )
                    if len(report["samples"]) >= 3:
                        if not args.keep_focus:
                            other_focus()
                            pump(c, 0.4)
                            report["unfocused_attack"] = values(
                                c.window.reader, spider, 12
                            )
                            assert report["unfocused_attack"][event.ACTIVE] == 0
                            assert report["unfocused_attack"][event.GRACE] == plan.GRACE
                        cancelled = True
                        break
            assert cancelled, "No attack observed"
            # Keep recording past the 3.54-second original sample plus the
            # PulseAudio monitor buffer; terminating earlier truncates its tail.
            pump(c, 6)
            recorder.terminate()
            recorder.wait(timeout=3)
            recorder = None
            audio_file.close()
            audio_file = None
            subprocess.run(["wmctrl", "-ia", c.window.window], check=True)
            pump(c, 1)
            assert values(c.window.reader, spider, 12)[event.ACTIVE] == 0
            assert int(state()["attacks"]) == 1 and int(state()["hits"]) == 0
            report["state_after_refocus"] = state()
            from music.continuity import decoded, match
            from music.bank import read
            from visuals.scenery_pack import App
            import numpy as np

            app = App(builds.DYNAMIC_BASE)
            bank, _ = read(app.payload(0x6668), app.payload(0x5557))
            ref = decoded(
                next(
                    s.audio
                    for s in bank.values()
                    if s.name == "aaaaaaaaaaaah_newandlouder"
                )
            )
            signal = (
                np.frombuffer(audio_path.read_bytes(), dtype="<i2")
                .reshape(-1, 2)
                .mean(axis=1)[::5]
                / 32768
            )
            report["audio_match"] = match(signal, ref)
            if args.keep_focus:
                assert report["audio_match"]["correlation"] > 0.6, report["audio_match"]
            else:
                # A focus switch may shift monitor-buffer timing. Match distinct
                # parts at their expected offsets, without claiming audio quality.
                report["audio_segments"] = [
                    dict(
                        offset=offset,
                        **match(
                            signal,
                            ref[round(offset * 4410) : round((offset + 0.4) * 4410)],
                        ),
                    )
                    for offset in (0, 1, 2, 2.5)
                ]
                onset = report["audio_segments"][0]["reference_seconds"]
                for part in report["audio_segments"]:
                    assert part["correlation"] > 0.65, part
                    assert (
                        abs(part["reference_seconds"] - onset - part["offset"]) < 0.08
                    ), part
            for s in report["samples"]:
                diff = abs((s["angle_float"] - s["expected_angle"] + 180) % 360 - 180)
                assert diff < 2, s
            report["passed"] = True
            print(
                json.dumps(
                    {k: v for k, v in report.items() if k != "samples"}, indent=2
                ),
                flush=True,
            )
        except BaseException as e:
            report["error"] = repr(e)
            raise
        finally:
            if recorder:
                recorder.terminate()
                recorder.wait(timeout=3)
            if audio_file:
                audio_file.close()
            c.close()
            (OUT / (label + "-results.json")).write_text(
                json.dumps(report, indent=2) + "\n"
            )


if __name__ == "__main__":
    main()
