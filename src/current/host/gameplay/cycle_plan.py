"""Seeded character priorities and persistent, stage-local selection records.

Uses the previous character-cycle-v1 ordering. Native events filter these
priorities against currently unlocked characters at each route station.
"""

import hashlib, json
from gameplay.characters import ROSTER, ROSTER_PATH, selected, profile_text
from transition.router import STAGES

GROUP = "FusionCycleV1"
RANKS = "FusionCycleRanksV1"
STARTERS = {
    c["name"]
    for c in json.loads(ROSTER_PATH.read_text())["characters"]
    if c["status"] == "unlocked"
}


def order(seed, index):
    return sorted(
        ROSTER,
        key=lambda name: hashlib.sha256(
            f"{seed}\0character-cycle-v1\0{index}\0{name}".encode()
        ).digest(),
    )


def choose(seed, index, unlocks, previous=None):
    available = [
        name
        for name in order(seed, index)
        if name in STARTERS or str(unlocks.get(name.lower(), 0)) == "1"
    ]
    name = next((name for name in available if name != previous), available[0])
    return dict(name=name, id=ROSTER[name])


def initial(options, seed):
    explicit = selected(options)
    if (
        explicit is None
        and options.get("extras", {}).get("death_character", False)
        and not options["characters"]
    ):
        explicit = selected({"start_character": "Dark Boshy"})
    if explicit is not None or not options["characters"]:
        return explicit
    return choose(seed, 0, {})


def settings(seed, route, enabled):
    if type(enabled) is not bool:
        raise ValueError("Cycle setting must be boolean")
    result = {GROUP: dict(Schema=1, Enabled=int(enabled))}
    if enabled:
        ranks = {}
        for index, spot in enumerate(route):
            sid = STAGES[spot]["id"]
            for rank, name in enumerate(order(seed, index), 1):
                ranks[f"{sid}_{ROSTER[name]}"] = rank
        result[RANKS] = ranks
    return result


def profile(choice, enabled, source):
    text = profile_text(choice)
    if not enabled:
        return text
    sid = STAGES[source]["id"]
    return (
        text
        + f"\r\n[{GROUP}]\r\nSchema=1\r\nEnabled=1\r\nLastStage={sid}\r\nHistoryId{sid}={choice['id']}\r\nHistoryName{sid}={choice['name']}\r\n"
    )


def validate(plan, config, license):
    if plan["options"].get("mode") == "normal":
        from gameplay.normal_plan import validate as normal_validate

        return normal_validate(plan, config, license)
    if plan["options"].get("mode") == "target":
        from gameplay.target_plan import validate as target_validate

        return target_validate(plan, config, license)
    enabled = plan["options"]["characters"]
    if "cycle_schema" not in plan:
        if enabled:
            raise ValueError("Character cycling requires a newer build")
        return
    if plan["cycle_schema"] != 1:
        raise ValueError("Unsupported character cycle schema")
    for group, values in settings(plan["seed"], plan["route"], enabled).items():
        if not config.has_section(group) or dict(config[group]) != {
            k.lower(): str(v) for k, v in values.items()
        }:
            raise ValueError("Character priorities do not match seed")
    if not enabled:
        return
    if (
        license.getint(GROUP, "Schema", fallback=0) != 1
        or license.getint(GROUP, "Enabled", fallback=0) != 1
    ):
        raise ValueError("Invalid saved character cycle")
    ids = {STAGES[s]["id"] for s in plan["route"]}
    last = license.getint(GROUP, "LastStage")
    if last not in ids:
        raise ValueError("Unknown character station")
    for sid in ids:
        cid = license.getint(GROUP, f"HistoryId{sid}", fallback=0)
        name = license.get(GROUP, f"HistoryName{sid}", fallback="")
        if bool(cid) != bool(name) or cid and ROSTER.get(name) != cid:
            raise ValueError("Invalid saved character history")
    if not license.getint(GROUP, f"HistoryId{last}", fallback=0):
        raise ValueError("Missing current character history")
