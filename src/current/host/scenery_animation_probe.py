"""Compare animation layout independent of engine-local image handle allocation."""

import argparse
from live_route_session import LiveRouteSession, ROOT
from route_cases import CASES
from actor_live_probe import sprite_state, EXPECTED, ACTORS

p = argparse.ArgumentParser()
p.add_argument("scene")
p.add_argument("mode")
a = p.parse_args()
t = LiveRouteSession(
    a.scene,
    ROOT / "outputs/Fusion-Scenery-20261023" / ("animation-inspect-" + a.scene + "-" + a.mode),
    build="scenery" if a.mode == "on" else "actors",
)
try:
    t.protect()
    t.restart(CASES[a.scene])
    t.protect()
    if a.scene == "castlevania-routes":
        t.position(850, 1280)
    t.report["animations"] = {}
    for oi in EXPECTED[a.scene]:
        t.wait(lambda: bool(t.objects(ACTORS[oi])))
        o = t.objects(ACTORS[oi])[0]
        t.report["animations"][str(oi)] = sprite_state(t.state, o)
    t.report["scope"] = (
        "Read-only animation layout after private restart and positioning"
    )
except BaseException as error:
    t.finish(error)
    raise
else:
    t.finish()
