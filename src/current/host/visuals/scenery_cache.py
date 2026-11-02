"""Cache scenery only across consecutive starts of the same room.

The marker is application memory, never a saved claim that graphics are loaded.
Every room (including menus) replaces it after its start events. Starting the
application/F2 clears it. Returning through the title before changing runs thus
forces fresh artwork even when both slots resume in the same room.
"""

import struct
from gameplay.native_events import Events
from transition.events import global_value

GLOBAL = 25


def previous_frame():
    return struct.pack("<hhHHHH", -1, 24, 12, 0, 0, GLOBAL)


def finish(frame, sections):
    e = Events(sections, low=0xDE00, high=0xDF00)
    return [*sections, [e.row([e.start()], [global_value(GLOBAL, frame)])]]


def install(app_type):
    original = app_type.globals

    def with_scenery_marker(self):
        values, strings = original(self)
        assert values["count"] == GLOBAL
        return (
            dict(
                values,
                count=GLOBAL + 1,
                values=[*values["values"], 0],
                types=[*values["types"], 0],
            ),
            strings,
        )

    app_type.globals = with_scenery_marker
