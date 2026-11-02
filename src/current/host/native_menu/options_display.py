"""Extend the original Options room's Screen size row using native events.

Left/right selects resolution; Enter toggles 4:3 and 16:9 stretch. Reuses the
original selector, label and value objects, including their original scrolling.
World dimensions, camera events, sound and other options are preserved.
"""

import struct
import copy
from gameplay.native_events import Events
from transition.events import (
    action,
    commands,
    event,
    expression,
    integer,
    string,
    parameter,
    ini_value,
    set_ini,
)
from transition.boss_exits import split
from transition.router import ini_expression
from native_menu.events import condition, file_path

OPTIONS = "Options"
INI = 4
HEIGHTS = (480, 720, 1080, 1440, 2160)
WIDTHS = ((640, 960, 1440, 1920, 2880), (854, 1280, 1920, 2560, 3840))


def change(key, value):
    return set_ini(OPTIONS, key, value, oi=INI)


def read(key, default=0):
    return ini_value(OPTIONS, key, default, oi=INI)


def extension(oi, code):
    return struct.pack("<hhHHH", 44, code + 80, 10, oi, 0)


def arithmetic(a, code, b):
    # Parenthesize each operand: available screen width is itself a subtraction.
    # Without grouping Fusion evaluates screenWidth - margin * height / width.
    opening = struct.pack("<hhH", -1, -1, 6)
    closing = struct.pack("<hhH", -1, -2, 6)
    return (
        opening + a + closing + struct.pack("<hhH", 0, code, 6) + opening + b + closing
    )


def call(code, *args):
    return (
        struct.pack("<hhH", -1, code, 6)
        + struct.pack("<hhH", -1, -3, 6).join(args)
        + struct.pack("<hhH", -1, -2, 6)
    )


def size_actions(oi, width, height):
    # Bound the requested size by the current screen, preserving the selected
    # presentation ratio. All scaling stays inside Fusion's renderer.
    available_w = arithmetic(extension(oi, 4), 4, integer(32))
    available_h = arithmetic(extension(oi, 5), 4, integer(88))
    fit_h = call(
        40,
        integer(height),
        call(
            40,
            available_h,
            arithmetic(arithmetic(available_w, 6, integer(height)), 8, integer(width)),
        ),
    )
    fit_w = arithmetic(arithmetic(fit_h, 6, integer(width)), 8, integer(height))
    w = arithmetic(arithmetic(fit_w, 2, extension(oi, 2)), 4, extension(oi, 7))
    h = arithmetic(arithmetic(fit_h, 2, extension(oi, 3)), 4, extension(oi, 8))
    return [action(44, 83, oi, [expression(w)]), action(44, 84, oi, [expression(h)])]


def with_options_instance(frame, instances):
    if frame == 47 and not any(i["objectInfo"] == INI for i in instances):
        return [
            *instances,
            dict(
                handle=59410,
                objectInfo=INI,
                x=-200,
                y=-200,
                layer=0,
                parentType=0,
                parentObjectInfo=0,
                tail="00 " * 8,
            ),
        ]
    return instances


def convert_frame(number, frame, objects):
    instances = with_options_instance(number, frame["instances"])
    if instances is frame["instances"]:
        return frame, objects
    result = copy.deepcopy(frame)
    result["instances"] = instances
    return result, objects


