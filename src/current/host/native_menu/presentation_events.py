"""Original Options rows and a global presentation view, independent of run saves."""

import copy
import re
import struct
from music.packs import PACKS
from gameplay.native_events import Events
from native_menu.events import condition, value, alt, file_path
from native_menu.classic_events import load
from transition.events import action, integer, parameter, string, ini_value, set_ini

INPUT, VIEW = 4506, 4507
GROUP = "Presentation"
INPUT_FILE, VIEW_FILE = "presentation-input.ini", "presentation-view.ini"
LANGUAGE = (4500, 4501, 4502)
PACKAGE = (4503, 4504, 4505)
NAMES = {
    **{
        oi: "Presentation " + name
        for oi, name in zip(
            (*LANGUAGE, *PACKAGE),
            (
                "Language Selector",
                "Language Label",
                "Language Value",
                "Package Selector",
                "Package Label",
                "Package Value",
            ),
        )
    },
    INPUT: "Presentation Input",
    VIEW: "Presentation View",
}


def convert_frame(number, frame, objects):
    result = copy.deepcopy(frame)
    objs = dict(objects) if isinstance(objects, dict) else dict(enumerate(objects))
    ids = [VIEW]
    if number == 20:
        ids += [INPUT, *LANGUAGE, *PACKAGE]
        # Insert language first and package below both original volume controls.
        # Keep original row pitch, native arrows, scrolling and the bottom stop.
        from native_menu.options_labels import ROWS

        rows = {oi for row in ROWS for oi in row[:3] if oi is not None}
        rows |= {1345, 1342, 1370}
        for inst in result["instances"]:
            if inst["objectInfo"] in rows:
                inst["y"] += 49 if inst["y"] < 226 else 98
    for oi in ids:
        old = (
            47
            if oi in (INPUT, VIEW)
            else 1337 if oi in (LANGUAGE[0], PACKAGE[0]) else 41
        )
        obj = copy.deepcopy(objs[old])
        obj.update(handle=oi, name=NAMES[oi])
        if oi in (INPUT, VIEW):
            data = bytearray(obj["private"]["data"])
            filename = (INPUT_FILE if oi == INPUT else VIEW_FILE).encode() + b"\0"
            data[22:282] = filename + bytes(260 - len(filename))
            obj["private"]["data"] = bytes(data)
        else:
            obj.update(values=[-1] * 4, qualifiers=[])
            # Native option selectors keep their original collision shape.
            if oi in (LANGUAGE[0], PACKAGE[0]):
                obj["strings"] = [
                    "Language" if oi == LANGUAGE[0] else "PresentationPack"
                ]
            else:
                props = bytearray(obj["properties"])
                struct.pack_into(
                    "<I", props, 16, struct.unpack_from("<I", props, 16)[0] | 0x6000
                )
                obj["properties"] = bytes(props)
        objs[oi] = obj
        x, y = -200, -200
        if oi in (*LANGUAGE, *PACKAGE):
            row = LANGUAGE if oi in LANGUAGE else PACKAGE
            x = (266, 273, 394)[row.index(oi)]
            y = 128 if row == LANGUAGE else 275
        result["instances"].append(
            dict(
                handle=59500 + oi - 4500,
                objectInfo=oi,
                x=x,
                y=y,
                layer=1 if number == 20 else 0,
                parentType=0,
                parentObjectInfo=0,
                tail="00 " * 8,
            )
        )
    return result, objs


def transform(number, sections):
    # Redirect only our explicit presentation-group expressions. Gameplay and
    # old immutable SaveFile/plan bindings remain byte-for-byte unchanged.
    result, changed = [], 0
    for rows in sections:
        output = []
        for row in rows:
            for group in ("FusionBloodV1", "FusionMusicV1"):
                pattern = (
                    re.escape(struct.pack("<h", 33))
                    + b"[XY]\\x00\\x0a\\x00(..)\\x00\\x00"
                    + re.escape(string(group))
                )

                def redirect(match):
                    return match[0][:6] + struct.pack("<H", VIEW) + match[0][8:]

                row, count = re.subn(pattern, redirect, row, flags=re.S)
                changed += count
            output.append(row)
        result.append(output)
    e = Events(result, low=0x1000, high=0xFFFE)
    result[0].insert(0, e.row([e.start()], [e.load(VIEW, VIEW_FILE)]))
    if number != 20:
        return result, (
            [dict(frame=number, presentation_expressions=changed)] if changed else []
        )
    rows = [
        e.row(
            [e.start()],
            [
                e.load(INPUT, INPUT_FILE),
                action(33, 125, INPUT, [file_path(INPUT_FILE)]),
            ],
        ),
        e.row([e.cmp(integer(1), integer(1))], [e.load(VIEW, VIEW_FILE)]),
    ]

    # The selector point follows the original interpolated selection cursor.
    def selected(selector):
        return condition(
            2,
            -4,
            1173,
            [parameter(1, struct.pack("<HHHH", 0, selector, 2, 0))],
            e.ident(),
        )

    for ids, field, count in ((LANGUAGE, "Language", 5), (PACKAGE, "Pack", len(PACKS))):
        for key, direction in ((37, -1), (39, 1), (13, 1)):
            trigger = condition(
                -6, -1, 0, [parameter(14, struct.pack("<HH", key, 0))], e.ident()
            )
            rows.append(
                e.row(
                    [trigger, selected(ids[0])],
                    [
                        set_ini(GROUP, "Request", direction, oi=INPUT),
                        set_ini(GROUP, "Field", ids[0], oi=INPUT),
                    ],
                )
            )
        for index in range(count):
            for direction in (-1, 1):
                rows.append(
                    e.row(
                        [
                            e.eq(INPUT, GROUP, "Field", ids[0]),
                            e.eq(INPUT, GROUP, "Request", direction),
                            e.eq(INPUT, GROUP, field, index),
                        ],
                        [
                            set_ini(
                                GROUP, field, (index + direction) % count, oi=INPUT
                            ),
                            set_ini(GROUP, "Request", 0, oi=INPUT),
                            action(33, 124, INPUT, []),
                        ],
                    )
                )
    generation = ini_value(GROUP, "Generation", 0, oi=VIEW)
    rows.append(
        e.row(
            [e.cmp(alt(LANGUAGE[1], 0), generation, 1)],
            [
                *[
                    load(oi, "native-options/" + name + ".png")
                    for oi, name in (
                        (LANGUAGE[1], "language-label"),
                        (LANGUAGE[2], "language-value"),
                        (PACKAGE[1], "package-label"),
                        (PACKAGE[2], "package-value"),
                    )
                ],
                value(LANGUAGE[1], 0, generation),
            ],
        )
    )
    from native_menu.options_locale import helper, HINT

    for ids, name in ((LANGUAGE, "language"), (PACKAGE, "package")):
        rows.append(
            e.row(
                [selected(ids[0]), e.cmp(alt(helper(HINT), 0), integer(ids[0]), 1)],
                [
                    load(helper(HINT), "native-options/" + name + "-hint.png"),
                    value(helper(HINT), 0, integer(ids[0])),
                ],
            )
        )
    result.append(rows)
    return result, [
        dict(frame=number, presentation_expressions=changed, global_options=True)
    ]
