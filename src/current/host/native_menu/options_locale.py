from platform_support.fonts import font_path

"""Unicode artwork for original Options labels, preserving native interactions.

Each replacement follows the original text object's layer and world position.
Native selectors, option keys, numeric values and scrolling stay untouched.
"""

import copy
import io
import struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from native_menu import options_labels as labels
from native_menu.classic_events import load
from native_menu.events import value
from gameplay.native_events import Events
from transition.events import action, commands, integer
from menu_host.store import atomic

DIRECTORY = "native-options"
HINT = 1353
STATIC = {1345: "controls_keys", 1342: "room_help"}


def helper(oi):
    return 4200 + oi


def targets():
    return (
        {r[0] for r in labels.ROWS}
        | {r[2] for r in labels.ROWS if r[3] in labels.TOGGLES}
        | {HINT, *STATIC}
    )


def convert_frame(number, frame, objects):
    if number != 20:
        return frame, objects
    result = copy.deepcopy(frame)
    objs = dict(objects) if isinstance(objects, dict) else dict(enumerate(objects))
    for oi in sorted(targets()):
        ident = helper(oi)
        assert ident not in objs
        obj = copy.deepcopy(objs[41])
        obj.update(
            handle=ident,
            name="Translated Options " + str(oi),
            values=[-1] * 4,
            qualifiers=[],
        )
        props = bytearray(obj["properties"])
        struct.pack_into(
            "<I", props, 16, struct.unpack_from("<I", props, 16)[0] | 0x6000
        )
        obj["properties"] = bytes(props)
        objs[ident] = obj
        for inst in frame["instances"]:
            if inst["objectInfo"] == oi:
                result["instances"].append(
                    dict(
                        inst, handle=58000 + len(result["instances"]), objectInfo=ident
                    )
                )
    return result, objs


def _picture(text, size, font, color, *, language, y=0):
    image = Image.new("RGBA", size)
    draw = ImageDraw.Draw(image)
    lines = []
    for paragraph in text.split("\n"):
        words = list(paragraph) if language == "ja" else paragraph.split()
        sep = "" if language == "ja" else " "
        line = ""
        for word in words:
            trial = line + sep + word if line else word
            if line and draw.textlength(trial, font=font) > size[0] - 4:
                lines.append(line)
                line = word
            else:
                line = trial
        lines.append(line)
    line_height = font.size + 2
    if y + len(lines) * line_height > size[1]:
        raise ValueError("Translated Options text exceeds its original region: " + text)
    for i, line in enumerate(lines):
        draw.text((2, y + i * line_height), line, font=font, fill=color)
    return image


def prepare(folder, language):
    folder = Path(folder) / DIRECTORY
    if (folder / "language.txt").is_file() and (
        folder / "language.txt"
    ).read_text() == language:
        return
    folder.mkdir(exist_ok=True)
    selected_font = font_path(language)

    def write(name, text, size=(113, 49), n=11, color="#101010", y=8):
        im = _picture(
            text,
            size,
            ImageFont.truetype(selected_font, n),
            color,
            language=language,
            y=y,
        )
        buffer = io.BytesIO()
        im.save(buffer, format="PNG")
        atomic(folder / (name + ".png"), buffer.getvalue())

    for row in labels.ROWS:
        write("label-" + str(row[0]), labels.label(row, language))
        write(
            "hint-" + str(row[1]),
            labels.hint(row[3], language),
            (248, 140),
            12,
            "white",
            0,
        )
    write(
        "controls_keys",
        labels.hint("controls_keys", language),
        (240, 49),
        10,
        "white",
        0,
    )
    write("room_help", labels.hint("room_help", language), (620, 160), 12, "white", 0)
    for state in ("on", "off"):
        write(state, labels.hint(state, language), (200, 49), 18, "white", 8)
    atomic(folder / "language.txt", language.encode())


def transform(frame, sections):
    if frame != 20:
        return sections, []
    result = [list(rows) for rows in sections]
    e = Events(result, low=0xD900, high=0xE000)
    start = []
    for row in labels.ROWS:
        start.append(load(helper(row[0]), f"{DIRECTORY}/label-{row[0]}.png"))
    for oi, key in STATIC.items():
        start.append(load(helper(oi), f"{DIRECTORY}/{key}.png"))
    start.append(load(helper(HINT), f"{DIRECTORY}/hint-1337.png"))
    rows = [
        e.row([e.start()], start + [action(32, 26, oi, []) for oi in sorted(targets())])
    ]
    from native_menu.presentation_events import VIEW, GROUP
    from transition.events import ini_value
    from native_menu.events import alt

    generation = ini_value(GROUP, "Generation", 0, oi=VIEW)
    rows.append(
        e.row(
            [e.cmp(alt(helper(HINT), 1), generation, 1)],
            start
            + [value(helper(HINT), 0, integer(-1)), value(helper(HINT), 1, generation)],
        )
    )
    selected = {}
    for sec in sections:
        for row in sec:
            for c in commands(row):
                if c[0] and c[1:4] == (2, -4, 1173):
                    target = struct.unpack_from("<H", c[-1], 22)[0]
                    selected.setdefault(target, c[-1])
    for label, selector, display, key, _ in labels.ROWS:
        assert selector in selected, (key, selector)
        condition = bytearray(selected[selector])
        struct.pack_into("<H", condition, 14, e.ident())
        rows.append(
            e.row(
                [
                    bytes(condition),
                    e.cmp(
                        struct.pack("<hhHHHH", 2, 16, 12, helper(HINT), 0, 0),
                        integer(selector),
                        1,
                    ),
                ],
                [
                    load(helper(HINT), f"{DIRECTORY}/hint-{selector}.png"),
                    value(helper(HINT), 0, integer(selector)),
                ],
            )
        )
        if key not in labels.TOGGLES:
            continue
        for enabled, name in ((0, "off"), (1, "on")):
            # Reuse the original computed ON/OFF condition, including its
            # per-setting missing-value default; never guess from the INI.
            matches = [
                c[-1]
                for sec in sections
                for original in sec
                if any(
                    not a[0]
                    and a[1:4] == (32, 80, display)
                    and (name.upper().encode() + b"\0") in a[-1]
                    for a in commands(original)
                )
                for c in commands(original)
                if c[0] and c[1:4] == (32, -27, display)
            ]
            assert len(matches) == 1, (key, name)
            state_condition = bytearray(matches[0])
            struct.pack_into("<H", state_condition, 14, e.ident())
            rows.append(
                e.row(
                    [
                        bytes(state_condition),
                        e.cmp(
                            struct.pack("<hhHHHH", 2, 16, 12, helper(display), 0, 0),
                            integer(enabled),
                            1,
                        ),
                    ],
                    [
                        load(helper(display), f"{DIRECTORY}/{name}.png"),
                        value(helper(display), 0, integer(enabled)),
                    ],
                )
            )
    result.append(rows)
    return result, [
        dict(
            frame=20,
            translated_labels=len(labels.ROWS),
            translated_hints=len(labels.ROWS),
            native_controls_unchanged=True,
        )
    ]