def transform(frame, sections, objects, instances):
    result = [list(rows) for rows in sections]
    windows = {
        i["objectInfo"] for i in instances if objects[i["objectInfo"]]["type"] == 44
    }
    if any(i["objectInfo"] == INI for i in instances):
        # Set both read and write paths explicitly. The recovered extension's
        # implicit filename alone does not establish its save target reliably.
        init = Events(result, low=0x1000, high=0xFFFE)
        result[0].insert(
            0,
            init.row(
                [init.start()],
                [
                    action(
                        33, 123, INI, [file_path("options.ini"), expression(integer(0))]
                    ),
                    action(33, 125, INI, [file_path("options.ini")]),
                ],
            ),
        )
    if any(i["objectInfo"] == INI for i in instances):
        keys = Events(result, low=0xE000, high=0xE100)

        def key(v, held=False):
            return condition(
                -6,
                -2 if held else -1,
                0,
                [parameter(14, struct.pack("<HH", v, 0))],
                keys.ident(),
            )

        result.append(
            [
                keys.row(
                    [key(115)],
                    [
                        keys.load(INI, "options.ini"),
                        ini_expression(
                            OPTIONS,
                            "DisplayFullscreen",
                            arithmetic(integer(1), 4, read("DisplayFullscreen")),
                            INI,
                        ),
                        action(33, 124, INI, []),
                    ],
                ),
                keys.row(
                    [key(68), key(17, True), key(18, True)],
                    [
                        keys.load(INI, "options.ini"),
                        ini_expression(
                            OPTIONS,
                            "DiagnosticRequest",
                            arithmetic(read("DiagnosticRequest"), 2, integer(1)),
                            INI,
                        ),
                        action(33, 124, INI, []),
                    ],
                ),
            ]
        )
    if frame == 1:
        from native_menu.classic_art import VARIANTS

        intro = Events(result, low=0xE100, high=0xE200)
        from transition.router import global_expression

        started = struct.pack("<hhHHHH", -1, 24, 12, 0, 0, 24)
        result.append(
            [
                intro.row(
                    [intro.start(), intro.cmp(started, integer(0))],
                    [
                        global_expression(24, integer(1)),
                        ini_expression(
                            OPTIONS,
                            "IntroVariant",
                            arithmetic(read("IntroVariant", -1), 2, integer(1)),
                            INI,
                        ),
                    ],
                ),
                intro.row(
                    [
                        intro.start(),
                        intro.cmp(read("IntroVariant"), integer(VARIANTS), 4),
                    ],
                    [change("IntroVariant", 0)],
                ),
                intro.row([intro.start()], [action(33, 124, INI, [])]),
            ]
        )
    # The inherited legacy ScreenSize handlers cap at 1280 and hardcode 4:3.
    removed = 0
    for si, rows in enumerate(result):
        for ri, row in enumerate(rows):
            cs = commands(row)
            if b"ScreenSize\0" in row and any(not c[0] and c[1] == 44 for c in cs):
                conds, acts = split(row)
                acts = [a for a in acts if struct.unpack_from("<h", a, 2)[0] != 44]
                rows[ri] = event(row, conds, acts)
                removed += 1
    if frame != 20:
        if windows and any(i["objectInfo"] == INI for i in instances):
            assert len(windows) == 1
            window = next(iter(windows))
            e = Events(result, low=0xB800, high=0xC000)
            rows = []
            for aspect in (0, 1):
                for index, height in enumerate(HEIGHTS):
                    rows.append(
                        e.row(
                            [
                                e.start(),
                                e.cmp(read("DisplayConfigured"), integer(1)),
                                e.cmp(read("DisplayFullscreen"), integer(0)),
                                e.cmp(read("DisplayIndex"), integer(index)),
                                e.cmp(read("DisplayAspect"), integer(aspect)),
                            ],
                            size_actions(window, WIDTHS[aspect][index], height),
                        )
                    )
            result.append(rows)
        return result, (
            [dict(frame=frame, legacy_resize_removed=removed)] if removed else []
        )
    assert objects[1363]["strings"][0] == "ScreenSize"
    assert windows == {1366}
    # Pin exact old room blocks; do not accidentally replace another option.
    assert len(sections[19]) == 6 and len(sections[20]) == 1 and len(sections[21]) == 2
    e = Events(result, low=0xB800, high=0xC000)
    base_selected = next(
        c[-1] for c in commands(sections[19][0]) if c[0] and c[1:4] == (2, -4, 1173)
    )

    def selected():
        b = bytearray(base_selected)
        struct.pack_into("<H", b, 14, e.ident())
        return bytes(b)

    def key(v):
        return condition(
            -6, -1, 0, [parameter(14, struct.pack("<HH", v, 0))], e.ident()
        )

    def eq(k, v):
        return e.cmp(read(k), integer(v))

    rows = []
    # Store a request first, then commit after selection. This prevents a new
    # index matching the next event during the very same keypress/frame.
    for v, request in ((37, 1), (39, 2), (13, 3)):
        rows.append(e.row([key(v), selected()], [change("DisplayRequest", request)]))
    for index, height in enumerate(HEIGHTS):
        for request, direction in ((1, -1), (2, 1)):
            new = (index + direction) % len(HEIGHTS)
            rows.append(
                e.row(
                    [eq("DisplayRequest", request), eq("DisplayIndex", index)],
                    [
                        change("DisplayIndex", new),
                        change("DisplayHeight", HEIGHTS[new]),
                        change("DisplayRequest", 0),
                        change("DisplayDirty", 1),
                    ],
                )
            )
    for aspect in (0, 1):
        rows.append(
            e.row(
                [eq("DisplayRequest", 3), eq("DisplayAspect", aspect)],
                [
                    change("DisplayAspect", 1 - aspect),
                    change("DisplayRequest", 0),
                    change("DisplayDirty", 1),
                ],
            )
        )
    for aspect in (0, 1):
        for index, height in enumerate(HEIGHTS):
            width = WIDTHS[aspect][index]
            label = f"{width}x{height}  " + ("4:3" if aspect == 0 else "16:9")
            match = [eq("DisplayIndex", index), eq("DisplayAspect", aspect)]
            rows.append(
                e.row(match, [action(32, 80, 1365, [expression(string(label), 45)])])
            )
            rows.append(
                e.row(
                    [eq("DisplayDirty", 1), eq("DisplayFullscreen", 0), *match],
                    size_actions(1366, width, height),
                )
            )
            rows.append(
                e.row(
                    [
                        eq("DisplayDirty", 1),
                        eq("DisplayIndex", index),
                        eq("DisplayAspect", aspect),
                    ],
                    [
                        change("ScreenSize", width),
                        change("DisplayConfigured", 1),
                        change("DisplayHeight", height),
                        change("DisplayDirty", 0),
                        action(33, 124, INI, []),
                    ],
                )
            )
    rows.append(
        e.row(
            [selected()],
            [
                action(
                    32,
                    80,
                    1353,
                    [
                        expression(
                            string(
                                "Left/right: resolution. Enter: 4:3 / 16:9 stretched."
                            ),
                            45,
                        )
                    ],
                )
            ],
        )
    )
    result[19] = rows
    result[20] = [
        e.row([e.start()], [action(32, 80, 1364, [expression(string("Display"), 45)])])
    ]
    # Opening Options must not resize a previously selected or manually resized
    # window until the user actually edits this row.
    result[21] = []
    return result, [
        dict(
            frame=frame,
            original_room=True,
            reused_objects=[1363, 1364, 1365, 1366],
            resolutions=WIDTHS,
            aspect_default="4:3",
            events=len(rows),
            legacy_resize_removed=removed,
        )
    ]
