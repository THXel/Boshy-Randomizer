"""Native Target goals and an unlimited, save-local route rotation.

Goal selection retains target-v1 exactly. Routing uses a new seed-ranked native
rotation with separate room/boss cursors. This is deliberately versioned apart
from the former host-injected SHA-per-visit route. No finite itinerary is used.
"""

import hashlib
from gameplay.reward_plan import LOCATIONS, CATALOGUE
from gameplay import normal_plan
from gameplay.characters import ROSTER, profile_text
from transition.router import STAGES, GROUP as ROUTE
from beta_catalogue import BOSSES, goals as legacy_goals

GROUP = "FusionTargetV1"
CONFIG = "FusionTargetConfigV1"
RANKS = "FusionTargetRanksV1"
CHARACTERS = "FusionTargetCharactersV1"
ITEMS = sorted({l["source"] for l in LOCATIONS if l["source_kind"] == "item"})
FINAL = "boss_solgryn.ini"
POOL = {k: v for k, v in STAGES.items() if k != FINAL}
BOSS_STAGES = {k: STAGES[v[2]]["id"] for k, v in BOSSES.items()}
SIZE = len(POOL)


def goals(seed, options):
    return legacy_goals(CATALOGUE.parent, seed, options)


def order(seed):
    return sorted(
        POOL,
        key=lambda k: hashlib.sha256(
            f"{seed}\0fusion-target-route-v1\0{k}".encode()
        ).digest(),
    )


def settings(seed, options):
    selected = goals(seed, options)
    return {
        CONFIG: dict(
            Schema=1,
            Enabled=1,
            Characters=int(options["characters"]),
            **{
                "Item" + str(i): int(n in selected["items"])
                for i, n in enumerate(ITEMS)
            },
            **{
                "Boss" + str(sid): int(k in selected["bosses"])
                for k, sid in BOSS_STAGES.items()
            },
        ),
        RANKS: {str(STAGES[k]["id"]): n for n, k in enumerate(order(seed), 1)},
        normal_plan.RANKS: normal_plan.settings(seed, options["characters"])[
            normal_plan.RANKS
        ],
    }


def initial_state():
    return {
        GROUP: dict(Ready=0, Visit=0, CursorRooms=1, CursorBosses=1),
        ROUTE: {"Done" + str(s["id"]): 0 for s in POOL.values()},
    }


def progress(selected, c):
    return dict(
        items=[
            n for n in selected["items"] if c.getint("Collectables", n, fallback=0) == 1
        ],
        bosses=[
            k
            for k in selected["bosses"]
            if c.getint(ROUTE, "Done" + str(BOSS_STAGES[k]), fallback=0) == 1
        ],
    )


def ready(selected, c):
    return progress(selected, c) == selected


def choose(seed, current, cursors, done, complete=False):
    if complete:
        return FINAL
    source = STAGES[current]
    priorities = {k: i for i, k in enumerate(order(seed), 1)}
    eligible = [
        k
        for k, s in POOL.items()
        if k != current
        and (
            s["frame"] not in source["frames"]
            or s.get("segment") != source.get("segment")
        )
        and (s["category"] != "bosses" or s["id"] not in done)
    ]

    def score(k):
        category = POOL[k]["category"]
        rank = priorities[k]
        cursor = cursors["CursorRooms" if category == "rooms" else "CursorBosses"]
        return (
            rank
            + (100 if rank < cursor else 0)
            + (1000 if category == source["category"] else 0)
        )

    return min(eligible, key=score)


def profile(choice, enabled):
    text = profile_text(choice)
    if enabled:
        text += f"\r\n[{CHARACTERS}]\r\nSchema=1\r\nCharacters=1\r\nLastVisit=0\r\nStep=1\r\n"
    return text


def validate(plan, c, license):
    if plan.get("target_schema") != 1 or plan["route"] or plan["source"] != "save1.ini":
        raise ValueError("Invalid native Target plan")
    selected = goals(plan["seed"], plan["options"])
    if plan.get("targets") != selected:
        raise ValueError("Target goals do not match seed")
    for group, values in settings(plan["seed"], plan["options"]).items():
        if not c.has_section(group) or dict(c[group]) != {
            k.lower(): str(v) for k, v in values.items()
        }:
            raise ValueError("Changed Target settings: " + group)
    for key in ("CursorRooms", "CursorBosses"):
        if not 1 <= c.getint(GROUP, key) <= SIZE:
            raise ValueError("Invalid Target cursor")
    visit = c.getint(GROUP, "Visit")
    if not 0 <= visit < 2**31 - 1 or c.getint(GROUP, "Ready") not in (0, 1):
        raise ValueError("Invalid Target progress")
    for s in POOL.values():
        if c.getint(ROUTE, "Done" + str(s["id"]), fallback=0) not in (0, 1):
            raise ValueError("Invalid Target completion receipt")
    unlocked = ready(selected, c)
    if c.getint(GROUP, "Ready") and not unlocked:
        raise ValueError("Finale unlocked without goals")
    if c.getint(ROUTE, "CurrentStage") == STAGES[FINAL]["id"] and not unlocked:
        raise ValueError("Premature Target finale")
    if c.getint(ROUTE, "Completed", fallback=0) and not unlocked:
        raise ValueError("Premature Target completion")
    if plan["options"]["characters"]:
        if (
            license is None
            or license.getint(CHARACTERS, "Schema", fallback=0) != 1
            or license.getint(CHARACTERS, "Characters", fallback=0) != 1
            or not 0 <= license.getint(CHARACTERS, "LastVisit") <= visit
            or not 1 <= license.getint(CHARACTERS, "Step") <= len(ROSTER)
        ):
            raise ValueError("Invalid Target character progress")
