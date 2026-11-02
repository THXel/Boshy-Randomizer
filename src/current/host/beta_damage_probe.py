"""Compare native projectile damage before and after the beta fight starts."""

import argparse
import time
from live_route_session import LiveRouteSession, ROOT
from route_cases import CASES


def hits(test, phase):
    test.state.set_value(test.obj("randomness"), 0, phase)
    time.sleep(0.12)
    before = test.state.values(test.obj("randomness"), 4)
    for _ in range(3):
        test.position(100, 300)
        test.key("Right", 0.06)
        test.key("x", 0.08)
        bullets = test.objects("Bullet 2")
        assert bullets, "The original shoot action did not create a bullet"
        boss = test.obj("randomness")
        # Only place a naturally created shot: damage still comes from collision events.
        test.state.position(bullets[-1], boss["x"], boss["y"])
        time.sleep(0.12)
    after = test.state.values(test.obj("randomness"), 4)
    return {"before": before, "after": after, "damage": before[3] - after[3]}


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("scene", choices=["questionmark-routes", "ridley-routes"])
    p.add_argument("--expect", choices=["protected", "vulnerable"], required=True)
    p.add_argument("--build", choices=["base", "guards"], default="base")
    p.add_argument("--label", required=True)
    a = p.parse_args()
    test = LiveRouteSession(
        a.scene, ROOT / "outputs/Fusion-RouteCoverage-20261023" / a.label, build=a.build
    )
    try:
        test.protect()
        test.restart(CASES[a.scene])
        test.protect()
        test.report["early"] = hits(test, 500)
        assert (
            test.report["early"]["after"][0] < 780
        ), "Early fixture crossed fight start"
        test.snap("early-shots")
        if a.expect == "protected":
            assert test.report["early"]["damage"] == 0, test.report["early"]
        else:
            assert test.report["early"]["damage"] > 0, test.report["early"]
        test.report["fight"] = hits(test, 779)
        assert test.report["fight"]["damage"] > 0, test.report["fight"]
        test.snap("fight-shots")
    except BaseException as error:
        test.finish(error)
        raise
    else:
        test.finish()
        print({k: test.report[k] for k in ["early", "fight", "passed"]}, flush=True)
