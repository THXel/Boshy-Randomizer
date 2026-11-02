"""Native bullet kills with an isolated player-position fixture.

No enemy destruction, blood ownership, animation, or audio state is written.
Mario's final-phase enemy spawn is requested through its native spawn selector.
"""

import argparse, json, subprocess, time
import numpy as np
from pathlib import Path
from live_route_session import LiveRouteSession, ROOT
from route_cases import CASES
from blood_live_probe import particles
from run_blood_suite import launch

OUT = ROOT / "outputs/Fusion-Blood-20261024"


def streams():
    try:
        rows = json.loads(
            subprocess.check_output(
                ["pactl", "-f", "json", "list", "sink-inputs"], text=True
            )
        )
        return [
            dict(
                index=r["index"],
                corked=r.get("corked"),
                muted=r.get("mute"),
                properties={
                    k: v
                    for k, v in r.get("properties", {}).items()
                    if k
                    in (
                        "application.name",
                        "application.process.binary",
                        "media.name",
                        "application.process.id",
                    )
                },
            )
            for r in rows
            if r.get("properties", {}).get("application.name") == "Boshy.exe"
        ]
    except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError):
        return []


def run(t, scene):
    t.report.update(scope=__doc__, samples=[])
    t.protect()
    t.restart(CASES[scene])
    t.protect()
    player = t.obj("Player")
    original_player = player["ptr"]
    if scene == "mario-routes":
        t.position(240, 431)
        boss = t.obj("Classic Mario 3")
        t.state.set_value(boss, 3, 1)
        name = "throwgoomba"
        t.wait(lambda: bool(t.objects(name)))
        target = t.objects(name)[-1]
        t.state.position(target, 360, 240)
    else:
        name = "Active 14"
        t.wait(lambda: bool(t.objects(name)))
        target = t.objects(name)[0]
        t.position(target["x"] - 60, target["y"])
    t.report["enemy_before"] = target
    t.snap("enemy-before")
    t.report["audio_before"] = streams()
    audio_path = t.out / "game-audio.s16le"
    audio_file = audio_path.open("wb")
    audio_log = (t.out / "audio-capture.log").open("w")
    assert len(t.report["audio_before"]) == 1
    audio = subprocess.Popen(
        [
            "parec",
            "--monitor-stream=" + str(t.report["audio_before"][0]["index"]),
            "--rate=22050",
            "--channels=2",
            "--format=s16le",
        ],
        stdout=audio_file,
        stderr=audio_log,
    )
    t.audio_capture = (audio, audio_file, audio_log)
    time.sleep(1)
    t.report["kill_recording_started"] = True
    t.key("Right", 0.04)
    subprocess.run(["xdotool", "keydown", "x"], check=True)
    try:
        end = time.monotonic() + 12
        while time.monotonic() < end:
            matches = [
                o
                for o in t.objects(name)
                if o["slot"] == target["slot"] and o["ptr"] == target["ptr"]
            ]
            if not matches:
                # Capture the short native hit flash before reading particle
                # banks; that heavier observation can outlive the effect.
                t.report["immediate_ninja_effects"] = (
                    t.objects("Active 5") if scene == "ninja-routes" else []
                )
                break
            current = matches[0]
            t.position(current["x"] - 80, current["y"] + 12)
            time.sleep(0.05)
        else:
            raise AssertionError("Native shots did not kill the selected enemy")
    finally:
        subprocess.run(["xdotool", "keyup", "x"], check=True)
    started = time.monotonic()
    for i in range(10):
        rows = particles(t)
        assert not any(
            o["values"][6] > 0 for o in rows
        ), "Enemy blood was marked player-owned"
        assert t.obj("Player")["ptr"] == original_player
        effects = (
            [dict(o, values=t.state.values(o, 7)) for o in t.objects("Active 5")]
            if scene == "ninja-routes"
            else []
        )
        t.report["samples"].append(
            dict(seconds=time.monotonic() - started, blood=rows, ninja_effects=effects)
        )
        if i in (0, 2, 5, 9):
            t.snap("enemy-after-" + str(i))
        time.sleep(0.08)
    if scene == "mario-routes":
        assert any(
            s["blood"] for s in t.report["samples"]
        ), "Native enemy blood not observed"
        assert all(
            o["w"] <= 8 and o["h"] <= 8 for s in t.report["samples"] for o in s["blood"]
        ), "Enemy blood dimensions changed"
    else:
        assert any(s["ninja_effects"] for s in t.report["samples"]) or t.report.get(
            "immediate_ninja_effects"
        ), "Native Ninja hit effect not observed"
    time.sleep(2)
    t.report["audio_after"] = streams()
    before, after = t.report["audio_before"], t.report["audio_after"]
    assert len(before) == len(after) == 1 and before[0]["index"] == after[0]["index"]
    assert not after[0]["corked"] and not after[0]["muted"]
    t.report["same_audio_stream_active"] = True
    audio.terminate()
    audio.wait(timeout=3)
    audio_file.close()
    audio_log.close()
    del t.audio_capture
    pcm = np.frombuffer(audio_path.read_bytes(), dtype="<i2").astype(float) / 32768
    tail = pcm[-22050 * 2 :]
    assert len(tail) == 22050 * 2, "Missing game-only audio capture"
    rms = float(np.sqrt(np.mean(tail**2)))
    t.report["audio_capture"] = dict(
        file=audio_path.name,
        sample_rate=22050,
        channels=2,
        seconds=len(pcm) / (22050 * 2),
        last_second_rms=rms,
        scope="game stream only; non-silent output after enemy effect, not subjective listening",
    )
    assert rms > 0.001, "Game audio became silent after the enemy kill"
    t.report["player_alive_after_kill"] = True
    t.report["enemy_killed_by_native_collision"] = True


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("scene", choices=["mario-routes", "ninja-routes"])
    a = p.parse_args()
    with (OUT / ("enemy-" + a.scene + ".log")).open("a") as log:
        launch(a.scene, "wannafest22", "Fusion-Blood-Enemy-" + a.scene, log)
    t = LiveRouteSession(a.scene, OUT / ("enemy-" + a.scene), build="blood-wannafest22")
    try:
        run(t, a.scene)
    except BaseException as e:
        if hasattr(t, "audio_capture"):
            proc, stream, log = t.audio_capture
            proc.terminate()
            proc.wait(timeout=3)
            stream.close()
            log.close()
        t.finish(e)
        raise
    else:
        t.finish()
