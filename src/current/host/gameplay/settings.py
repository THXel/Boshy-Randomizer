"""Versioned native per-run rules, including compatibility with older saves."""

from gameplay.god_mode import GROUP as GROUP, settings as god_settings

CONTROLS = (
    "autofire",
    "no_mouse_ghost",
    "one_hp",
    "skip_intro",
    "fast_chests",
    "quiet_pickups",
)


def settings(extras, schema=5, difficulty=0):
    if type(schema) is not int or schema not in (1, 2, 3, 4, 5):
        raise ValueError("Unknown native gameplay schema")
    if type(difficulty) is not int or difficulty not in range(4):
        raise ValueError("Invalid native difficulty")
    if any(type(extras.get(k, False)) is not bool for k in ("god_mode", *CONTROLS)):
        raise ValueError("Gameplay flags must be boolean")
    if schema < 4 and extras.get("skip_intro", False):
        raise ValueError("Intro skip requires a newer native gameplay build")
    if schema < 5 and any(
        extras.get(k, False) for k in ("fast_chests", "quiet_pickups")
    ):
        raise ValueError("Pickup options require a newer native gameplay build")
    result = god_settings(extras["god_mode"])
    if schema == 1:
        if any(extras.get(k, False) for k in CONTROLS):
            raise ValueError("Controls require a newer native gameplay build")
        return result
    result.update(
        Schema=2,
        AutoFireMaxDifficulty=3 if extras["autofire"] else 0,
        MouseGhostDisabled=1 if extras["no_mouse_ghost"] else 0,
    )
    if schema == 2:
        if extras["one_hp"]:
            raise ValueError("One-hit requires a newer native gameplay build")
        return result
    result.update(
        Schema=3,
        OneHit=int(extras["one_hp"]),
        OneHitSonicFloor=(35, 90, 90, 180)[difficulty],
    )
    if schema >= 4:
        result.update(Schema=4, SkipIntro=int(extras.get("skip_intro", False)))
    if schema == 5:
        result.update(
            Schema=5,
            FastChests=int(extras.get("fast_chests", False)),
            QuietPickups=int(extras.get("quiet_pickups", False)),
        )
    return result
