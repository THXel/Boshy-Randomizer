"""Observe delayed death rendering after a visible Sonic encounter, without Q."""

import argparse
import time
from actor_live_probe import OUT
from live_route_session import LiveRouteSession
from route_cases import CASES


def run(test, scene):
    source = CASES[scene]
    test.report.update(
        scope="Palettes ON; temporary protection and player positioning at visible Sonic; no Q; delayed death images",
        attempts=[],
    )
    test.protect()
    test.restart(source)
    test.protect()
    assert test.saved().getint("FusionActorsV1", "Enabled") == 1

    def visible_boss():
        bosses = test.objects("Active 4sonic")
        return bool(
            bosses and 80 <= bosses[0]["x"] <= 550 and 50 <= bosses[0]["y"] <= 420
        )

    test.wait(visible_boss, seconds=25)
    boss = test.obj("Active 4sonic")
    test.report["boss_at_contact"] = boss
    test.position(boss["x"], boss["y"])
    test.unprotect()
    test.wait(lambda: not test.objects("Player"))
    test.snap("death-immediate")
    time.sleep(2)
    test.snap("death-2-seconds")
    time.sleep(3)
    test.snap("death-5-seconds")
    assert not test.objects("Player")
    test.restart(source)
    test.snap("restart")
    test.report["restart"] = test.station(source)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("scene", choices=["sonic-routes", "oldsonic-routes"])
    a = p.parse_args()
    test = LiveRouteSession(a.scene, OUT / ("death-" + a.scene), build="actors")
    try:
        run(test, a.scene)
    except BaseException as error:
        test.finish(error)
        raise
    else:
        test.finish()
