"""Observe native blood ownership and expiration, without altering particles."""

import argparse, json, time
from pathlib import Path
from live_route_session import LiveRouteSession, ROOT
from route_cases import CASES
from actor_live_probe import sprite_state

OUT = ROOT / "outputs/Fusion-Blood-20261024"


def particles(t):
    result = []
    for o in t.state.objects():
        if o["name"] in ("Active 2", "blood"):
            values = t.state.values(o, 7)
            # Unrelated objects may share a display name; the blood lifetime
            # and immutable common-bank size distinguish the private prototype.
            if len(values) != 7:
                continue  # ordinary particles can expire during observation
            common = t.state.b.u32(o["ptr"] + 0x44)
            if t.state.b.u32(common) != 398:
                continue
            result.append(dict(**o, values=values, visual=sprite_state(t.state, o)))
    return result


def run(t, scene, pack):
    t.report.update(
        scope="synthetic start/protection; native Q death and R restart; no blood image or lifetime writes",
        pack=pack,
        samples=[],
    )
    t.protect()
    t.restart(CASES[scene])
    t.protect()
    if scene == "castlevania-routes":
        t.position(850, 1280)
    t.snap("alive")
    t.unprotect()
    # The normal Q key invokes the game's ordinary player-death event.
    t.key("q", 0.06)
    t.wait(lambda: not t.objects("Player"))
    started = time.monotonic()
    for index in range(12):
        rows = particles(t)
        t.report["samples"].append(
            dict(seconds=time.monotonic() - started, particles=rows)
        )
        if index in (0, 1, 2, 4, 7, 11):
            t.snap("death-" + str(index))
        time.sleep(0.12)
    owned = [
        o for s in t.report["samples"] for o in s["particles"] if o["values"][6] > 0
    ]
    if pack == "original":
        assert not owned, "Vanilla blood incorrectly marked custom"
        assert any(s["particles"] for s in t.report["samples"])
    else:
        assert owned, "No player-owned native blood observed"
        expect = (32, 31) if pack == "kamilia3" else (20, 20)
        assert any((o["w"], o["h"]) == expect for o in owned), (
            expect,
            [(o["w"], o["h"]) for o in owned[:8]],
        )
        time.sleep(0.8)
        assert not any(
            o["values"][6] > 0 for o in particles(t)
        ), "Custom blood failed to expire"
    time.sleep(2)
    t.snap("death-late")
    t.restart(CASES[scene])
    t.protect()
    t.snap("restart")
    assert not any(o["values"][6] > 0 for o in particles(t))
    t.report["restart"] = t.station(CASES[scene])


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("scene")
    p.add_argument("pack")
    a = p.parse_args()
    t = LiveRouteSession(
        a.scene, OUT / ("live-" + a.scene + "-" + a.pack), build="blood-" + a.pack
    )
    try:
        run(t, a.scene, a.pack)
    except BaseException as e:
        t.finish(e)
        raise
    else:
        t.finish()
