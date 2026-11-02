"""Native title-to-save handoff for the unified application prototype.

Preparation/rendering still happens offline. A versioned, sequential request is
consumed once by Fusion; only a valid native save can enter a playable frame.
The engine and window stay alive. This is not the final seed/menu implementation.
"""

import copy
import struct
from gameplay.native_events import Events
from gameplay.normal_plan import FRAMES
from native_menu.events import PANEL, VIEW, GROUP, alt, value
from transition.events import (
    action,
    expression,
    integer,
    string,
    parameter,
    ini_value,
    set_ini,
)
from transition.router import global_expression, ini_expression

SESSION = 4006
STATE = "Session"


def clone_object(objects, frame):
    assert SESSION not in objects
    obj = copy.deepcopy(objects[47])
    obj.update(handle=SESSION, name="Randomizer Session")
    data = bytearray(obj["private"]["data"])
    assert data[22:36].startswith(b"SaveFile1.ini\0")
    filename = b"native-session.ini\0"
    data[22:282] = filename + bytes(260 - len(filename))
    obj["private"]["data"] = bytes(data)
    objects[SESSION] = obj
    frame["instances"].append(
        dict(
            handle=54006,
            objectInfo=SESSION,
            x=-200,
            y=-200,
            layer=4,
            parentType=0,
            parentObjectInfo=0,
            tail="00 " * 8,
        )
    )


def transform(sections):
    e = Events(sections, low=0xD000, high=0xDF00)
    result = [list(s) for s in sections]
    persist = action(33, 124, SESSION, [])
    # On every title entry, including F2, retain the accepted request number.
    # Never replay a request left behind in the view file.
    result[0][2:2] = [
        e.row(
            [e.start()],
            [
                e.load(SESSION, "native-session.ini"),
                set_ini(STATE, "Schema", 1, oi=SESSION),
                set_ini(STATE, "Status", 0, oi=SESSION),
                persist,
            ],
        )
    ]
    request = ini_value(GROUP, "Begin", oi=VIEW)
    accepted = ini_value(STATE, "Accepted", oi=SESSION)
    ready = [
        e.eq(VIEW, GROUP, "Schema", 3),
        e.eq(VIEW, GROUP, "Enabled", 1),
        e.eq(VIEW, GROUP, "SessionSchema", 1),
        e.eq(VIEW, GROUP, "Busy", 0),
        e.cmp(alt(PANEL, 1), integer(1)),
        e.cmp(request, e.add(accepted, integer(1))),
    ]
    rows = [
        e.row(
            ready,
            [
                ini_expression(STATE, "Accepted", request, SESSION),
                set_ini(STATE, "Status", 1, oi=SESSION),
                persist,
                e.load(47, "SaveFile1.ini"),
                value(PANEL, 5, integer(1)),
            ],
        )
    ]
    # The original application uses global string 0 as the save filename and
    # global value 0 for difficulty. Preserve its dynamic frame expression.
    filename = action(
        -1,
        19,
        0,
        [
            parameter(58, struct.pack("<IH", 0, 0)),
            expression(string("SaveFile1.ini"), 45),
        ],
    )
    for frame in [*FRAMES, 47, 49]:
        rows.append(
            e.row(
                [
                    e.cmp(alt(PANEL, 5), integer(1)),
                    e.eq(47, "Check", "SaveVersion", 1),
                    e.eq(47, "Positions", "frame", frame),
                    *(
                        [e.eq(47, "FusionRouteV4", "Completed", 1)]
                        if frame in (47, 49)
                        else []
                    ),
                    e.cmp(ini_value("Stats", "Difficulty", -1, oi=47), integer(0), 4),
                    e.cmp(ini_value("Stats", "Difficulty", -1, oi=47), integer(3), 2),
                ],
                [
                    value(PANEL, 5, integer(0)),
                    filename,
                    global_expression(0, ini_value("Stats", "Difficulty", oi=47)),
                    set_ini(STATE, "Status", 2, oi=SESSION),
                    persist,
                    action(
                        -3, 2, 0, [expression(ini_value("Positions", "frame", oi=47))]
                    ),
                ],
            )
        )
    rows.append(
        e.row(
            [e.cmp(alt(PANEL, 5), integer(1))],
            [
                value(PANEL, 5, integer(0)),
                set_ini(STATE, "Status", 3, oi=SESSION),
                persist,
            ],
        )
    )
    result.append(rows)
    return result, dict(
        schema=1,
        playable_frames=FRAMES,
        added_events=len(rows) + 1,
        external_process_launches=0,
        scope=__doc__,
    )
