"""Native, exit-driven Target routing and once-only goal/finale transitions.

Existing exit predicates are cloned with Target guards; the proven fixed-route
rows and every original event remain present. Planning runs synchronously in a
native fastloop before the jump, never from host polling or broad screen tests.
"""

import struct
from gameplay.native_events import Events
from gameplay import target_plan as p
from transition.events import (
    commands,
    action,
    expression,
    integer,
    string,
    ini_value,
    set_ini,
    event,
)
from transition.boss_exits import split
from transition.router import (
    STAGES,
    GROUP as ROUTE,
    frame_metadata,
    ini_expression,
    global_expression,
    guarded,
)

LOOP = "Fusion Target next"


def transform(frame, sections, objects, instances):
    local = [s for s in STAGES.values() if frame in s["frames"]]
    if not local and frame != 9:
        return sections, []
    ini, _, save = frame_metadata(frame, sections, objects, instances)
    e = Events(sections)
    get = lambda k: ini_value(p.GROUP, k, oi=ini)
    put = lambda k, v: set_ini(p.GROUP, k, v, oi=ini)
    eq = lambda k, v, op=0: e.eq(ini, p.GROUP, k, v, op)
    enabled = lambda: [
        e.eq(ini, p.CONFIG, "Schema", 1),
        e.eq(ini, p.CONFIG, "Enabled", 1),
    ]
    runloop = action(-1, 14, 0, [expression(string(LOOP), 45), expression(integer(1))])

    def fresh(conditions):
        return [c[:14] + struct.pack("<H", e.ident()) + c[16:] for c in conditions]

    def onloop():
        par = expression(string(LOOP), 45)
        return [
            struct.pack("<HhhHHHBBH", 16 + len(par), -1, -16, 0, 0, 0, 1, 0, e.ident())
            + par
        ] + enabled()

    def goals():
        return [
            e.cmp(
                ini_value("Collectables", n, oi=ini),
                ini_value(p.CONFIG, "Item" + str(i), oi=ini),
                4,
            )
            for i, n in enumerate(p.ITEMS)
        ] + [
            e.cmp(
                ini_value(ROUTE, "Done" + str(sid), oi=ini),
                ini_value(p.CONFIG, "Boss" + str(sid), oi=ini),
                4,
            )
            for sid in p.BOSS_STAGES.values()
        ]

    def jump():
        result = [
            global_expression(i, get(k))
            for i, k in [(1, "NextX"), (2, "NextY"), (8, "NextFrame")]
        ]
        result += [
            ini_expression("Positions", k, get(v), ini)
            for k, v in [("xPos", "NextX"), ("yPos", "NextY"), ("frame", "NextFrame")]
        ]
        result += [
            ini_expression(ROUTE, "CurrentStage", get("NextId"), ini),
            set_ini(ROUTE, "Handled", 1, oi=ini),
            ini_expression(p.GROUP, "Visit", e.add(get("Visit"), integer(1)), ini),
            save,
            action(-3, 2, 0, [expression(struct.pack("<hhHHHH", -1, 24, 12, 0, 0, 8))]),
        ]
        return result

    def destination(stage):
        return [
            put(k, stage[f])
            for k, f in [
                ("NextId", "id"),
                ("NextFrame", "frame"),
                ("NextX", "x"),
                ("NextY", "y"),
            ]
        ]

    # Clone the actual router dispatches, retaining all original pre-jump actions.
    out = []
    count = 0
    final = 0
    for section in sections:
        rows = []
        for row in section:
            cs = commands(row)
            conditions, actions = split(row)
            done = [
                c
                for c in cs
                if not c[0]
                and c[1:3] == (33, 94)
                and b"FusionRouteV4\0" in c[-1]
                and b"Done" in c[-1]
            ]
            if done:
                assert len(done) == 1
                start = next(
                    i
                    for i, a in enumerate(actions)
                    if b"NextX" in a and struct.unpack_from("<hh", a, 2) == (-1, 3)
                )
                clean = [
                    c
                    for c in conditions
                    if not any(k in c for k in (b"NextId", b"NextFrame"))
                ]
                rows.append(
                    e.row(
                        fresh(guarded(clean, enabled())),
                        actions[:start] + [done[0][-1], runloop] + jump(),
                    )
                )
                # Keep the fixed route row byte-for-byte except the mode guard.
                rows.append(
                    event(
                        row,
                        fresh(guarded(conditions, [e.eq(ini, p.CONFIG, "Enabled", 0)])),
                        actions,
                    )
                )
                count += 1
            elif any(not c[0] and b"Completed\0" in c[-1] for c in cs) and any(
                b"CurrentStage\0" in c for c in conditions
            ):
                rows.append(
                    event(
                        row,
                        fresh(guarded(conditions, [e.eq(ini, p.CONFIG, "Enabled", 0)])),
                        actions,
                    )
                )
                rows.append(
                    e.row(
                        fresh(guarded(conditions, enabled() + [eq("Ready", 1)])),
                        actions,
                    )
                )
                final += 1
            else:
                rows.append(row)
        out.append(rows)

    # A single persistent bit per native completion cannot double-count a boss.
    rows = [e.row(onloop(), [put("BestRank", 9999), put("Preferred", 0)])]
    for s in STAGES.values():
        rows.append(
            e.row(
                onloop() + [e.eq(ini, ROUTE, "CurrentStage", s["id"])],
                [put("Preferred", int(s["category"] == "rooms"))],
            )
        )
    for key, stage in p.POOL.items():
        if stage["frame"] == frame and not stage.get("segment"):
            continue
        sid = stage["id"]
        rank = ini_value(p.RANKS, str(sid), 999, oi=ini)
        cursor = "CursorRooms" if stage["category"] == "rooms" else "CursorBosses"
        category = int(stage["category"] == "bosses")
        for same in (False, True):
            for wrap in (False, True):
                penalty = 1000 * int(same) + 100 * int(wrap)
                score = e.add(rank, integer(penalty)) if penalty else rank
                gates = onloop() + [
                    e.eq(ini, ROUTE, "CurrentStage", sid, 1),
                    eq("Preferred", category, 1 if same else 0),
                    e.cmp(rank, get(cursor), 3 if wrap else 4),
                    e.cmp(score, get("BestRank"), 3),
                ]
                if category:
                    gates.append(e.eq(ini, ROUTE, "Done" + str(sid), 0))
                rows.append(
                    e.row(
                        gates,
                        [
                            ini_expression(p.GROUP, "BestRank", score, ini),
                            ini_expression(p.GROUP, "SelectedRank", rank, ini),
                        ]
                        + destination(stage),
                    )
                )
    # Advance only the chosen category's cursor, and only on an actual dispatch.
    for key, stage in p.POOL.items():
        cursor = "CursorRooms" if stage["category"] == "rooms" else "CursorBosses"
        rows.append(
            e.row(
                onloop() + [eq("NextId", stage["id"])],
                [
                    ini_expression(
                        p.GROUP, cursor, e.add(get("SelectedRank"), integer(1)), ini
                    )
                ],
            )
        )
    for cursor in ("CursorRooms", "CursorBosses"):
        rows.append(e.row(onloop() + [eq(cursor, p.SIZE, 5)], [put(cursor, 1)]))
    # Revisit world 3 at legitimate grass once Awesomesauce enables Gastly.
    rows.append(
        e.row(
            onloop()
            + [
                eq("NextId", STAGES["save3.ini"]["id"]),
                e.eq(ini, "Collectables", "Awesomesauce", 1),
                e.eq(ini, "Collectables", "Gastly", 0),
            ],
            [put("NextX", 380), put("NextY", 300)],
        )
    )
    rows.append(e.row(onloop() + goals(), [put("Ready", 1)]))
    rows.append(e.row(onloop() + [eq("Ready", 1)], destination(STAGES[p.FINAL])))

    # Finish immediately after the last item is genuinely awarded. This is not
    # an exit receipt: the interrupted room/boss must never be marked Done.
    rows.append(
        e.row(
            enabled() + [eq("Ready", 0), e.eq(ini, ROUTE, "Handled", 0)] + goals(),
            [runloop] + jump(),
        )
    )
    # The optional Gastly encounter returns after its native catch receipt.
    if frame == 9:
        rows.insert(
            0, e.row([e.start()] + enabled(), [set_ini(ROUTE, "Handled", 0, oi=ini)])
        )
        rows.append(
            e.row(
                enabled()
                + [
                    e.eq(ini, ROUTE, "Handled", 0),
                    e.eq(ini, "Collectables", "Gastly", 1),
                ],
                [runloop] + jump(),
            )
        )
    if frame == 46:
        rows.append(
            e.row([e.start()] + enabled() + [eq("Ready", 0)], [runloop] + jump())
        )
    out[-1] += rows
    return out, [
        dict(
            frame=frame, exit_hooks=count, finale_hooks=final, planner_events=len(rows)
        )
    ]
