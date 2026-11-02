"""Serial scene checks for native cloned scenery with matching seed/save binding."""

import json
import subprocess
import sys
from pathlib import Path
from export_actor_probe import export_actor
from run_settings import normalize, encode
from live_route_session import ROOT

LAB = Path(__file__).resolve().parent
OUT = ROOT / "outputs/Fusion-Scenery-20261023"
audit = json.loads((OUT / "audit.json").read_text())
scenes = [
    "castlevania-routes",
    "prehistorik-routes",
    "secret-mario-routes",
    "sonic-routes",
    "oldsonic-routes",
    "finale-routes",
]
results = []
for scene in scenes:
    previous = json.loads((OUT / ("seed-" + scene) / "plan.json").read_text())
    for mode in (["off", "on"] if scene in scenes[:3] else ["on"]):
        build = "scenery" if mode == "on" else "actors"
        options = previous["options"]
        if mode == "off":
            options = normalize(
                {
                    **options,
                    "extras": {
                        **options["extras"],
                        "sprite_backgrounds": False,
                        "sprite_decor": False,
                        "sprite_tiles": False,
                        "sprite_dim": 0,
                    },
                }
            )
        seed = OUT / ("seed-" + scene + "-" + mode)
        export_actor(
            encode(audit["seed"], options), seed, previous["source"], build=build
        )
        print("START", scene, mode, flush=True)
        with (OUT / (scene + "-" + mode + ".log")).open("x") as log:
            boot = subprocess.run(
                [
                    sys.executable,
                    str(LAB / "scene_probe.py"),
                    "rebuilt",
                    scene,
                    "--route-build",
                    build,
                    "--save-fixture",
                    str(seed / "SaveFile1.ini"),
                    "--seconds",
                    "0",
                    "--leave-open",
                    "--output-group",
                    "Fusion-Scenery-" + scene + "-" + mode,
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=100,
            )
            assert boot.returncode == 0, ("Startup failed", scene, mode)
            check = subprocess.run(
                [sys.executable, str(LAB / "scenery_live_probe.py"), scene, mode],
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=180,
            )
        results.append(
            {
                "scene": scene,
                "mode": mode,
                "passed": check.returncode == 0,
                "evidence": "live-" + scene + "-" + mode + "/result.json",
            }
        )
        (OUT / "live-suite.json").write_text(json.dumps(results, indent=2))
        print("PASS" if check.returncode == 0 else "FAIL", scene, mode, flush=True)
        assert not any(
            r.endswith(" I Wanna Be The Boshy")
            for r in subprocess.check_output(["wmctrl", "-lp"], text=True).splitlines()
        )
