"""Targeted native fire phases with actor palettes enabled; private fixtures only."""

import argparse
import json
import time
from actor_live_probe import OUT
from live_route_session import LiveRouteSession
from route_cases import CASES


def run(test, scene):
    solgryn = scene == "finale-routes"
    source = CASES[scene]
    test.report.update(
        scope="Actor palettes ON; temporary godmode, boss HP and climb-entry position; not a full fight",
        samples=[],
    )
    test.protect()
    test.restart(source)
    test.protect()
    test.report["initial"] = test.station(source)
    assert test.saved().getint("FusionActorsV1", "Enabled") == 1
    bossname = "randomness" if solgryn else "Active 4sonic"
    boss = test.obj(bossname)
    test.report["boss_before"] = test.state.values(boss)
    test.state.set_value(boss, 3 if solgryn else 1, 0 if solgryn else 35)
    if not solgryn:
        test.position(320, 400)
    started = time.monotonic()
    entered = False
    while time.monotonic() - started < (63 if solgryn else 34):
        obs = test.state.objects()
        boss = next((o for o in obs if o["name"] == bossname), None)
        values = test.state.values(boss) if boss else []
        player = next((o for o in obs if o["name"] == "Player"), None)
        assert player, "Player disappeared during protected phase"
        if solgryn and values and values[0] == 5999 and not entered:
            test.position(300, -8)
            entered = True
        objects = [
            o
            for o in obs
            if (
                "sonic" in o["name"].lower()
                or (
                    solgryn
                    and o["name"]
                    in ("Active 9", "Active 10", "Active 14", "randomness")
                )
            )
        ]
        row = {
            "seconds": round(time.monotonic() - started, 3),
            "boss_values": values,
            "objects": objects,
            "player": player,
            "image": "phase-%03d" % len(test.report["samples"]),
        }
        test.snap(row["image"])
        test.report["samples"].append(row)
        if len(test.report["samples"]) % 15 == 0:
            print(scene, row["seconds"], values, flush=True)
        time.sleep(0.35)
    test.report["climb_entered"] = entered
    names = {o["name"] for r in test.report["samples"] for o in r["objects"]}
    if solgryn:
        assert entered, "Climb entry phase not reached"
        assert {"Active 9", "Active 10"} <= names, ("Missing fire effects", names)
    else:
        widths = [
            o["w"]
            for r in test.report["samples"]
            for o in r["objects"]
            if o["name"] == "Active 23sonic"
        ]
        test.report["platform_widths"] = sorted(set(widths))
        assert widths and min(widths) == 168, ("Fire platform not shrunk", widths)
    if solgryn:
        test.death_restart(source, "fire")
        test.report["death_trigger"] = "Q self-death"
    else:
        test.unprotect()
        boss = test.obj(bossname)
        test.report["death_fixture_boss"] = boss
        test.position(boss["x"], boss["y"])
        test.wait(lambda: not test.objects("Player"))
        test.snap("fire-death")
        test.restart(source)
        test.snap("fire-restart")
        test.report["death_trigger"] = (
            "native hazard death after positioning at Sonic; no Q"
        )

    test.report["after_restart"] = test.station(source)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument(
        "scene", choices=["sonic-routes", "oldsonic-routes", "finale-routes"]
    )
    a = p.parse_args()
    test = LiveRouteSession(a.scene, OUT / ("fire-" + a.scene), build="actors")
    try:
        run(test, a.scene)
    except BaseException as error:
        test.finish(error)
        raise
    else:
        test.finish()
