"""Settle a fresh randomized Tower arrival on the original elevator surface.

The converted runtime can place the collision body one extra pixel into the
lift after reset. Correct only the first landing, for three ticks. A jump
cancels the correction; later lift travel and the original physics are intact.
The frame-local counter needs no file writes or per-tick INI reads.
"""
import struct
from gameplay.native_events import Events
from gameplay.spider_events import xy, calc
from native_menu.events import alt, value, condition
from transition.events import action, commands, expression, integer, parameter
from transition.router import frame_metadata, GROUP, params

FRAME, LIFT, DOWN, COUNTER = 51, 2822, 97, 25


def transform(frame, sections, objects, instances):
    if frame != FRAME:
        return sections, []
    ini, player, _ = frame_metadata(frame, sections, objects, instances)
    assert objects[LIFT]['name'] == 'Active 26'
    assert objects[DOWN]['name'] == 'Down'
    # Reserve a genuinely unused frame-local value, never a physics counter.
    for rows in sections:
        for row in rows:
            for c in commands(row):
                for kind, p in params(c[-1], c[0]):
                    assert not (c[1] == 2 and c[3] == LIFT and kind == 50
                                and struct.unpack_from('<I', p, 4)[0] == COUNTER)
                    assert alt(LIFT, COUNTER) not in p
    e = Events(sections, low=0xCC00, high=0xCF00)
    y, floor = xy(player, 1), xy(LIFT, 1)
    overlap = lambda: condition(2, -4, DOWN,
        [parameter(1, struct.pack('<HHHH', 0, LIFT, 2, 0))], e.ident())
    armed = lambda: e.cmp(alt(LIFT, COUNTER), integer(0), 4)
    rows = [
        e.row([e.start(), e.eq(ini, GROUP, 'Schema', 4)],
              [value(LIFT, COUNTER, integer(3))]),
        e.row([armed(), e.cmp(alt(player, 2), integer(0), 3)],
              [value(LIFT, COUNTER, integer(0))]),
        e.row([armed(), overlap(),
               e.cmp(y, floor, 5),
               e.cmp(y, Events.add(floor, integer(4)), 2)],
              [action(2, 3, player, [expression(Events.add(floor, integer(1)))]),
               value(player, 2, integer(0)),
               value(LIFT, COUNTER, calc(alt(LIFT, COUNTER), 4, integer(1)))]),
    ]
    return [*sections, rows], [dict(frame=frame, rule='tower_first_landing',
                                   surface_offset=1, maximum_ticks=3,
                                   jump_cancels=True, per_tick_file_reads=0)]
