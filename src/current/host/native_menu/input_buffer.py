"""Retain one click/key arriving while a hover update awaits acknowledgement.

Hover is advisory. A deliberate action must not disappear merely because the
host is still drawing its help text. The queued coordinates are captured once;
replay uses the same mailbox sequence/retry protocol as ordinary input.
"""

import struct
from gameplay.native_events import Events
from native_menu import events as menu
from transition.events import commands, event, integer, ini_value, string
from transition.boss_exits import split
from transition.router import params, value_parameter

QUEUED, X, Y = 10, 11, 12


def transform(sections):
    result = [list(rows) for rows in sections]
    e = Events(result, low=0xCA00, high=0xCF00)
    extra = []

    def fresh(raw):
        raw = bytearray(raw)
        struct.pack_into("<H", raw, 14, e.ident())
        return bytes(raw)

    def empty():
        return e.cmp(menu.alt(menu.PANEL, QUEUED), integer(0))

    for si, rows in enumerate(sections):
        for ri, row in enumerate(rows):
            cs, acts = split(row)
            assignments = [
                c
                for c in commands(row)
                if not c[0] and c[1:4] == (33, 94, menu.INPUT) and b"Key\0" in c[-1]
            ]
            if not assignments:
                continue
            tokens = value_parameter(params(assignments[0][-1])[-1])
            if tokens[:6] != integer(0)[:6]:
                continue
            key = struct.unpack_from("<i", tokens, 6)[0]
            # A waiting intentional action also stops fresh hover publications.
            if key == 1001:
                result[si][ri] = event(row, [*cs, empty()], acts)
                continue
            trigger = [c for c in cs if struct.unpack_from("<h", c, 2)[0] == -6]
            ready = [c for c in cs if b"Sequence\0" in c and b"Ack\0" in c]
            if len(trigger) != 1 or len(ready) != 1:
                continue
            result[si][ri] = event(row, [*cs, empty()], acts)
            pending = e.cmp(
                ini_value(menu.GROUP, "Sequence", 0, oi=menu.INPUT),
                e.add(ini_value(menu.GROUP, "Ack", 0, oi=menu.VIEW), integer(1)),
            )
            capture = [fresh(c) for c in cs if c not in ready] + [
                pending,
                e.eq(menu.INPUT, menu.GROUP, "Key", 1001),
                empty(),
            ]
            extra.append(
                e.row(
                    capture,
                    [
                        menu.value(menu.PANEL, QUEUED, integer(key)),
                        *[
                            menu.value(
                                menu.PANEL, index, struct.pack("<hhH", -6, axis, 6)
                            )
                            for index, axis in ((X, 0), (Y, 1))
                        ],
                    ],
                )
            )
            dispatch = [fresh(c) for c in cs if c not in trigger] + [
                e.cmp(menu.alt(menu.PANEL, QUEUED), integer(key))
            ]
            replay = []
            for a in acts:
                if key == 1000 and string("X") in a:
                    from transition.router import ini_expression

                    a = ini_expression(
                        menu.GROUP, "X", menu.alt(menu.PANEL, X), menu.INPUT
                    )
                elif key == 1000 and string("Y") in a:
                    from transition.router import ini_expression

                    a = ini_expression(
                        menu.GROUP, "Y", menu.alt(menu.PANEL, Y), menu.INPUT
                    )
                replay.append(a)
            extra.append(
                e.row(dispatch, [*replay, menu.value(menu.PANEL, QUEUED, integer(0))])
            )
    result.append(extra)
    return result
