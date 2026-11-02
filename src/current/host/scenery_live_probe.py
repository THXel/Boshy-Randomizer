"""Check actor preservation and settled floor collisions in a scenery package."""

import argparse
import hashlib
import json
import time
from pathlib import Path
from actor_live_probe import run as actors
from actor_fire_probe import run as fire
from live_route_session import LiveRouteSession, ROOT
from route_cases import CASES

OUT = ROOT / "outputs/Fusion-Scenery-20261023"
LANDINGS = {
    "castlevania-routes": (30, 1300),
    "prehistorik-routes": (200, 150),
    "secret-mario-routes": (1020, 320),
}


def run(test, scene, mode):
    fixture = OUT / ("seed-" + scene + "-" + mode) / "plan.json"
    p = json.loads(fixture.read_text())
    with (test.lab / "Boshy.exe").open("rb") as f:
        assert hashlib.file_digest(f, "sha256").hexdigest() == p["game_sha256"]
    test.report["texture_enabled"] = mode == "on"
    test.report["bound_game_sha256"] = p["game_sha256"]
    if scene in LANDINGS:
        actors(test, scene, "on", plan_path=fixture)
        test.position(*LANDINGS[scene])
        time.sleep(2)
        first = test.obj("Player")
        time.sleep(0.4)
        last = test.obj("Player")
        assert first["y"] == last["y"], (
            "Player still falling at collision fixture",
            first,
            last,
        )
        test.report["landing"] = {
            "start": LANDINGS[scene],
            "first": first,
            "settled": last,
        }
        test.snap("collision-landing")
    else:
        fire(test, scene)
    test.report["final_station"] = test.station(CASES[scene])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "scene", choices=[*LANDINGS, "sonic-routes", "oldsonic-routes", "finale-routes"]
    )
    p.add_argument("mode", choices=["on", "off"])
    a = p.parse_args()
    t = LiveRouteSession(
        a.scene,
        OUT / ("live-" + a.scene + "-" + a.mode),
        build="scenery" if a.mode == "on" else "actors",
    )
    try:
        run(t, a.scene, a.mode)
    except BaseException as error:
        t.finish(error)
        raise
    else:
        t.finish()
