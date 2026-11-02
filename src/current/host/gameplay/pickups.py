"""Shorten the native pickup timeline; optionally omit only item help dialogs.

All award, character-unlock, HUD and input-release actions remain native. The
setting changes the five Player timer thresholds, never boss timers or rewards.
"""

import struct
from transition.events import (
    commands,
    compare_ini,
    event,
    expression,
    integer,
    ini_value,
    parameter,
)
from transition.router import params
from gameplay.god_mode import GROUP

TIMELINE = {200: 0, 250: 1, 315: 2, 330: 3, 360: 4}


def timer(c, objects):
    raw = c[-1]
    if not (
        c[0] and c[1:3] == (2, -27) and objects.get(c[3], {}).get("name") == "Player"
    ):
        return None
    ps = params(raw, True)
    if ps[0][1] != parameter(50, struct.pack("<IH", 24, 0)):
        return None
    for value in TIMELINE:
        if ps[1][1] == expression(
            integer(value), 23, struct.unpack_from("<H", ps[1][1], 4)[0]
        ):
            return value
    return None


def threshold(original, ini):
    # Native arithmetic: old + (new-old) * bool, multiplication before addition.
    return (
        integer(original)
        + struct.pack("<hhH", 0, 2, 6)
        + integer(TIMELINE[original] - original)
        + struct.pack("<hhH", 0, 6, 6)
        + ini_value(GROUP, "FastChests", 0, oi=ini)
    )


def transform(frame, sections, objects):
    # Unused source test frame has no save object and is outside the route catalogue.
    if frame == 58:
        return sections, []
    out, audit = [], []
    used = {
        struct.unpack_from("<H", c[-1], 14)[0]
        for rows in sections
        for row in rows
        for c in commands(row)
        if c[0]
    }
    ini = None

    def save_ini():
        nonlocal ini
        if ini is None:
            found = {
                c[3]
                for rows in sections
                for row in rows
                for c in commands(row)
                if not c[0] and c[1:3] == (33, 94) and b"Positions\0" in c[-1]
            }
            assert len(found) == 1, (frame, found)
            ini = found.pop()
        return ini

    def identifier():
        n = next(n for n in range(0xC800, 0xCB00) if n not in used)
        used.add(n)
        return n

    for si, rows in enumerate(sections):
        result = []
        for ri, row in enumerate(rows):
            cs = commands(row)
            changed = []
            for ci, c in enumerate(cs):
                raw = c[-1]
                value = timer(c, objects)
                if value is not None:
                    # Guard ensures the threshold belongs to the actual pickup animation.
                    assert any(
                        x[0]
                        and x[1:4] == (2, -25, c[3])
                        and params(x[-1], True) == [(22, expression(integer(101)))]
                        for x in cs
                    ), (frame, si, ri)
                    ps = params(raw, True)
                    raw = (
                        raw[:16]
                        + ps[0][1]
                        + expression(
                            threshold(value, save_ini()),
                            23,
                            struct.unpack_from("<H", ps[1][1], 4)[0],
                        )
                    )
                    raw = struct.pack("<H", len(raw)) + raw[2:]
                    audit.append(
                        dict(
                            rule="fast_chests",
                            frame=frame,
                            section=si,
                            source_row=ri,
                            output_row=len(result),
                            command=ci,
                            old=value,
                            new=TIMELINE[value],
                            ini=ini,
                        )
                    )
                changed.append(raw)
            conditions = changed[: row[2]]
            actions = changed[row[2] :]
            popups = [i for i, c in enumerate(cs[row[2] :]) if c[1:3] == (37, 82)]
            reward = any(
                not c[0] and c[1:3] == (33, 94) and b"Collectables\0" in c[-1]
                for c in cs
            )
            if popups and reward:
                manual = event(
                    row,
                    conditions
                    + [
                        compare_ini(
                            GROUP, "QuietPickups", 0, 0, identifier(), oi=save_ini()
                        )
                    ],
                    actions,
                )
                quiet = [
                    raw[:14] + struct.pack("<H", identifier()) + raw[16:]
                    for raw in conditions
                ]
                quiet.append(
                    compare_ini(
                        GROUP, "QuietPickups", 1, 0, identifier(), oi=save_ini()
                    )
                )
                automatic = event(
                    row,
                    quiet,
                    [raw for i, raw in enumerate(actions) if i not in popups],
                )
                audit.append(
                    dict(
                        rule="quiet_pickups",
                        frame=frame,
                        section=si,
                        source_row=ri,
                        output_row=len(result),
                        popup_actions=popups,
                        ini=ini,
                    )
                )
                result.extend((manual, automatic))
            else:
                result.append(
                    event(row, conditions, actions)
                    if changed != [c[-1] for c in cs]
                    else row
                )
        out.append(result)
    return out, audit
