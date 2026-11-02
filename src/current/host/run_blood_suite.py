"""Serial, isolated native player death checks for both local packs."""

import json, subprocess, sys
from pathlib import Path
from export_actor_probe import export_actor
from live_route_session import ROOT
from run_settings import encode, normalize

LAB = Path(__file__).resolve().parent
OUT = ROOT / "outputs/Fusion-Blood-20261024"
old = ROOT / "outputs/Fusion-Scenery-20261023"
audit = json.loads((old / "audit.json").read_text())


def fixture(scene, pack):
    target = OUT / ("seed-" + scene + "-" + pack)
    if target.exists():
        return target
    previous = old / ("seed-" + scene + "-on") / "plan.json"
    if not previous.exists():
        previous = (
            ROOT
            / "outputs/Fusion-RouteCoverage-20261023"
            / ("seed-guards-" + scene)
            / "plan.json"
        )
    if scene == "mario-routes":
        previous = ROOT / "outputs/Fusion-FrameLinks-20261023/seed-mario/plan.json"
    p = json.loads(previous.read_text())
    options = normalize(
        {**p["options"], "extras": {**p["options"]["extras"], **audit["options"]}}
    )
    export_actor(
        encode(audit["seed"], options), target, p["source"], build="blood-" + pack
    )
    return target


def launch(scene, pack, group, log):
    seed = fixture(scene, pack)
    initial = group
    attempt = 1
    while (ROOT / "outputs" / group).exists():
        group = initial + "-retry" + str(attempt)
        attempt += 1
    run = subprocess.run(
        [
            sys.executable,
            str(LAB / "scene_probe.py"),
            "rebuilt",
            scene,
            "--route-build",
            "blood-" + pack,
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
    assert run.returncode == 0, ("startup", scene, pack)


if __name__ == "__main__":
    cases = [
        ("castlevania-routes", "kamilia3"),
        ("castlevania-routes", "original"),
        ("castlevania-routes", "wannafest22"),
        ("sonic-routes", "kamilia3"),
        ("sonic-routes", "wannafest22"),
        ("finale-routes", "wannafest22"),
    ]
    results = []
    for scene, pack in cases:
        path = OUT / ("live-" + scene + "-" + pack) / "result.json"
        if not path.exists():
            with (OUT / ("live-" + scene + "-" + pack + ".log")).open("a") as log:
                launch(scene, pack, "Fusion-Blood-" + scene + "-" + pack, log)
                run = subprocess.run(
                    [sys.executable, str(LAB / "blood_live_probe.py"), scene, pack],
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    timeout=90,
                )
                assert run.returncode == 0, ("probe", scene, pack)
        d = json.loads(path.read_text())
        assert d["passed"] and d["same_process"]
        results.append(
            dict(scene=scene, pack=pack, passed=True, result=str(path.relative_to(OUT)))
        )
        print("PASS", scene, pack, flush=True)
        (OUT / "death-suite.json").write_text(json.dumps(results, indent=2))
