"""Native shot appearance and persistent time/death/section triggers.

The two Bullet 2 frame expressions and their character-license guard change. Every
collision, sound, shot limit and motion action is retained. New rows manage
only Ini++ state; shot changes do not depend on a host memory watcher.
"""

import struct
from gameplay import shot_plan as plan
from gameplay.shot_gates import effective_license
from gameplay.native_events import Events
from gameplay.profile_batch import batch
from gameplay.native_extras import operator, group, modulo
from gameplay.normal_plan import FRAMES
from transition.events import (
    commands,
    event,
    expression,
    integer,
    ini_value,
    set_ini,
    parameter,
)
from transition.router import (
    params,
    frame_metadata,
    ini_expression,
    count,
    GROUP as ROUTE,
)


def transform(frame, sections, objects, instances):
    if frame not in FRAMES and frame != 2:
        return sections, []
    e = Events(sections, low=0x1000, high=0xFFFE)
    license = e.profile(sections)
    result = [list(s) for s in sections]

    def state(key):
        return ini_value(plan.STATE, key, oi=license)

    def put(key, value):
        return set_ini(plan.STATE, key, value, oi=license)

    def write(key, tokens):
        return ini_expression(plan.STATE, key, tokens, license)

    if frame == 2:
        result[0][2:2] = [
            e.row(
                [e.start(), e.eq(license, plan.STATE, "Schema", 1)],
                [put("ResumePending", 1)],
            )
        ]
        return result, [dict(frame=frame, shot_resume_guard=True)]

    save, player, _ = frame_metadata(frame, sections, objects, instances)

    def setting(key):
        return ini_value(plan.GROUP, key, oi=save)

    def enabled():
        return [
            e.eq(save, plan.GROUP, "Schema", 1),
            e.eq(save, plan.GROUP, "Enabled", 1),
            e.eq(license, plan.STATE, "Schema", 1),
        ]

    def modes(*values):
        # Separate rows for the two trigger modes; Pending coalesces them.
        return [e.eq(save, plan.GROUP, "Mode", v) for v in values]

    rewrites = []
    for si, rows in enumerate(sections):
        for ri, row in enumerate(rows):
            cs = commands(row)
            shot_row = any(
                not c[0] and c[1:3] == (2, 40) and objects[c[3]]["name"] == "Bullet 2"
                for c in cs
            )
            edited = []
            for cond, kind, code, oi, raw in cs:
                if cond and shot_row:
                    raw = effective_license(raw, save)
                if (
                    not cond
                    and (kind, code) == (2, 40)
                    and objects[oi]["name"] == "Bullet 2"
                ):
                    ps = params(raw)
                    assert len(ps) == 1 and ps[0][0] == 22, (frame, si, ri)
                    old = ps[0][1][6:-4]
                    tokens = (
                        group(old)
                        + operator(6)
                        + group(integer(1) + operator(4) + setting("Enabled"))
                        + operator(2)
                        + state("Frame")
                        + operator(6)
                        + setting("Enabled")
                    )
                    body = expression(tokens)
                    raw = struct.pack("<H", 14 + len(body)) + raw[2:14] + body
                    rewrites.append(dict(section=si, row=ri, object=oi))
                edited.append(raw)
            result[si][ri] = event(row, edited[: row[2]], edited[row[2] :])
    assert len(rewrites) == 2, (frame, rewrites)

    # Early initialization after the profile load, before original gameplay.
    # The native route ID includes split sections that share one game frame.
    early = [e.row([e.start()], [e.load(save, "SaveFile1.ini")])]
    early += [e.row(enabled() + [e.start()], [put("Pending", 0)])]
    for is_route in (True, False):
        spot = (
            ini_value(ROUTE, "CurrentStage", oi=save)
            if is_route
            else integer(1000 + frame)
        )

        def route_guard():
            return e.eq(save, ROUTE, "Schema", 4, 0 if is_route else 1)

        for mode in (2, 4):
            early.append(
                e.row(
                    enabled()
                    + [e.start(), route_guard()]
                    + modes(mode)
                    + [
                        e.eq(license, plan.STATE, "LastSpot", 0, 5),
                        e.eq(license, plan.STATE, "ResumePending", 0),
                        e.cmp(state("LastSpot"), spot, 1),
                        # A respawn in another room is a death, not a section change.
                        e.cmp(state("Observed"), ini_value("Stats", "Deaths", oi=save)),
                    ],
                    [put("Pending", 1)],
                )
            )
        early.append(
            e.row(enabled() + [e.start(), route_guard()], [write("LastSpot", spot)])
        )
    early.append(e.row(enabled() + [e.start()], [put("ResumePending", 0)]))
    result[0][2:2] = early

    late = []
    for mode in (3, 4):
        late.append(
            e.row(
                enabled()
                + modes(mode)
                + [e.cmp(ini_value("Stats", "Deaths", oi=save), state("Observed"), 5)],
                [put("Pending", 1)],
            )
        )
    # MMF's native Every condition pauses with the game. Count only living play.
    tick_param = parameter(2, struct.pack("<II", 1000, 50))
    tick = (
        struct.pack(
            "<HhhHHHBBH", 16 + len(tick_param), -4, -4, 0, 0, 0x20, 1, 0, e.ident()
        )
        + tick_param
    )
    late.append(
        e.row(
            enabled() + modes(1) + [tick, count(player, 0, 5, e.ident())],
            [write("Remaining", state("Remaining") + operator(4) + integer(1))],
        )
    )
    late.append(
        e.row(
            enabled() + modes(1) + [e.eq(license, plan.STATE, "Remaining", 0, 2)],
            [put("Pending", 1)],
        )
    )
    rng = modulo(
        state("Rng") + operator(6) + integer(109) + operator(2) + integer(1021)
    )
    frame_tokens = (
        group(
            state("Frame")
            + operator(2)
            + integer(1)
            + operator(2)
            + group(state("Rng") + operator(10) + integer(35))
        )
        + operator(10)
        + integer(36)
    )
    # Split multiplication to keep every intermediate within signed 32-bit range.
    interval = (
        integer(1)
        + operator(2)
        + state("Rng")
        + operator(6)
        + group(setting("Maximum") + operator(8) + integer(plan.MODULUS))
        + operator(2)
        + group(
            state("Rng")
            + operator(6)
            + group(setting("Maximum") + operator(10) + integer(plan.MODULUS))
        )
        + operator(8)
        + integer(plan.MODULUS)
    )
    late.append(
        e.row(
            enabled() + [e.eq(license, plan.STATE, "Pending", 1)],
            batch(license, [
                write("Rng", rng),
                write("Frame", frame_tokens),
                write("Sequence", state("Sequence") + operator(2) + integer(1)),
                write("Remaining", interval),
                put("Pending", 0),
            ]),
        )
    )
    late.append(
        e.row(
            enabled()
            + [e.cmp(ini_value("Stats", "Deaths", oi=save), state("Observed"), 1)],
            [write("Observed", ini_value("Stats", "Deaths", oi=save))],
        )
    )
    result.append(late)
    return result, [
        dict(
            frame=frame,
            shot_frames=rewrites,
            shot_state_rows=len(early) + len(late),
            save=save,
            license=license,
        )
    ]
