"""Foldable native Target checklist, driven by the game's existing receipts.

Artwork is prepared once per language. Mouse input, visibility and collection
state are handled by engine events; no gameplay polling or tracker connection.
"""

import copy
import io
import struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from gameplay.target_plan import ITEMS, BOSS_STAGES, CONFIG
from gameplay.normal_plan import FRAMES
from gameplay.native_events import Events
from gameplay.spider_events import window, calc
from native_menu.events import alt, value, condition, load_image
from transition.events import action, expression, integer, parameter
from transition.router import frame_metadata, GROUP as ROUTE
from platform_support.fonts import font_path
from menu_host.store import atomic
from tracker.localization import catalogue
from beta_catalogue import BOSSES

BUTTON, FIRST = 4800, 4801
BOUNDS = (48, 6, 70, 28)  # Leave room for the original death counter.
ARTWORK_VERSION = "icon-v2"
ROWS_PER_COLUMN = 21
ROWS = [(f"Item{i}", "Collectables", name, name) for i, name in enumerate(ITEMS)] + [
    (f"Boss{sid}", ROUTE, f"Done{sid}", BOSSES[key][0])
    for key, sid in BOSS_STAGES.items()
]
LABEL = dict(de="Ziele", en="Targets", es="Objetivos", ru="Цели", ja="目標")


def prepare(folder, language):
    language = language if language in LABEL else "en"
    root = Path(folder) / "native-targets"
    root.mkdir(exist_ok=True)
    signature = root / "language.txt"
    if (
        signature.exists()
        and signature.read_text() == language + ARTWORK_VERSION
        and len(list(root.glob("*.png"))) == 4 + 2 * len(ROWS)
    ):
        return
    font = ImageFont.truetype(font_path(language), 12)
    strings = catalogue(language)

    def put(name, image):
        data = io.BytesIO()
        image.save(data, format="PNG")
        atomic(root / name, data.getvalue())

    for opened in (0, 1):
        for hover in (0, 1):
            im = Image.new("RGBA", (22, 22))
            d = ImageDraw.Draw(im)
            colour = "#b5ffe8" if hover else "#a6bcb6"
            # Only the glyph has pixels; its outline remains visible on bright rooms.
            strokes = (
                [(5, 5, 17, 17), (17, 5, 5, 17)]
                if opened
                else [
                    (3, 5, 5, 7, 8, 3),
                    (11, 5, 19, 5),
                    (3, 12, 5, 14, 8, 10),
                    (11, 12, 19, 12),
                    (3, 19, 7, 19),
                    (11, 19, 19, 19),
                ]
            )
            for points in strokes:
                d.line(points, fill=(8, 20, 24, 210), width=4)
            for points in strokes:
                d.line(points, fill=colour, width=2)
            put(f"button-{opened}-{hover}.png", im)
    for index, (_, _, _, name) in enumerate(ROWS):
        text = strings.get(name, name)
        for done in (0, 1):
            im = Image.new("RGBA", (230, 20))
            d = ImageDraw.Draw(im)
            d.rectangle((0, 0, 229, 19), fill=(13, 26, 35, 236))
            d.rectangle((6, 4, 18, 16), outline="#9aecd5" if done else "#8196a4")
            if done:
                d.line((8, 10, 11, 13, 17, 6), fill="#9aecd5", width=2)
            size = 12
            while size > 9 and d.textbbox((0, 0), text, font=font)[2] > 202:
                size -= 1
                font = ImageFont.truetype(font_path(language), size)
            d.text((25, 2), text, font=font, fill="#9aecd5" if done else "#f4f7f8")
            put(f"row-{index}-{done}.png", im)
            font = ImageFont.truetype(font_path(language), 12)
    atomic(signature, (language + ARTWORK_VERSION).encode())


def convert_frame(number, frame, objects):
    if number not in FRAMES:
        return frame, objects
    result = copy.deepcopy(frame)
    objs = dict(objects) if isinstance(objects, dict) else dict(enumerate(objects))
    layer = max(i["layer"] for i in frame["instances"])
    for oi in range(BUTTON, FIRST + len(ROWS)):
        assert oi not in objs
        obj = copy.deepcopy(objs[41])
        obj.update(
            handle=oi,
            name="Target Checklist Button"
            if oi == BUTTON
            else f"Target Checklist Row {oi - FIRST}",
            values=[0, 0, 0, -1],
            qualifiers=[],
        )
        props = bytearray(obj["properties"])
        struct.pack_into(
            "<I", props, 16, struct.unpack_from("<I", props, 16)[0] | 0x6000
        )
        obj["properties"] = bytes(props)
        objs[oi] = obj
        result["instances"].append(
            dict(
                handle=60000 + oi - BUTTON,
                objectInfo=oi,
                x=0,
                y=0,
                layer=layer,
                parentType=0,
                parentObjectInfo=0,
                tail="00 " * 8,
            )
        )
    return result, objs


