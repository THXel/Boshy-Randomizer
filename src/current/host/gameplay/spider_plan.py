"""Versioned native spider schedule, persisted independently for each run."""

import hashlib
from gameplay.native_extras import advance, MODULUS

GROUP = "FusionSpiderV1"
STATE = "FusionSpiderStateV1"
MINIMUM = 300
MAXIMUM = 1800
GRACE = 750  # Original game runs at 50 updates/second.
SPEED = 475


def interval(rng):
    return MINIMUM + rng * (MAXIMUM - MINIMUM + 1) // MODULUS


def settings(seed, extras):
    enabled = extras.get("spider", False)
    if type(enabled) is not bool:
        raise ValueError("Spider setting must be boolean")
    raw = hashlib.sha256(("fusion-spider-v1\0" + seed).encode()).digest()
    rng = 1 + int.from_bytes(raw[:4], "little") % (MODULUS - 1)
    return dict(Schema=1, Enabled=int(enabled), InitialState=rng)


def profile(config):
    return {
        STATE: dict(
            Schema=1,
            Rng=config["InitialState"],
            Remaining=interval(config["InitialState"]),
            Attacks=0,
            Hits=0,
        )
    }


def validate(plan, config, license):
    enabled = plan["options"]["extras"].get("spider", False)
    if plan.get("native_spider_schema") is None:
        if enabled:
            raise ValueError("Spider requires a newer native build")
        return
    if plan["native_spider_schema"] != 1:
        raise ValueError("Unknown native spider schema")
    expected = settings(plan["seed"], plan["options"]["extras"])
    if not config.has_section(GROUP) or dict(config[GROUP]) != {
        k.lower(): str(v) for k, v in expected.items()
    }:
        raise ValueError("Changed native spider settings")
    if not enabled:
        return
    if license is None or license.getint(STATE, "Schema", fallback=0) != 1:
        raise ValueError("Missing spider state")
    st = {k: license.getint(STATE, k) for k in profile(expected)[STATE]}
    if (
        not 0 <= st["Attacks"] <= 715827882
        or not 0 <= st["Hits"] <= st["Attacks"]
        or not 0 <= st["Remaining"] <= MAXIMUM
        or st["Rng"] != advance(expected["InitialState"], st["Attacks"] * 3)
    ):
        raise ValueError("Invalid native spider progress")
