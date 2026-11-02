"""Fusion title-frame objects and input events for the Randomizer menu.

Only the title frame is extended. Gameplay and its original entry path remain
unchanged. The menu is active on the native save-selection page, only when a
versioned view file enables it. Input is committed with a sequence number last.
"""

import copy
import struct
from transition.events import (
    action,
    commands,
    event,
    expression,
    integer,
    string,
    parameter,
    ini_value,
    compare_ini,
)
from transition.router import ini_expression
from transition.boss_exits import split

PANEL, INPUT, VIEW, CAST_LEFT, CAST_RIGHT, CAST_CENTRE = (
    4000,
    4001,
    4002,
    4003,
    4004,
    4005,
)
CAST = (CAST_LEFT, CAST_RIGHT, CAST_CENTRE)
ANIMATION_FRAMES = 8
GROUP = "Menu"
TEMPLATE = struct.pack("<hBB", -14, 0, 0) + bytes(10)
KEYS = (8, 9, 13, 32, 107, 109, 187, 189, 27, 33, 34, 37, 38, 39, 40, 46, 116, 117, 118)


def condition(kind, code, oi, ps, ident, flags=0x20):
    body = b"".join(ps)
    return (
        struct.pack(
            "<HhhHHHBBH", 16 + len(body), kind, code, oi, 0, flags, len(ps), 0, ident
        )
        + body
    )


def alt(oi, index):
    return struct.pack("<hhHHHH", 2, 16, 12, oi, 0, index)


def value(oi, index, tokens):
    return action(
        2, 31, oi, [parameter(50, struct.pack("<IH", index, 0)), expression(tokens)]
    )


def compare_tokens(a, b, op, ident):
    return condition(-1, -3, 0, [expression(a), expression(b, 23, op)], ident)


def active(ident):
    return [
        compare_ini(GROUP, "Schema", 3, 0, ident, oi=VIEW),
        compare_ini(GROUP, "Enabled", 1, 0, ident + 1, oi=VIEW),
        compare_tokens(alt(46, 1), integer(0), 0, ident + 2),
    ]


def load_image(oi, path, hx=0, hy=0, frame=0):
    # Built-in Active: load a file into Stopped, direction 0, frame 0.
    return action(
        2,
        89,
        oi,
        [
            expression(string(path), 45),
            parameter(10, struct.pack("<H", 0) + b"Stopped\0" + bytes(24)),
            parameter(29, struct.pack("<IH", 1, 0)),
            expression(integer(frame)),
            *[expression(integer(n)) for n in (hx, hy, 0, 0, -1)],
        ],
    )


def clone_objects(objects, frame):
    for new, old, name in (
        (PANEL, 41, "Randomizer Panel"),
        (4510, 41, "Randomizer Update Card"),
        (INPUT, 47, "Randomizer Input"),
        (VIEW, 47, "Randomizer View"),
        (CAST_LEFT, 41, "Randomizer Cast Left"),
        (CAST_RIGHT, 41, "Randomizer Cast Right"),
        (CAST_CENTRE, 41, "Randomizer Cast Centre"),
    ):
        assert new not in objects
        obj = copy.deepcopy(objects[old])
        obj["handle"] = new
        obj["name"] = name
        if new in (PANEL, 4510, *CAST):
            obj["values"] = [-1, 0, 0, 0, -1]
            obj["qualifiers"] = []
            if new in CAST:
                obj["animations"] = [
                    dict(
                        slot=0,
                        name="Stopped",
                        directions=[
                            dict(
                                direction=0,
                                minSpeed=20,
                                maxSpeed=20,
                                repeat=0,
                                backTo=0,
                                frames=[96] * ANIMATION_FRAMES,
                            )
                        ],
                    )
                ]
        else:
            data = bytearray(obj["private"]["data"])
            assert data[22:36].startswith(b"SaveFile1.ini\0")
            # Keep native INI++ serialization/encryption, use a private file.
            filename = (
                ("native-input.ini" if new == INPUT else "native-view.ini") + "\0"
            ).encode()
            data[22:282] = filename + bytes(260 - len(filename))
            obj["private"]["data"] = bytes(data)
        objects[new] = obj
        frame["instances"].append(
            dict(
                handle=50000 + new,
                objectInfo=new,
                x=0 if new in (PANEL, 4510) else -200,
                y=0 if new in (PANEL, 4510) else -200,
                layer=0 if new == 4510 else 4,
                parentType=0,
                parentObjectInfo=0,
                tail="00 " * 8,
            )
        )

    # Draw these last on the panel layer: their scale animation can overlap news.
    digits = [i for i in frame["instances"] if i["objectInfo"] in (43, 44, 45)]
    frame["instances"] = [i for i in frame["instances"] if i not in digits]
    for inst in digits:
        inst["layer"] = 4
        inst["tail"] = "00 00 00 00 04 00 00 00"
    frame["instances"].extend(digits)


def file_path(name):
    return expression(
        struct.pack("<hhH", -1, 8, 6) + struct.pack("<hhH", 0, 2, 6) + string(name), 45
    )