def transform(frame, sections, objects, instances):
    if frame not in FRAMES:
        return sections, []
    ini, _, _ = frame_metadata(frame, sections, objects, instances)
    e = Events(sections, low=0x1000, high=0xFFFE)
    rows = []

    def add(cs, acts):
        rows.append(e.row(cs, acts))

    def eq(oi, index, n, comparison=0):
        return e.cmp(alt(oi, index), integer(n), comparison)

    def enabled():
        return e.eq(ini, CONFIG, "Enabled", 1)

    def pos(oi, x, y):
        return [
            action(2, 2, oi, [expression(calc(window(0), 2, x))]),
            action(2, 3, oi, [expression(calc(window(1), 2, y))]),
        ]

    owned = range(BUTTON, FIRST + len(ROWS))
    add(
        [e.start()],
        [action(2, 26, oi, []) for oi in owned]
        + [
            value(BUTTON, 0, integer(0)),
            value(BUTTON, 1, integer(0)),
            value(BUTTON, 2, integer(0)),
            value(BUTTON, 3, integer(-1)),
        ],
    )
    add(
        [e.start(), e.eq(ini, CONFIG, "Enabled", 1, 1)],
        [action(2, 24, oi, []) for oi in owned],
    )
    mouse_x = calc(struct.pack("<hhH", -6, 0, 6), 4, window(0))
    mouse_y = calc(struct.pack("<hhH", -6, 1, 6), 4, window(1))

    def inside():
        return [
            e.cmp(mouse_x, integer(BOUNDS[0]), 4),
            e.cmp(mouse_x, integer(BOUNDS[2]), 2),
            e.cmp(mouse_y, integer(BOUNDS[1]), 4),
            e.cmp(mouse_y, integer(BOUNDS[3]), 2),
        ]

    add(
        [
            enabled(),
            condition(-6, -5, 0, [parameter(32, struct.pack("<IH", 0, 0))], e.ident()),
            *inside(),
        ],
        [value(BUTTON, 0, calc(integer(1), 4, alt(BUTTON, 0)))],
    )
    add([enabled(), eq(BUTTON, 2, 0), *inside()], [value(BUTTON, 2, integer(1))])
    for axis, bound, comparison in (
        (mouse_x, BOUNDS[0], 2),
        (mouse_x, BOUNDS[2], 4),
        (mouse_y, BOUNDS[1], 2),
        (mouse_y, BOUNDS[3], 4),
    ):
        add(
            [enabled(), eq(BUTTON, 2, 1), e.cmp(axis, integer(bound), comparison)],
            [value(BUTTON, 2, integer(0))],
        )
    for opened in (0, 1):
        for hover in (0, 1):
            variant = opened * 2 + hover
            add(
                [
                    enabled(),
                    eq(BUTTON, 0, opened),
                    eq(BUTTON, 2, hover),
                    eq(BUTTON, 3, variant, 1),
                ],
                [
                    load_image(BUTTON, f"native-targets/button-{opened}-{hover}.png"),
                    value(BUTTON, 3, integer(variant)),
                    action(2, 27, BUTTON, []),
                ],
            )
    add([enabled()], pos(BUTTON, integer(BOUNDS[0]), integer(BOUNDS[1])))
    for i, (key, group, receipt, _) in enumerate(ROWS):
        oi = FIRST + i
        add(
            [e.start()],
            [
                value(oi, 0, integer(-1)),
                value(oi, 1, integer(-1)),
                value(oi, 2, integer(0)),
            ],
        )
        add(
            [e.start(), enabled(), e.eq(ini, CONFIG, key, 1)],
            [
                value(oi, 1, alt(BUTTON, 1)),
                value(BUTTON, 1, calc(alt(BUTTON, 1), 2, integer(1))),
            ],
        )
        for done in (0, 1):
            add(
                [
                    enabled(),
                    eq(BUTTON, 0, 1),
                    eq(oi, 1, 0, 4),
                    e.eq(ini, group, receipt, done),
                    eq(oi, 0, done, 1),
                ],
                [
                    load_image(oi, f"native-targets/row-{i}-{done}.png"),
                    value(oi, 0, integer(done)),
                ],
            )
        add(
            [enabled(), eq(BUTTON, 0, 1), eq(oi, 1, 0, 4), eq(oi, 2, 0)],
            [action(2, 27, oi, []), value(oi, 2, integer(1))],
        )
        add(
            [eq(BUTTON, 0, 0), eq(oi, 2, 1)],
            [action(2, 26, oi, []), value(oi, 2, integer(0))],
        )
        for column in (0, 1):
            index = calc(alt(oi, 1), 4, integer(column * ROWS_PER_COLUMN))
            add(
                [
                    enabled(),
                    eq(BUTTON, 0, 1),
                    eq(oi, 1, column * ROWS_PER_COLUMN, 4),
                    eq(oi, 1, (column + 1) * ROWS_PER_COLUMN, 2),
                ],
                pos(
                    oi,
                    integer(8 + column * 232),
                    calc(integer(36), 2, calc(index, 6, integer(20))),
                ),
            )
    return [*sections, rows], [
        dict(
            frame=frame,
            target_checklist=True,
            rows=len(ROWS),
            native_receipts=True,
            per_frame_file_reads=0,
        )
    ]
