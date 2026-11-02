"""Run selected private route cases sequentially, never overlapping games."""

import argparse
import json
from pathlib import Path
import subprocess
import sys
from route_cases import CASES
from build_profiles import BUILDS, seed_folder

ROOT = Path(__file__).resolve().parents[2]
LAB = ROOT / "work/fusion-lab"
OUT = ROOT / "outputs/Fusion-RouteCoverage-20261023"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scenes", nargs="+", choices=CASES)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--build", choices=BUILDS, default="base")
    args = parser.parse_args()
    if not args.run_id or not all(c.isalnum() or c in "-_" for c in args.run_id):
        parser.error("Invalid run id")
    results = []
    for scene in args.scenes:
        print("START", scene, flush=True)
        log = OUT / (scene + "-" + args.run_id + ".log")
        with log.open("x") as stream:
            boot = subprocess.run(
                [
                    sys.executable,
                    str(LAB / "scene_probe.py"),
                    "rebuilt",
                    scene,
                    "--route-build",
                    args.build,
                    "--save-fixture",
                    str(OUT / seed_folder(scene, args.build) / "SaveFile1.ini"),
                    "--seconds",
                    "0",
                    "--leave-open",
                    "--output-group",
                    "Fusion-Coverage-" + args.run_id,
                ],
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=100,
            )
            if boot.returncode:
                raise RuntimeError("Scene boot failed: " + str(log))
            check = subprocess.run(
                [
                    sys.executable,
                    str(LAB / "coverage_probe.py"),
                    scene,
                    "--build",
                    args.build,
                    "--label",
                    scene + "-" + args.run_id,
                ],
                stdout=stream,
                stderr=subprocess.STDOUT,
                timeout=160,
            )
        results.append(
            {"scene": scene, "passed": check.returncode == 0, "log": str(log)}
        )
        print("PASS" if check.returncode == 0 else "FAIL", scene, flush=True)
        if any(
            r.endswith(" I Wanna Be The Boshy")
            for r in subprocess.check_output(["wmctrl", "-lp"], text=True).splitlines()
        ):
            raise RuntimeError("Previous test game still open; refusing another launch")
    (OUT / ("batch-" + args.run_id + ".json")).write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
