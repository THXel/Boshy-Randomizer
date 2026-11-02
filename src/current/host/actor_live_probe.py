"""Verify native actor colours, shared animation banks and death/retry in game."""

import argparse
import hashlib
import json
import struct
import time
from pathlib import Path
from live_route_session import LiveRouteSession, ROOT
from route_cases import CASES
from visuals.actor_palettes import ACTORS

OUT = ROOT / "outputs/Fusion-Actors-20261023"
SCENES = {
    "castlevania-routes": [(850, 1280), (930, 1040), (30, 1300), (850, 1280)],
    "prehistorik-routes": [(180, 1450), (2110, 300)],
    "secret-mario-routes": [(1020, 320), (2350, 320)],
    "hellokitty-routes": [],
    "dedede-fight-routes": [],
}
EXPECTED = {
    "castlevania-routes": [1088, 1089],
    "prehistorik-routes": [153, 165],
    "secret-mario-routes": [2048, 2084],
    "hellokitty-routes": [318],
    "dedede-fight-routes": [553, 561],
}


def sprite_state(state, obj):
    raw = state.b.read(obj["ptr"] + obj["rel"] - 36, 36)
    effect, rgba = struct.unpack_from("<II", raw, 24)
    common = state.b.u32(obj["ptr"] + 0x44)
    header = state.b.read(common, 8)
    size = struct.unpack_from("<I", header)[0]
    offset = struct.unpack_from("<H", header, 6)[0]
    assert 8 <= offset < size < 50000, (obj["name"], size, offset)
    bank = state.b.read(common + offset, size - offset)
    return {
        "effect": effect,
        "rgba": rgba,
        "flags": struct.unpack_from("<H", raw, 32)[0],
        "animation_bank_sha256": hashlib.sha256(bank).hexdigest(),
        "bank_size": len(bank),
        "animation_bank_hex": bank.hex(),
    }


def run(test, scene, mode, plan_path=None):
    plan = json.loads(
        (
            Path(plan_path)
            if plan_path
            else OUT / ("seed-" + scene + "-" + mode) / "plan.json"
        ).read_text()
    )
    test.report.update(
        scope=plan["scope"],
        enabled=mode == "on",
        shared_seed=plan["shared_seed"],
        samples=[],
    )
    bank = test.state.protect()
    data = b"".join(
        test.state.b.read(bank["bank"] + i, min(64000, bank["event_bytes"] - i))
        for i in range(0, bank["event_bytes"], 64000)
    )
    assert "FusionActorsV1".encode("utf-16le") in data
    test.report["compiled_actor_group_verified"] = True
    test.report["runtime_event_bytes"] = bank["event_bytes"]
    test.restart(CASES[scene])
    test.protect()
    test.report["initial"] = test.station(CASES[scene])
    seen = set()

    def capture(label):
        time.sleep(0.35)
        obs = test.state.objects()
        rows = []
        for oi in EXPECTED[scene]:
            found = [o for o in obs if o["name"] == ACTORS[oi]]
            for obj in found:
                info = sprite_state(test.state, obj)
                col = (
                    plan["actor_settings"]["RGB" + str(oi)]
                    if mode == "on"
                    else 0xFFFFFF
                )
                rgb = ((col & 255) << 16) | (col & 0xFF00) | ((col >> 16) & 255)
                assert info["rgba"] & 0xFFFFFF == rgb, (oi, hex(info["rgba"]), hex(rgb))
                assert info["rgba"] >> 24 == 255, ("Actor alpha changed", oi)
                assert obj["w"] > 0 and obj["h"] > 0
                rows.append({"source_oi": oi, **obj, **info})
                seen.add(oi)
        test.report["samples"].append({"label": label, "objects": rows})
        test.snap(label)
        print(scene, mode, label, sorted(seen), flush=True)

    capture("initial-colours")
    for i, (x, y) in enumerate(SCENES[scene]):
        test.position(x, y)
        capture("waypoint-" + str(i))
    if scene == "dedede-fight-routes":
        test.state.set_value(test.obj("Active 15"), 7, 200)
        test.wait(lambda: bool(test.objects("Active 27")))
        capture("native-late-spawn")
    assert seen == set(EXPECTED[scene]), ("Missing actor types", seen, EXPECTED[scene])
    test.death_restart(CASES[scene], "source")
    test.protect()
    capture("after-death-restart")
    test.report["actor_types_verified"] = sorted(seen)


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("scene", choices=SCENES)
    a.add_argument("mode", choices=["on", "off"])
    a.add_argument("--label", default="")
    args = a.parse_args()
    test = LiveRouteSession(
        args.scene,
        OUT / ("live-" + args.scene + "-" + args.mode + args.label),
        build="actors",
    )
    try:
        run(test, args.scene, args.mode)
    except BaseException as error:
        test.finish(error)
        raise
    else:
        test.finish()
