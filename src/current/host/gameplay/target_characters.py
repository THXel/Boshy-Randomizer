"""Change character on a committed Target visit, including same-frame segments.

Visit only advances at a native exit or the once-only finale unlock. Death,
reload, dresser and menu therefore cannot reroll. Revisits get a fresh choice.
"""

from gameplay.native_events import Events
from gameplay import target_plan as target, normal_plan
from gameplay.characters import ROSTER
from gameplay.cycle_plan import STARTERS
from gameplay.rewards import ini_string
from transition.events import integer, string, ini_value, set_ini
from transition.router import frame_metadata, ini_expression


def transform(frame, sections, objects, instances):
    if frame not in normal_plan.FRAMES:
        return sections, []
    ini, _, _ = frame_metadata(frame, sections, objects, instances)
    e = Events(sections)
    license = e.profile(sections)
    group = target.CHARACTERS
    get = lambda k: ini_value(group, k, oi=license)
    put = lambda k, v: set_ini(group, k, v, oi=license)
    enabled = lambda: [
        e.start(),
        e.eq(license, group, "Schema", 1),
        e.eq(license, group, "Characters", 1),
    ]
    changed = lambda: enabled() + [
        e.cmp(get("LastVisit"), ini_value(target.GROUP, "Visit", oi=ini), 1)
    ]
    rows = [
        e.row(enabled(), [e.load(ini, "SaveFile1.ini")]),
        e.row(
            changed(),
            [
                put("BestRank", 999),
                put("BestId", 0),
                ini_expression(
                    group,
                    "Previous",
                    ini_value("License", "Character", oi=license),
                    license,
                ),
            ],
        ),
    ]
    for name, cid in ROSTER.items():
        rank = ini_value(normal_plan.RANKS, f"{frame}_{cid}", 999, oi=ini)
        for wrap in (False, True):
            score = e.add(rank, integer(len(ROSTER))) if wrap else rank
            gates = changed() + [
                e.eq(license, group, "Previous", cid, 1),
                e.cmp(rank, get("Step"), 3 if wrap else 4),
                e.cmp(score, get("BestRank"), 3),
            ]
            if name not in STARTERS:
                gates.append(e.eq(license, "Unlockables", name, 1))
            rows.append(
                e.row(
                    gates,
                    [
                        ini_expression(group, "BestRank", score, license),
                        put("BestId", cid),
                        e.text(license, group, "BestName", string(name)),
                    ],
                )
            )
    rows.append(
        e.row(
            changed() + [e.eq(license, group, "BestId", 0, 5)],
            [
                ini_expression("License", "Character", get("BestId"), license),
                e.text(
                    license,
                    "License",
                    "CharacterName",
                    ini_string(group, "BestName", "", license),
                ),
                ini_expression(group, "Step", e.add(get("Step"), integer(1)), license),
                ini_expression(
                    group,
                    "LastVisit",
                    ini_value(target.GROUP, "Visit", oi=ini),
                    license,
                ),
            ],
        )
    )
    rows.append(
        e.row(
            enabled() + [e.eq(license, group, "Step", len(ROSTER), 5)], [put("Step", 1)]
        )
    )
    result = [list(s) for s in sections]
    result[0][2:2] = rows
    return result, [dict(frame=frame, visit_cycle=True)]
