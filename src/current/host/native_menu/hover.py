"""Native mouse motion updates focus only; it never activates a menu row."""

import struct
from gameplay.native_events import Events
from native_menu import events as menu
from transition.events import action, ini_value, integer
from transition.router import ini_expression


def transform(sections):
    result = [list(rows) for rows in sections]
    e = Events(result, low=0xD700, high=0xD800)
    rows = []
    for axis, code in (("X", 0), ("Y", 1)):
        mouse = struct.pack("<hhH", -6, code, 6)
        guards = [
            e.eq(menu.VIEW, menu.GROUP, "Schema", 3),
            e.eq(menu.VIEW, menu.GROUP, "Enabled", 1),
            e.eq(menu.VIEW, menu.GROUP, "Busy", 0),
            e.cmp(
                ini_value(menu.GROUP, "Sequence", 0, oi=menu.INPUT),
                ini_value(menu.GROUP, "Ack", 0, oi=menu.VIEW),
            ),
            e.cmp(mouse, ini_value(menu.GROUP, axis, 0, oi=menu.INPUT), 1),
        ]
        acts = [ini_expression(menu.GROUP, "Key", integer(1001), menu.INPUT)]
        acts += [
            ini_expression(menu.GROUP, name, struct.pack("<hhH", -6, n, 6), menu.INPUT)
            for name, n in (("X", 0), ("Y", 1))
        ]
        acts += [
            ini_expression(
                menu.GROUP,
                "Sequence",
                e.add(ini_value(menu.GROUP, "Sequence", 0, oi=menu.INPUT), integer(1)),
                menu.INPUT,
            ),
            action(33, 124, menu.INPUT, []),
        ]
        rows.append(e.row(guards, acts))
    result.append(rows)
    return result
