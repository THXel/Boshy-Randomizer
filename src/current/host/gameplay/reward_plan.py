"""Canonical 36-location mixed pool, shared with the previous randomizer.

Every physical chest has its own receipt. Owning a reward never consumes a
second chest. Names and kinds are immutable per run and bound to the seed.
"""

import json
import sys
from pathlib import Path

from app_paths import REPO
sys.path.insert(0, str(REPO / "src/python/rules"))
from mixed_rewards import assignments

CATALOGUE = REPO / "assets/catalogues/slot_reward_plan.json"
LOCATIONS = json.loads(CATALOGUE.read_text())["locations"]
GROUP = "FusionRewardsV1"
CHECKS = "RandoChecks"


def mapping(seed, enabled):
    if (
        not isinstance(seed, str)
        or not 1 <= len(seed) <= 256
        or type(enabled) is not bool
    ):
        raise ValueError("Invalid reward seed/settings")
    if enabled:
        return assignments(seed, {"locations": LOCATIONS})
    return {l["key"]: dict(name=l["source"], kind=l["source_kind"]) for l in LOCATIONS}


def settings(seed, enabled):
    result = {"Schema": 1, "Enabled": int(enabled)}
    for key, reward in mapping(seed, enabled).items():
        result["Name" + key] = reward["name"]
        result["Kind" + key] = int(reward["kind"] == "character")
    return result


def validate(plan, config):
    expected = mapping(plan["seed"], plan["options"]["items"])
    if plan.get("rewards") != expected:
        raise ValueError("Rewards do not match seed")
    for key, value in settings(plan["seed"], plan["options"]["items"]).items():
        if config.get(GROUP, key, fallback=None) != str(value):
            raise ValueError("Changed reward settings: " + key)
    if plan.get("runtime_reward_icons_schema") is not None:
        from gameplay.runtime_reward_icons import settings as runtime_settings

        if plan["runtime_reward_icons_schema"] != 1:
            raise ValueError("Unknown runtime reward artwork schema")
        for key, value in runtime_settings(
            plan["seed"], plan["options"]["items"]
        ).items():
            if config.get(GROUP, key, fallback=None) != str(value):
                raise ValueError("Changed runtime reward artwork selection")
    keys = {l["key"].lower() for l in LOCATIONS}
    for key, value in config.items(CHECKS) if config.has_section(CHECKS) else []:
        if key.lower() not in keys or value not in ("0", "1"):
            raise ValueError("Invalid chest receipt")
