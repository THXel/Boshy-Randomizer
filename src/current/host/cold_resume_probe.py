"""Verify isolated route progress survives a complete process restart."""

import configparser
import json
from pathlib import Path
import runpy
import subprocess
import sys
from live_route_session import ROOT, PREFIX
from transition.router import GROUP

OUT = ROOT / "outputs/Fusion-RouteCoverage-20261023"
RC4 = runpy.run_path(str(ROOT / "work/Boshy-Randomizer/src/shared/PY/rc4_utils.py"))[
    "rc4_crypt"
]
CASES = [
    ("ninja-routes", "base"),
    ("kid-routes", "base"),
    ("kappa-routes", "base"),
    ("random1-routes", "base"),
    ("dedede-shortcut-routes", "guards"),
]


def progress(text):
    c = configparser.ConfigParser()
    c.read_string(text)
    group = {
        k: v
        for k, v in c[GROUP].items()
        if k.startswith("done")
        or k in ["currentstage", "completed", "binding", "schema", "catalogue"]
    }
    return {"progress": group, "frame": c.getint("Positions", "frame")}


if __name__ == "__main__":
    results = []
    for scene, build in CASES:
        case = "rebuilt-" + scene + ("-guards" if build == "guards" else "")
        before = progress(
            RC4(
                b"BLOB",
                (
                    PREFIX / "drive_c/BoshySceneTests" / case / "SaveFile1.ini"
                ).read_bytes(),
            ).decode("latin1")
        )
        with (OUT / ("cold-" + case + ".log")).open("x") as log:
            subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "work/fusion-lab/scene_probe.py"),
                    "rebuilt",
                    scene,
                    "--route-build",
                    build,
                    "--keep-save",
                    "--seconds",
                    "0",
                    "--output-group",
                    "Fusion-Coverage-Cold-20261023",
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=100,
            )
        launch = json.loads(
            (
                ROOT / "outputs/Fusion-Coverage-Cold-20261023" / case / "result.json"
            ).read_text()
        )
        after = progress(launch["save_after"])
        assert before == after, (case, before, after)
        results.append({"case": case, "passed": True, "before": before, "after": after})
        print("COLD PASS", case, flush=True)
    (OUT / "cold-resume-results.json").write_text(json.dumps(results, indent=2))
