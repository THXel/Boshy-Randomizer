"""Real Hello Kitty victory and exit with shot cycling; no runtime memory writes."""

import argparse
import json
import subprocess
import time
import uuid
from functools import partial
from pathlib import Path
from native_menu import builds
from menu_host.store import digest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exe", type=Path, required=True)
    args = ap.parse_args()
    builds.DYNAMIC_BASE = args.exe
    builds.DYNAMIC_SHA = digest(args.exe)
    builds.DYNAMIC_SHOTS = True
    from export_native_run import export
    from export_route_probe import ROOT
    from menu_host.store import Store, save
    from menu_host.draft import Draft
    from native_menu.combined import CombinedController
    from native_menu_probe import pump
    from native_menu_lifecycle_probe import wait_for
    from native_menu.observe import objects
    from god_mode_boss_probe import values
    from gameplay.shot_plan import STATE
    from transition.router import GROUP as ROUTE
    import god_mode_live as capture
    import native_death_visual_probe as screenshots

    out = ROOT / "outputs/Fusion-Shots-20261025"
    screenshots.OUT = capture.OUT = out
    store = Store(
        out / ("exit-profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    report = dict(
        scope=__doc__,
        memory_writes=0,
        sha256=builds.DYNAMIC_SHA,
        profile=str(store.root),
        samples=[],
    )

    def state(c):
        return dict(save(c.folder / "onlineLicense.ini")[STATE])

    with store.lock():
        d = Draft()
        d.set_mode("boss_rush")
        d.update(
            boss_pool=["hellokitty"],
            route_boss_count=1,
            god_mode=True,
            one_hp=True,
            no_mouse_ghost=True,
            autofire=True,
            skip_intro=True,
            start_character="Auto",
            characters=False,
            shot_mode="spot",
            sprite_scenery=True,
            sprite_actors=True,
        )
        d.seed = "SHOTEXIT"
        store.create(1, d)
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            c.model.slot = 1
            c.model.load_slot()
            c.begin()
            wait_for(c, lambda: c.phase == "playing", seconds=35)
            pump(c, 0.5)
            report["entry"] = state(c)
            from blood_enemy_probe import streams

            audio = streams()
            assert len(audio) == 1
            report["audio_stream"] = audio[0]
            audio_path = out / "shot-exit-audio.s16le"
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
            pump(c, 0.4)
            subprocess.run(["xdotool", "keydown", "x"], check=True)
            started = time.monotonic()
            seen = False
            dead = False
            last = 0
            try:
                while time.monotonic() - started < 90:
                    pump(c, 0.25)
                    obs = objects(c.window.reader)
                    boss = next((o for o in obs if o["name"] == "hellokitty"), None)
                    if boss:
                        seen = True
                        hp = values(c.window.reader, boss, 3)[1]
                        report["samples"].append(
                            dict(t=round(time.monotonic() - started, 2), hp=hp)
                        )
                        if hp <= 0:
                            dead = True
                            break
                    elif seen:
                        dead = True
                        break
                    if time.monotonic() - last > 10:
                        print("FIGHT", report["samples"][-1:], flush=True)
                        last = time.monotonic()
            finally:
                subprocess.run(["xdotool", "keyup", "x"], check=True)
                pump(c, 0.5)
                recorder.terminate()
                recorder.wait(timeout=3)
                audio_file.close()
            from music.continuity import decoded, match
            from music.bank import read as read_bank
            from visuals.scenery_pack import App
            import numpy as np

            app = App(args.exe)
            bank, _ = read_bank(app.payload(0x6668), app.payload(0x5557))
            signal = (
                np.frombuffer(audio_path.read_bytes(), dtype="<i2")
                .reshape(-1, 2)
                .mean(axis=1)[::5]
                / 32768
            )
            report["sound_matches"] = {
                name: match(
                    signal,
                    decoded(next(s.audio for s in bank.values() if s.name == name)),
                )
                for name in ("Luigi_shoot", "shoot")
            }
            print("AUDIO", report["sound_matches"], flush=True)
            assert seen and dead, "Boss victory not observed"
            report["defeated"] = state(c)
            screenshots.snapshot(c, "shots-exit-victory")
            assert report["defeated"]["sequence"] == report["entry"]["sequence"]
            print("BRIDGE waiting for original victory animation", flush=True)
            pump(c, 30)
            for attempt in range(18):
                cfg = save(c.folder / "SaveFile1.ini")
                if cfg.getint(ROUTE, "CurrentStage") != 1:
                    break
                subprocess.run(["xdotool", "keydown", "Right"], check=True)
                try:
                    c.window.key("Shift_L")
                    c.window.key("z")
                    pump(c, 0.45)
                finally:
                    subprocess.run(["xdotool", "keyup", "Right"], check=True)
                pump(c, 0.25)
                print(
                    "WALK",
                    attempt,
                    [
                        (o["x"], o["y"])
                        for o in objects(c.window.reader)
                        if o["name"] == "Player"
                    ],
                    flush=True,
                )
            wait_for(
                c,
                lambda: c.window.reader.frame() == "Eleventh Boss - Solgryn",
                seconds=15,
            )
            pump(c, 0.5)
            report["arrival"] = state(c)
            cfg = save(c.folder / "SaveFile1.ini")
            assert cfg.getint(ROUTE, "Done1") == 1
            assert (
                int(report["arrival"]["sequence"])
                == int(report["entry"]["sequence"]) + 1
            )
            assert report["arrival"]["frame"] != report["entry"]["frame"]
            screenshots.snapshot(c, "shots-exit-solgryn")
            c.window.key("F2")
            wait_for(c, lambda: c.phase == "menu")
            c.enter()
            store.resume(1)
            report["passed"] = True
            print("PASS real boss exit", report["entry"], report["arrival"], flush=True)
        except BaseException as error:
            report["error"] = repr(error)
            try:
                screenshots.snapshot(c, "shots-exit-failure")
            except Exception:
                pass
            raise
        finally:
            subprocess.run(["xdotool", "keyup", "x", "Right", "Left"], check=False)
            c.close()
            (out / "exit-live-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )


if __name__ == "__main__":
    main()
