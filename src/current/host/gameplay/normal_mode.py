"""Native Normal-mode character changes and original Solgryn completion."""

from gameplay.native_events import Events
from gameplay.normal_plan import GROUP, RANKS, FRAMES
from gameplay.cycle_plan import STARTERS
from gameplay.characters import ROSTER
from gameplay.rewards import ini_string
from transition.events import commands, integer, string, ini_value, set_ini
from transition.router import frame_metadata, ini_expression, GROUP as ROUTE
from transition.boss_exits import split


def transform(frame, sections, objects, instances):
    if frame == 2:
        e = Events(sections)
        license = e.profile(sections)
        result = [list(rows) for rows in sections]
        result[0][2:2] = [
            e.row(
                [e.start(), e.eq(license, GROUP, "Characters", 1)],
                [set_ini(GROUP, "ResumePending", 1, oi=license)],
            )
        ]
        return result, [dict(frame=2, resume_guard=True)]
    if frame not in FRAMES:
        return sections, []
    ini, _, save = frame_metadata(frame, sections, objects, instances)
    e = Events(sections)
    license = e.profile(sections)

    def get(key):
        return ini_value(GROUP, key, oi=license)

    def put(key, value):
        return set_ini(GROUP, key, value, oi=license)

    def enabled():
        return [
            e.start(),
            e.eq(license, GROUP, "Schema", 1),
            e.eq(license, GROUP, "Characters", 1),
        ]

    def changed():
        return enabled() + [
            e.eq(license, GROUP, "LastFrame", frame, 1),
            e.eq(license, GROUP, "ResumePending", 0),
            e.cmp(get("LastDeaths"), ini_value("Stats", "Deaths", oi=ini)),
        ]

    rows = [e.row(enabled(), [e.load(ini, "SaveFile1.ini")])]
    rows.append(
        e.row(
            changed(),
            [
                put("BestRank", 999),
                put("BestId", 0),
                ini_expression(
                    GROUP,
                    "Previous",
                    ini_value("License", "Character", oi=license),
                    license,
                ),
            ],
        )
    )
    for name, cid in ROSTER.items():
        rank = ini_value(RANKS, f"{frame}_{cid}", 999, oi=ini)
        for wrap in (False, True):
            score = e.add(rank, integer(len(ROSTER))) if wrap else rank
            gates = changed() + [
                e.eq(license, GROUP, "Previous", cid, 1),
                e.cmp(rank, get("Step"), 3 if wrap else 4),
                e.cmp(score, get("BestRank"), 3),
            ]
            if name not in STARTERS:
                gates.append(e.eq(license, "Unlockables", name, 1))
            rows.append(
                e.row(
                    gates,
                    [
                        ini_expression(GROUP, "BestRank", score, license),
                        put("BestId", cid),
                        e.text(license, GROUP, "BestName", string(name)),
                    ],
                )
            )
    rows.append(
        e.row(
            changed() + [e.eq(license, GROUP, "BestId", 0, 5)],
            [
                ini_expression("License", "Character", get("BestId"), license),
                e.text(
                    license,
                    "License",
                    "CharacterName",
                    ini_string(GROUP, "BestName", "", license),
                ),
                ini_expression(GROUP, "Step", e.add(get("Step"), integer(1)), license),
            ],
        )
    )
    rows.append(
        e.row(
            enabled() + [e.eq(license, GROUP, "Step", len(ROSTER), 5)], [put("Step", 1)]
        )
    )
    # Always remember deaths after this frame entry, including a cross-frame respawn.
    rows.append(
        e.row(
            enabled(),
            [
                put("LastFrame", frame),
                put("ResumePending", 0),
                ini_expression(
                    GROUP, "LastDeaths", ini_value("Stats", "Deaths", oi=ini), license
                ),
            ],
        )
    )
    result = [list(s) for s in sections]
    result[0][2:2] = rows
    finale = 0
    if frame == 46:
        for si, ss in enumerate(sections):
            for ri, row in enumerate(ss):
                cs = commands(row)
                if any(not c[0] and b"Completed\0" in c[-1] for c in cs):
                    conditions, actions = split(row)
                    conditions = [c for c in conditions if b"FusionRouteV4\0" not in c]
                    conditions += [
                        e.eq(ini, GROUP, "Enabled", 1),
                        e.eq(ini, ROUTE, "Handled", 0),
                    ]
                    normal = e.row(conditions, actions)
                    result[si].insert(ri, normal)
                    finale += 1
        assert finale == 1
    return result, [
        dict(
            frame=frame, normal_cycle=True, candidates=len(ROSTER), finale=bool(finale)
        )
    ]
