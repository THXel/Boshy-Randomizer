"""Versioned, run-local cosmetic shot cycle; no character unlocks or combat rules.

Native v1 uses a seeded integer generator, distinct from the legacy host's SHA
sequence. All 36 original shot frames are available, with no immediate repeats.
The interval counts whole seconds of active gameplay, never menu/death time.
"""

import hashlib
from gameplay.native_extras import advance, MODULUS

GROUP = "FusionShotsV1"
STATE = "FusionShotStateV1"
MODES = ("off", "random_interval", "spot", "death", "death_and_spot")
FRAME_COUNT = 36


def settings(seed, extras):
    mode = extras.get("shot_mode", "off")
    maximum = extras.get("shot_interval_seconds", 300)
    if mode not in MODES or type(maximum) is not int or not 1 <= maximum <= 86400:
        raise ValueError("Invalid native shot settings")
    raw = hashlib.sha256(("fusion-shots-v1\0" + seed).encode()).digest()
    return dict(
        Schema=1,
        Enabled=int(mode != "off"),
        Mode=MODES.index(mode),
        Maximum=maximum,
        InitialState=1 + int.from_bytes(raw[:4], "little") % (MODULUS - 1),
        InitialFrame=int.from_bytes(raw[4:8], "little") % FRAME_COUNT,
    )


def interval(rng, maximum):
    return 1 + rng * maximum // MODULUS


def next_frame(previous, rng):
    return (previous + 1 + rng % (FRAME_COUNT - 1)) % FRAME_COUNT


def profile(config):
    return {
        STATE: dict(
            Schema=1,
            Rng=config["InitialState"],
            Frame=config["InitialFrame"],
            Sequence=0,
            Observed=0,
            LastSpot=0,
            ResumePending=0,
            Pending=0,
            Remaining=interval(config["InitialState"], config["Maximum"]),
        )
    }


def validate(plan, config, license):
    enabled = plan["options"]["extras"].get("shot_mode", "off") != "off"
    if plan.get("native_shots_schema") is None:
        if enabled:
            raise ValueError("Shot cycling requires a newer native build")
        return
    if plan["native_shots_schema"] != 1:
        raise ValueError("Unknown native shot schema")
    expected = settings(plan["seed"], plan["options"]["extras"])
    if not config.has_section(GROUP) or dict(config[GROUP]) != {
        k.lower(): str(v) for k, v in expected.items()
    }:
        raise ValueError("Changed native shot settings")
    if not enabled:
        return
    if license is None or license.getint(STATE, "Schema", fallback=0) != 1:
        raise ValueError("Missing shot cycle profile")
    state = {k: license.getint(STATE, k) for k in profile(expected)[STATE]}
    if (
        not 0 <= state["Sequence"] <= 2147483646
        or state["Rng"] != advance(expected["InitialState"], state["Sequence"])
        or not 0 <= state["Frame"] < FRAME_COUNT
        or not 0 <= state["Observed"] <= config.getint("Stats", "Deaths", fallback=0)
        or not 0 <= state["LastSpot"] <= 1060
        or state["ResumePending"] not in (0, 1)
        or state["Pending"] not in (0, 1)
        or not 0 <= state["Remaining"] <= expected["Maximum"]
    ):
        raise ValueError("Invalid native shot progress")
    if state["Sequence"] == 0 and state["Frame"] != expected["InitialFrame"]:
        raise ValueError("Changed initial shot frame")
