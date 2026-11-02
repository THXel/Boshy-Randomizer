"""Keyboard access to the native F3 dresser, retaining every original unlock guard.

The original buttons still own character changes and their effects. This adapter
only adds focus, key equivalents and an optional view of unlocked characters.
"""

import copy
import io
import struct
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from gameplay.native_events import Events
from native_menu.events import alt, value, condition
from native_menu.classic_events import load
from transition.events import (
    action,
    commands,
    event,
    expression,
    integer,
    parameter,
    string,
)
from transition.boss_exits import split
from transition.router import params, guarded
from platform_support.fonts import font_path
from menu_host.store import atomic

FOCUS, FILTER, HINT = 4700, 4701, 4702
LOOP = "RandomizerDresserMove"
LABELS = (
    (
        "Nur freigeschaltete",
        "Alle Charaktere",
        "Pfeile: wählen · Enter: auswählen · Tab: Weiter · Esc: zurück · U: Filter",
    ),
    (
        "Unlocked only",
        "All characters",
        "Arrows: focus · Enter: select · Tab: next · Esc: return · U: filter",
    ),
    (
        "Solo desbloqueados",
        "Todos los personajes",
        "Flechas: elegir · Enter: seleccionar · Tab: siguiente · Esc: volver · U: filtro",
    ),
    (
        "Только открытые",
        "Все персонажи",
        "Стрелки: выбор · Enter: выбрать · Tab: далее · Esc: назад · U: фильтр",
    ),
    (
        "解放済みのみ",
        "すべてのキャラ",
        "矢印: 移動 · Enter: 選択 · Tab: 次 · Esc: 戻る · U: フィルター",
    ),
)


def prepare(folder, language):
    from native_menu.preferences import LANGUAGES

    out = Path(folder) / "native-dresser"
    out.mkdir(exist_ok=True)
    captions = LABELS[LANGUAGES.index(language)]
    font = ImageFont.truetype(font_path(language), 11)
    for name, size, text in [
        ("focus", (44, 44), None),
        ("filter-0", (220, 24), captions[0]),
        ("filter-1", (220, 24), captions[1]),
        ("hint", (640, 22), captions[2]),
    ]:
        im = Image.new("RGBA", size)
        d = ImageDraw.Draw(im)
        if text is None:
            d.rounded_rectangle((1, 1, 42, 42), 5, outline="#9aecd5", width=2)
        else:
            d.rounded_rectangle(
                (0, 0, size[0] - 1, size[1] - 1), 4, fill="#16232f", outline="#435767"
            )
            d.text((8, 5), text, font=font, fill="#edf5f6")
        buf = io.BytesIO()
        im.save(buf, format="PNG")
        atomic(out / (name + ".png"), buf.getvalue())


def convert_frame(number, frame, objects):
    if number != 21:
        return frame, objects
    result = copy.deepcopy(frame)
    objs = dict(objects) if isinstance(objects, dict) else dict(enumerate(objects))
    for oi, x, y in ((FOCUS, 58, 250), (FILTER, 210, 451), (HINT, 0, 421)):
        assert oi not in objs
        obj = copy.deepcopy(objs[41])
        obj.update(
            handle=oi,
            name={
                FOCUS: "Dresser keyboard focus",
                FILTER: "Dresser unlocked filter",
                HINT: "Dresser controls",
            }[oi],
            values=[0] * 8,
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
                handle=59000 + oi,
                objectInfo=oi,
                x=x,
                y=y,
                layer=3,
                parentType=0,
                parentObjectInfo=0,
                tail="00 " * 8,
            )
        )
    return result, objs


def catalogue(objects, instances):
    result = []
    for inst in instances:
        oi = inst["objectInfo"]
        obj = objects[oi]
        strings = obj.get("strings") or []
        if (
            obj["name"].startswith("MenuButton")
            and len(strings) >= 2
            and strings[0].isdigit()
            and 0 <= inst["x"] < 640
            and 260 <= inst["y"] < 400
        ):
            result.append(
                dict(
                    oi=oi, x=inst["x"], y=inst["y"], id=int(strings[0]), name=strings[1]
                )
            )
    return sorted(result, key=lambda r: (r["y"], r["x"]))


def neighbours(nodes, index, key):
    """Original staggered rows retain spatial up/down; horizontal wraps all."""
    if key in (9, 37, 39):
        return (index + (-1 if key == 37 else 1)) % len(nodes)
    current = nodes[index]
    ys = sorted({n["y"] for n in nodes})
    y = ys[(ys.index(current["y"]) + (-1 if key == 38 else 1)) % len(ys)]
    return min(
        (i for i, n in enumerate(nodes) if n["y"] == y),
        key=lambda i: abs(nodes[i]["x"] - current["x"]),
    )