def transform(sections):
    result = []
    guarded = 0
    ident = 0xE000
    for sec in sections:
        rows = []
        for row in sec:
            cs, acts = split(row)
            if any(c and k in (-6, -7) for c, k, code, oi, raw in commands(row)):
                # Own controls are active only on the save page. Preserve the
                # original intro, options and outer-menu navigation.
                # Simpler guard: Panel value B is 1 while the custom UI is active.
                cs.append(compare_tokens(alt(PANEL, 1), integer(0), 0, ident))
                ident += 1
                guarded += 1
                row = event(row, cs, acts)
            rows.append(row)
        result.append(rows)
    extra = []

    def row(cs, acts):
        extra.append(event(TEMPLATE, cs, acts))

    start = condition(-3, -1, 0, [], ident, flags=0)
    ident += 1
    row(
        [start],
        [
            action(33, 129, INPUT, [expression(integer(0)), expression(integer(0))]),
            action(
                33, 123, INPUT, [file_path("native-input.ini"), expression(integer(0))]
            ),
            *[action(2, 26, oi, []) for oi in (PANEL, *CAST)],
        ],
    )
    # Read-only reload never alters gameplay saves or the menu music channel.
    row(
        [condition(-1, -1, 0, [], ident)],
        [
            action(
                33, 123, VIEW, [file_path("native-view.ini"), expression(integer(1))]
            ),
            value(PANEL, 1, integer(0)),
            action(2, 26, PANEL, []),
            action(2, 26, CAST_CENTRE, []),
            value(PANEL, 2, ini_value(GROUP, "Schema", 0, oi=VIEW)),
            value(PANEL, 3, ini_value(GROUP, "Generation", 0, oi=VIEW)),
        ],
    )
    ident += 1
    row(
        active(ident),
        [
            value(PANEL, 1, integer(1)),
            action(2, 27, PANEL, []),
            *[action(2, 26, oi, []) for oi in (41, 43, 44, 45, 46)],
            *[action(32, 26, oi, []) for oi in (25, 26, 27, 40, 48, 51, 59, 60)],
            *[action(3, 26, oi, []) for oi in (85, 90, 92)],
            *[action(2, 27, oi, []) for oi in (CAST_LEFT, CAST_RIGHT)],
            action(2, 2, CAST_LEFT, [expression(integer(68))]),
            action(2, 3, CAST_LEFT, [expression(integer(170))]),
            action(2, 2, CAST_RIGHT, [expression(integer(572))]),
            action(2, 3, CAST_RIGHT, [expression(integer(170))]),
            action(2, 2, PANEL, [expression(integer(0))]),
            action(2, 3, PANEL, [expression(integer(0))]),
        ],
    )
    ident += 3
    row(
        active(ident) + [compare_ini(GROUP, "CentreVisible", 1, 0, ident + 3, oi=VIEW)],
        [
            action(2, 27, CAST_CENTRE, []),
            action(
                2,
                2,
                CAST_CENTRE,
                [expression(ini_value(GROUP, "CentreX", 294, oi=VIEW))],
            ),
            action(
                2,
                3,
                CAST_CENTRE,
                [expression(ini_value(GROUP, "CentreY", 365, oi=VIEW))],
            ),
        ],
    )
    ident += 4
    # Load the finite animation once per seed; Fusion advances the frames itself.
    row(
        active(ident)
        + [
            compare_tokens(
                alt(PANEL, 4),
                ini_value(GROUP, "ArtGeneration", 0, oi=VIEW),
                1,
                ident + 3,
            )
        ],
        [
            *[
                load_image(oi, f"native-cast-{side}-{frame:02d}.png", 96, 128, frame)
                for oi, side in zip(CAST, ("left", "right", "centre"))
                for frame in range(ANIMATION_FRAMES)
            ],
            value(PANEL, 4, ini_value(GROUP, "ArtGeneration", 0, oi=VIEW)),
        ],
    )
    ident += 4
    # Swap only on a published generation. PNG is written atomically first.
    row(
        active(ident)
        + [
            compare_tokens(
                alt(PANEL, 0), ini_value(GROUP, "Generation", 0, oi=VIEW), 1, ident + 3
            )
        ],
        [
            load_image(PANEL, "native-panel.png"),
            value(PANEL, 0, ini_value(GROUP, "Generation", 0, oi=VIEW)),
        ],
    )
    ident += 4
    row([start], [load_image(41, "native-logo.png", 110, 44)])
    for key in KEYS + (1000,):
        if key == 1000:
            trigger = condition(
                -6, -5, 0, [parameter(32, struct.pack("<IH", 0, 0))], ident
            )
        else:
            trigger = condition(
                -6, -1, 0, [parameter(14, struct.pack("<HH", key, 0))], ident
            )
        ident += 1
        guards = active(ident)
        ident += 3
        guards += [
            compare_ini(GROUP, "Busy", 0, 0, ident, oi=VIEW),
            compare_tokens(
                ini_value(GROUP, "Sequence", 0, oi=INPUT),
                ini_value(GROUP, "Ack", 0, oi=VIEW),
                0,
                ident + 1,
            ),
        ]
        ident += 2
        seq = (
            ini_value(GROUP, "Sequence", 0, oi=INPUT)
            + struct.pack("<hhH", 0, 2, 6)
            + integer(1)
        )
        acts = [ini_expression(GROUP, "Key", integer(key), INPUT)]
        if key == 1000:
            acts += [
                ini_expression(GROUP, name, struct.pack("<hhH", -6, code, 6), INPUT)
                for name, code in [("X", 0), ("Y", 1)]
            ]
        acts += [
            ini_expression(GROUP, "Sequence", seq, INPUT),
            action(33, 124, INPUT, []),
        ]
        row([trigger, *guards], acts)
    result.append(extra)
    return result, dict(
        frame=2,
        guarded_input_rows=guarded,
        added_events=len(extra),
        objects=[PANEL, INPUT, VIEW, *CAST],
    )
