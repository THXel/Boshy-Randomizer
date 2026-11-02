"""Serial native music regressions: actual enemy shots and player Q/R cycle."""

import json, subprocess, sys
from pathlib import Path
from live_route_session import LiveRouteSession, ROOT
from export_actor_probe import export_actor
from run_settings import encode
from blood_enemy_probe import run as enemy_run
from blood_live_probe import run as death_run
from run_blood_suite import fixture as blood_fixture
from prepare_music_builds import OUT, SEED

LAB = Path(__file__).resolve().parent


def one(scene, pack, kind):
    result = OUT / (kind + "-" + scene + "-" + pack)
    if (result / "result.json").exists():
        d = json.loads((result / "result.json").read_text())
        if not d["passed"]:
            raise RuntimeError("Previous failure requires review: " + str(result))
        return
    seed = OUT / ("seed-" + scene + "-" + pack)
    if not seed.exists():
        p = json.loads((blood_fixture(scene, pack) / "plan.json").read_text())
        p["options"]["extras"]["music"] = True
        export_actor(
            encode(SEED, p["options"]), seed, p["source"], build="music-" + pack
        )
    group = "Fusion-Music-" + kind + "-" + scene + "-" + pack
    if (ROOT / "outputs" / group).exists():
        group += "-retry"
    with (OUT / (kind + "-" + scene + "-" + pack + ".log")).open("a") as log:
        r = subprocess.run(
            [
                sys.executable,
                str(LAB / "scene_probe.py"),
                "rebuilt",
                scene,
                "--route-build",
                "music-" + pack,
                "--save-fixture",
                str(seed / "SaveFile1.ini"),
                "--seconds",
                "0",
                "--leave-open",
                "--output-group",
                group,
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=100,
        )
        if r.returncode:
            raise RuntimeError("Scene startup failed; see " + str(log.name))
    t = LiveRouteSession(scene, result, build="music-" + pack)
    try:
        if kind == "enemy":
            enemy_run(t, scene)
        else:
            death_run(t, scene, pack)
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
    print("PASS", kind, scene, pack, flush=True)


if __name__ == "__main__":
    for pack in ("wannafest22", "kamilia3", "original"):
        for scene in ("mario-routes", "ninja-routes"):
            one(scene, pack, "enemy")
        one("sonic-routes", pack, "death")
