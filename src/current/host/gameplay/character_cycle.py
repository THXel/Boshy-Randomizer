"""Choose a native character once on entry to a new route station.

An early save read precedes the original character sprite readers. Choices and
history are committed through the game's local Ini++ profile. No runtime writes
or host polling are required. Ordinary death, reload and dresser visits retain
LastStage, so they cannot consume a new choice.
"""

import struct
from gameplay.cycle_plan import GROUP, RANKS, STARTERS
from gameplay.characters import ROSTER
from gameplay.rewards import ini_string
from transition.events import (
    commands,
    event,
    action,
    expression,
    integer,
    string,
    ini_value,
    compare_ini,
    set_ini,
)
from transition.router import STAGES, GROUP as ROUTE, ini_expression, frame_metadata


def transform(frame, sections, objects, instances):
    stages = [s for s in STAGES.values() if frame in s["frames"]]
    if not stages:
        return sections, []
    save, _, _ = frame_metadata(frame, sections, objects, instances)
    loads = [
        c
        for row in sections[0][:2]
        for c in commands(row)
        if c[1:3] == (33, 123) and b"onlineLicense.ini\0" in c[-1]
    ]
    assert len(loads) == 1, (frame, "early profile load")
    license = loads[0][3]
    used = {
        struct.unpack_from("<H", c[-1], 14)[0]
        for rows in sections
        for row in rows
        for c in commands(row)
        if c[0]
    }

    def ident():
        n = next(n for n in range(0xD800, 0xF800) if n not in used)
        used.add(n)
        return n

    def start():
        return struct.pack("<HhhHHHBBH", 16, -3, -1, 0, 0, 0x20, 0, 0, ident())

    def eq(group, key, value, oi=license, comparison=0):
        return compare_ini(group, key, value, comparison, ident(), oi=oi)

    def cmp(a, b, comparison=0):
        ps = expression(a) + expression(b, 23, comparison)
        return (
            struct.pack("<HhhHHHBBH", 16 + len(ps), -1, -3, 0, 0, 0x20, 2, 0, ident())
            + ps
        )

    def set_string(group, key, tokens):
        return action(
            33,
            95,
            license,
            [
                expression(string(group), 45),
                expression(string(key), 45),
                expression(tokens, 45),
            ],
        )

    template = struct.pack("<hBB", -14, 0, 0) + bytes(10)

    def ev(conditions, actions):
        return event(template, conditions, actions)

    added = [
        ev(
            [start(), eq(GROUP, "Enabled", 1)],
            [
                action(
                    33,
                    123,
                    save,
                    [
                        expression(
                            struct.pack("<hhH", -1, 8, 6)
                            + struct.pack("<hhH", 0, 2, 6)
                            + string("SaveFile1.ini"),
                            45,
                        ),
                        expression(integer(0)),
                    ],
                )
            ],
        )
    ]

    def gates(sid):
        return [
            start(),
            eq(GROUP, "Schema", 1),
            eq(GROUP, "Enabled", 1),
            eq(ROUTE, "Schema", 4, save),
            eq(ROUTE, "CurrentStage", sid, save),
            eq(GROUP, "LastStage", sid, comparison=1),
        ]

    audit = []
    for stage in stages:
        sid = stage["id"]
        hid = f"HistoryId{sid}"
        hname = f"HistoryName{sid}"
        # Recover an already committed selection rather than rolling twice.
        added.append(
            ev(
                gates(sid) + [eq(GROUP, hid, 0, comparison=5)],
                [
                    ini_expression(
                        "License",
                        "Character",
                        ini_value(GROUP, hid, oi=license),
                        license,
                    ),
                    set_string(
                        "License",
                        "CharacterName",
                        ini_string(GROUP, hname, "", license),
                    ),
                    set_ini(GROUP, "LastStage", sid, oi=license),
                ],
            )
        )

        def unseen():
            return gates(sid) + [eq(GROUP, hid, 0)]

        added.append(
            ev(
                unseen(),
                [
                    set_ini(GROUP, "BestRank", 999, oi=license),
                    set_ini(GROUP, "BestId", 0, oi=license),
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
            rank = ini_value(RANKS, f"{sid}_{cid}", 999, oi=save)
            conditions = unseen() + [
                eq(GROUP, "Previous", cid, comparison=1),
                cmp(rank, ini_value(GROUP, "BestRank", 999, oi=license), 3),
            ]
            if name not in STARTERS:
                conditions.append(eq("Unlockables", name, 1))
            added.append(
                ev(
                    conditions,
                    [
                        ini_expression(GROUP, "BestRank", rank, license),
                        set_ini(GROUP, "BestId", cid, oi=license),
                        set_string(GROUP, "BestName", string(name)),
                    ],
                )
            )
        added.append(
            ev(
                unseen() + [eq(GROUP, "BestId", 0, comparison=5)],
                [
                    ini_expression(
                        GROUP, hid, ini_value(GROUP, "BestId", oi=license), license
                    ),
                    set_string(
                        GROUP, hname, ini_string(GROUP, "BestName", "", license)
                    ),
                    ini_expression(
                        "License",
                        "Character",
                        ini_value(GROUP, "BestId", oi=license),
                        license,
                    ),
                    set_string(
                        "License",
                        "CharacterName",
                        ini_string(GROUP, "BestName", "", license),
                    ),
                    set_ini(GROUP, "LastStage", sid, oi=license),
                ],
            )
        )
        audit.append(
            dict(
                frame=frame,
                stage=sid,
                candidates=len(ROSTER),
                save=save,
                license=license,
            )
        )
    result = [list(rows) for rows in sections]
    result[0][2:2] = added
    return result, audit