def transform(frame, sections, objects, instances):
    if frame != 21:
        return sections, []
    result = [list(rows) for rows in sections]
    e = Events(result, low=0xB000, high=0xCF00)
    nodes = catalogue(objects, instances)
    nodes.append(dict(oi=1409, x=320, y=408, id=None, name="Change"))
    picks = {n["oi"]: [] for n in nodes}
    for rows in sections:
        for row in rows:
            cs, acts = split(row)
            for c in commands(row):
                if c[0] and c[1:3] == (-6, -7):
                    ps = params(c[-1], True)
                    oi = struct.unpack_from("<H", ps[1][1], 6)[0]
                    if oi in picks:
                        picks[oi].append((row, cs, acts))
    assert all(picks[n["oi"]] for n in nodes)
    rows = []

    def add(cs, acts):
        rows.append(e.row(cs, acts))

    def eq(index, n, op=0):
        return e.cmp(alt(FOCUS, index), integer(n), op)

    def key(n):
        return condition(
            -6, -1, 0, [parameter(14, struct.pack("<HH", n, 0))], e.ident()
        )

    def fresh(raw):
        raw = bytearray(raw)
        struct.pack_into("<H", raw, 14, e.ident())
        return bytes(raw)

    def loop():
        return condition(-1, -16, 0, [expression(string(LOOP), 45)], e.ident(), flags=0)

    def runloop():
        return action(
            -1, 14, 0, [expression(string(LOOP), 45), expression(integer(len(nodes)))]
        )

    add(
        [e.start()],
        [
            load(FOCUS, "native-dresser/focus.png", hx=22, hy=22),
            load(FILTER, "native-dresser/filter-0.png"),
            load(HINT, "native-dresser/hint.png"),
            value(FOCUS, 0, integer(0)),
            value(FOCUS, 1, integer(0)),
        ],
    )
    for i, n in enumerate(nodes[:-1]):
        add(
            [e.start(), e.eq(83, "License", "Character", n["id"])],
            [value(FOCUS, 0, integer(i))],
        )
    # The selected-character marker remains original; this second outline only
    # indicates keyboard focus and never writes License or Unlockables.
    for k in (9, 37, 38, 39, 40):
        add(
            [key(k)],
            [value(FOCUS, 2, integer(1)), value(FOCUS, 3, integer(k)), runloop()],
        )
    # A snapshot per loop iteration prevents cascading through several nodes.
    add([loop(), eq(2, 1)], [value(FOCUS, 4, alt(FOCUS, 0))])
    for i, n in enumerate(nodes):
        for k in (9, 37, 38, 39, 40):
            add(
                [loop(), eq(2, 1), eq(4, i), eq(3, k)],
                [value(FOCUS, 0, integer(neighbours(nodes, i, k)))],
            )
    add([loop(), eq(1, 0)], [value(FOCUS, 2, integer(0))])
    for i, n in enumerate(nodes):
        original, cs, acts = picks[n["oi"]][0]
        guards = (
            [fresh(c) for c in cs if struct.unpack_from("<hh", c, 2) != (-6, -7)]
            if n["id"] is not None
            else []
        )
        add([loop(), eq(0, i), *guards], [value(FOCUS, 2, integer(0))])
        # Reuse original unlock checks and actions, including native sounds and
        # preview. The Change button retains all its original OR branches.
        for original, cs, acts in picks[n["oi"]]:
            replaced = []
            for c in cs:
                replaced.append(
                    key(13) if struct.unpack_from("<hh", c, 2) == (-6, -7) else fresh(c)
                )
            rows.append(event(original, guarded(replaced, [eq(0, i)]), acts))
            if n["id"] is None:
                rows.append(
                    event(
                        original,
                        [
                            (
                                key(27)
                                if struct.unpack_from("<hh", c, 2) == (-6, -7)
                                else fresh(c)
                            )
                            for c in cs
                        ],
                        acts,
                    )
                )
        add(
            [eq(0, i)],
            [
                action(2, 2, FOCUS, [expression(integer(n["x"]))]),
                action(2, 3, FOCUS, [expression(integer(n["y"]))]),
            ],
        )
        if n["id"] is None:
            continue
        # Original click events already guard locked characters. Hiding them
        # cannot grant a character, even if the user clicks an old position.
        if guards:
            add([eq(1, 1)], [action(2, 26, n["oi"], [])])
            add([eq(1, 1), *[fresh(c) for c in guards]], [action(2, 27, n["oi"], [])])
        add([eq(1, 0)], [action(2, 27, n["oi"], [])])
    click = condition(
        -6,
        -7,
        0,
        [
            parameter(32, struct.pack("<IH", 0, 0)),
            parameter(1, struct.pack("<HHHH", 0, FILTER, 2, 0)),
        ],
        e.ident(),
        flags=0,
    )
    # One action toggles the filter; zero/one are kept in a private Active value.
    toggle = integer(1) + struct.pack("<hhH", 0, 4, 6) + alt(FOCUS, 1)
    for trigger in (key(85), click):
        add([trigger], [value(FOCUS, 1, toggle)])
    for state in (0, 1):
        add(
            [eq(1, state), eq(5, state, 1)],
            [
                load(FILTER, f"native-dresser/filter-{state}.png"),
                value(FOCUS, 5, integer(state)),
            ],
        )
    result.append(rows)
    return result, [
        dict(
            frame=21,
            keyboard_characters=len(nodes) - 1,
            original_selection_guards=True,
            unlocked_filter=True,
        )
    ]
