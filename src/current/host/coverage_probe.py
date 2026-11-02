"""Targeted native exit fixtures for the recovered Fusion route build."""

import argparse
import json
import time
from live_route_session import LiveRouteSession, ROOT
from route_cases import CASES
from build_profiles import BUILDS
from exit_matrix import MATRIX, exercise_matrix
from transition.router import GROUP, STAGES


def native_contact(test, name, target, label):
    obj = test.obj(name)
    test.report[label + "-contact"] = dict(obj)
    test.position(obj["x"], obj["y"])
    test.arrival(target, label)


def portal(test, native_frame, target, label):
    matches = [
        o
        for o in test.state.objects()
        if o["name"].startswith("Teleporter")
        and test.state.values(o, 4)[2] == native_frame
    ]
    assert matches, ("No native portal", native_frame)
    obj = matches[0]
    test.report[label + "-portal"] = dict(obj, values=test.state.values(obj, 4))
    test.position(obj["x"], obj["y"])
    # A real collision enables the portal. Its own timer drives the transition.
    test.arrival(target, label)


def exercise(test, scene):
    source = CASES[scene]
    test.protect()
    test.restart(source)
    test.protect()
    test.report["initial"] = test.station(source)
    test.snap("initial")
    if scene in MATRIX:
        exercise_matrix(test, scene)
    elif scene in ["questionmark-routes", "ridley-routes"]:
        boss = test.obj("randomness")
        test.report["boss_before"] = test.state.values(boss, 8)
        time.sleep(0.5)
        test.station(source)
        test.state.set_value(boss, 3, 0)
        test.arrival("save1.ini", "after-beta-victory")
        test.death_restart("save1.ini", "target")
    elif scene == "ninja-routes":
        test.position(4580, 250)
        test.arrival("boss16.ini", "ryu-entry")
        test.death_restart("boss16.ini", "ryu")
        test.protect()
        test.position(5200, 205)
        test.arrival("save22.ini", "after-ryu")
        test.protect()
        test.state.set_value(test.obj("Active 35"), 0, 135)
        test.arrival("save1.ini", "ninja-or-exit")
        test.death_restart("save1.ini", "target")
    elif scene == "kid-routes":
        test.position(777, 6607)
        test.arrival("boss_kid_icarus", "kid-entry")
        test.protect()
        test.wait(lambda: bool(test.objects("Active 26")))
        test.report["kid_before"] = test.state.values(test.obj("Active 26"), 5)
        test.station("boss_kid_icarus")
        test.state.set_value(test.obj("Active 26"), 2, 3)
        test.arrival("kid_icarus_after", "after-kid")
        test.death_restart("kid_icarus_after", "after-kid")
        test.protect()
        portal(test, 59, "save1.ini", "kid-level-exit")
        test.death_restart("save1.ini", "target")
    elif scene == "kappa-routes":
        test.position(2175, 1864)
        test.arrival("boss_kappa", "kappa-entry")
        test.death_restart("boss_kappa", "kappa")
        test.protect()
        portal(test, 29, "save1.ini", "kappa-exit")
        test.death_restart("save1.ini", "target")
    elif scene == "dedede-shortcut-routes":
        native_contact(test, "Active 52", "save1.ini", "dedede-shortcut-exit")
        test.death_restart("save1.ini", "target")
    elif scene == "random1-bonus-routes":
        portal(test, 53, "save10.ini", "bonus-world-exit")
        test.death_restart("save10.ini", "target")
    elif scene == "random1-routes":
        native_contact(test, "Active 44", "save10.ini", "part2-entry")
        test.death_restart("save10.ini", "part2")
        test.protect()
        native_contact(test, "Active 24", "save1.ini", "mega-man-door")
        test.death_restart("save1.ini", "target")
    elif scene == "random2-routes":
        native_contact(test, "Active 24", "save1.ini", "mega-man-door")
        test.death_restart("save1.ini", "target")
    elif scene == "finale-routes":
        assert test.saved().getint(GROUP, "Completed") == 0
        boss = test.obj("randomness")
        test.report["boss_before"] = test.state.values(boss, 8)
        test.state.set_value(boss, 0, 15301)
        test.state.set_value(boss, 3, 0)
        test.state.set_value(boss, 6, 350)
        test.wait(lambda: test.saved().getint(GROUP, "Completed") == 1)
        time.sleep(1)
        test.snap("native-finale")
        test.wait(lambda: bool(test.objects("Player")), seconds=30)
        test.snap("native-credits")
        test.report["outro_to_credits_observed"] = True
        test.report["completed_save"] = {
            k: dict(test.saved()[k]) for k in test.saved().sections()
        }
    else:
        raise ValueError(scene)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scene", choices=CASES)
    parser.add_argument("--build", choices=BUILDS, default="base")
    parser.add_argument("--label")
    args = parser.parse_args()
    test = LiveRouteSession(
        args.scene,
        ROOT
        / "outputs/Fusion-RouteCoverage-20261023"
        / ("live-" + (args.label or args.scene)),
        build=args.build,
    )
    try:
        exercise(test, args.scene)
    except BaseException as error:
        test.finish(error)
        raise
    else:
        test.finish()
        print(
            json.dumps(
                {
                    "scene": args.scene,
                    "passed": True,
                    "same_process": test.report["same_process"],
                }
            ),
            flush=True,
        )
