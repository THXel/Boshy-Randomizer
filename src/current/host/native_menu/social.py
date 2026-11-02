"""Current author social link, retaining the original native menu click behavior.

Profile verified on https://grynsoft.com/site/ (Art Twitter) on 2026-10-25.
The icon is generated from vector polygons; no font or extra runtime file needed.
"""

import struct
from PIL import Image, ImageDraw
from transition.events import action, commands, event, expression, string

URL = "https://x.com/soulgryn"
IMAGE = 6255


def icon():
    scale = 4
    im = Image.new("RGB", (32 * scale, 32 * scale))
    draw = ImageDraw.Draw(im)
    draw.rounded_rectangle(
        (0, 0, 127, 127), radius=20, fill="#0b0b0b", outline="#7b7b7b", width=4
    )

    # The familiar X mark: a narrow rising stroke and an outlined falling one.
    def polygon(points, fill):
        draw.polygon(
            [(round((4 + x) * scale), round((4 + y) * scale)) for x, y in points],
            fill=fill,
        )

    polygon(
        [
            (18.9, 1.15),
            (22.58, 1.15),
            (14.54, 10.34),
            (24, 22.85),
            (16.59, 22.85),
            (10.79, 15.27),
            (4.16, 22.85),
            (0.48, 22.85),
            (9.08, 13.02),
            (0, 1.15),
            (7.6, 1.15),
            (12.84, 8.08),
        ],
        "white",
    )
    polygon([(17.61, 20.65), (19.65, 20.65), (6.49, 3.24), (4.3, 3.24)], "#0b0b0b")
    return im.resize((32, 32), Image.Resampling.LANCZOS)


def update_bank(images):
    result = dict(images)
    old = result[IMAGE]
    assert struct.unpack_from("<HH", old, 12) == (32, 32)
    assert struct.unpack_from("<hh", old, 20) == (16, 16)
    head = bytearray(old[:32])
    head[17] = 0
    struct.pack_into("<I", head, 0, 0xFFFFFFFF)
    pixels = icon().tobytes("raw", "BGR")
    struct.pack_into("<I", head, 8, len(pixels))
    result[IMAGE] = bytes(head) + pixels
    return result


def image_loader(original):
    def load(app):
        return update_bank(original(app))

    return load


def transform(frame, sections):
    if frame != 2:
        return sections, []
    result = []
    changed = 0
    for rows in sections:
        output = []
        for row in rows:
            cs = commands(row)
            acts = []
            for c in cs:
                if c[0]:
                    continue
                if c[1:4] == (40, 80, 7) and b"https://twitter.com/Soulgryn" in c[-1]:
                    acts.append(action(40, 80, 7, [expression(string(URL), 45)]))
                    changed += 1
                else:
                    acts.append(c[-1])
            output.append(event(row, [c[-1] for c in cs if c[0]], acts))
        result.append(output)
    assert changed == 1, "Expected original author profile link"
    return result, [
        dict(frame=2, profile_url=URL, image=IMAGE, native_click_preserved=True)
    ]
