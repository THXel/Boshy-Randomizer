"""Collected rewards read from native save receipts, shared by menu and tracker."""

from gameplay.reward_plan import LOCATIONS


def collected(config, profile):
    items = [
        dict(
            name=n, kind="item", done=config.getint("Collectables", n, fallback=0) == 1
        )
        for n in sorted(
            {r["source"] for r in LOCATIONS if r["source_kind"] == "item"} | {"Gastly"}
        )
    ]
    chars = [
        dict(
            name=n,
            kind="character",
            done=profile.getint("Unlockables", n, fallback=0) == 1,
        )
        for n in sorted(
            {r["source"] for r in LOCATIONS if r["source_kind"] == "character"}
        )
    ]
    return items, chars
