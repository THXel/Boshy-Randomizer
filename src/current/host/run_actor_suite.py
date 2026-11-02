"""Sequential isolated actor comparisons, one game process at a time."""

import json
import subprocess
import sys
from actor_live_probe import ROOT, OUT, SCENES

LAB = ROOT / "work/fusion-lab"
results = []
for scene in SCENES:
    for mode in ["off", "on"]:
        label = scene + "-" + mode + "-confirmed"
        prior = OUT / ("live-" + label) / "result.json"
        if prior.exists() and json.loads(prior.read_text()).get("passed"):
            results.append(
                {
                    "scene": scene,
                    "mode": mode,
                    "passed": True,
                    "evidence": "live-" + label + "/result.json",
                }
            )
            print("ALREADY PASS", label, flush=True)
            continue
        print("START", label, flush=True)
        with (OUT / (label + ".log")).open("x") as log:
            boot = subprocess.run(
                [
                    sys.executable,
                    str(LAB / "scene_probe.py"),
                    "rebuilt",
                    scene,
                    "--route-build",
                    "actors",
                    "--save-fixture",
                    str(OUT / ("seed-" + scene + "-" + mode) / "SaveFile1.ini"),
                    "--seconds",
                    "0",
                    "--leave-open",
                    "--output-group",
                    "Fusion-Actors-" + label,
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=100,
            )
            assert boot.returncode == 0, ("Boot failure", label)
            check = subprocess.run(
                [
                    sys.executable,
                    str(LAB / "actor_live_probe.py"),
                    scene,
                    mode,
                    "--label=-confirmed",
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=160,
            )
        results.append(
            {
                "scene": scene,
                "mode": mode,
                "passed": check.returncode == 0,
                "evidence": "live-" + label + "/result.json",
            }
        )
        (OUT / "actor-suite.json").write_text(json.dumps(results, indent=2))
        print("PASS" if check.returncode == 0 else "FAIL", label, flush=True)
        assert not any(
            r.endswith(" I Wanna Be The Boshy")
            for r in subprocess.check_output(["wmctrl", "-lp"], text=True).splitlines()
        )
