"""Run native fire-phase fixtures serially, keeping every test's evidence."""

import json
import subprocess
import sys
from actor_live_probe import OUT, ROOT

LAB = ROOT / "work/fusion-lab"
results = []
for scene in ["sonic-routes", "oldsonic-routes", "finale-routes"]:
    print("START fire", scene, flush=True)
    with (OUT / ("fire-" + scene + ".log")).open("x") as log:
        boot = subprocess.run(
            [
                sys.executable,
                str(LAB / "scene_probe.py"),
                "rebuilt",
                scene,
                "--route-build",
                "actors",
                "--save-fixture",
                str(OUT / ("seed-" + scene + "-on") / "SaveFile1.ini"),
                "--seconds",
                "0",
                "--leave-open",
                "--output-group",
                "Fusion-Actors-Fire-" + scene,
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=100,
        )
        assert boot.returncode == 0, scene
        check = subprocess.run(
            [sys.executable, str(LAB / "actor_fire_probe.py"), scene],
            stdout=log,
            stderr=subprocess.STDOUT,
            timeout=180,
        )
    results.append(
        {
            "scene": scene,
            "passed": check.returncode == 0,
            "evidence": "fire-" + scene + "/result.json",
        }
    )
    (OUT / "fire-suite.json").write_text(json.dumps(results, indent=2))
    print("PASS" if check.returncode == 0 else "FAIL", scene, flush=True)
    assert not any(
        r.endswith(" I Wanna Be The Boshy")
        for r in subprocess.check_output(["wmctrl", "-lp"], text=True).splitlines()
    )
