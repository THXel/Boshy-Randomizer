"""Keep original animated title, Game/Options and the native 1/2/3 selector."""

import struct
from gameplay.native_events import Events
from native_menu import events as menu
from native_menu.classic_art import VARIANTS, layout
from native_menu.session import SESSION
from transition.events import (
    action,
    commands,
    event,
    expression,
    integer,
    string,
    parameter,
    ini_value,
)
from transition.boss_exits import split
from transition.router import guarded, ini_expression


def load(oi, path, animation=0, direction=0, frame=0, hx=0, hy=0):
    return action(
        2,
        89,
        oi,
        [
            expression(string(path), 45),
            parameter(10, struct.pack("<H", animation) + b"Stopped\0" + bytes(24)),
            parameter(29, struct.pack("<IH", 1 << direction, 0)),
            expression(integer(frame)),
            *[expression(integer(n)) for n in (hx, hy, 0, 0, -1)],
        ],
    )


def transform(sections):
    result, audit = menu.transform(sections)
    e = Events(result, low=0xF000, high=0xFE00)
    # Replace blanket keyboard interception with guards only for our modal pages
    # and slot confirmation. The native arrows continue selecting the large digits.
    for si, original in enumerate(sections):
        for ri, row in enumerate(original):
            cs, acts = split(row)
            if any(c and k in (-6, -7) for c, k, code, oi, raw in commands(row)):
                cs = guarded(cs, [e.eq(menu.VIEW, menu.GROUP, "Modal", 0)])
                keys = [
                    struct.unpack_from("<H", raw, 20)[0]
                    for c, k, code, oi, raw in commands(row)
                    if c and k == -6 and code in (-1, -2)
                ]
                if 13 in keys or 46 in keys:
                    cs = guarded(cs, [e.cmp(menu.alt(46, 1), integer(0), 1)])
            if any(b"Online\0" in raw for c, k, code, oi, raw in commands(row) if c):
                cs = guarded(cs, [e.cmp(integer(0), integer(1))])
            if any(
                b"NeverDoneItBefore\0" in raw
                for c, k, code, oi, raw in commands(row)
                if c
            ):
                acts = [a for a in acts if struct.unpack_from("<hh", a, 2) != (37, 82)]
            # The receipt-based preview replaces the old disk screenshot.
            # Hiding the object alone left its PNG load running every frame.
            acts = [a for a in acts if struct.unpack_from('<hhH', a, 2) != (49, 80, 76)]
            result[si][ri] = event(row, cs, acts)
    # Keep the original logo, save digits, cursor and animated intro actors.
    extra = []
    for row in result[-1]:
        cs, acts = split(row)
        fixed = []
        for a in acts:
            kind, code, oi = struct.unpack_from("<hhH", a, 2)
            if code == 26 and (kind, oi) in [(2, n) for n in (41, 43, 44, 45, 46)] + [
                (32, n) for n in (25, 26, 27, 40, 48, 51, 59, 60)
            ]:
                continue
            if kind == 2 and oi in menu.CAST:
                if code == 27:
                    a = action(2, 26, oi, [])
                if code == 89:
                    continue
            if kind == 2 and code == 89 and oi == 41:
                a = load(41, "classic-logo.png", hx=151, hy=60)
            fixed.append(a)
        # Game's Return must only enter the native save page. It must not
        # also open Randomizer settings during the same event loop.
        if any(c and k == -6 for c, k, code, oi, raw in commands(row)):
            cs = guarded(cs, [e.cmp(menu.alt(menu.PANEL, 8), integer(0))])
        extra.append(event(row, cs, fixed))
    result[-1] = extra
    rows = []

    def add(cs, acts):
        rows.append(e.row(cs, acts))

    def outside():
        return [e.cmp(menu.alt(46, 1), integer(0), 1)]

    def slots():
        return [e.cmp(menu.alt(46, 1), integer(0))]

    # News sits after background objects on layer zero. Main controls, terrain,
    # intro actors, digits and logo retain higher layers.
    add([e.start()], [menu.value(4510, 0, integer(-1))])
    add(
        [
            e.cmp(
                menu.alt(4510, 0),
                ini_value(menu.GROUP, "Generation", 0, oi=menu.VIEW),
                1,
            )
        ],
        [
            load(4510, "classic-news.png"),
            menu.value(4510, 0, ini_value(menu.GROUP, "Generation", 0, oi=menu.VIEW)),
        ],
    )
    # Original save thumbnail: Active 6 uses image 2754 (the three question
    # marks) and image 2012 (its frame). Our receipt-based preview replaces it.
    add([], [action(2, 26, oi, []) for oi in (78, 79)] + [action(49, 26, 76, [])])
    # Online is removed as an object and blocked as a destination.
    add([e.start()], [action(2, 24, 70, [])])
    add([e.cmp(menu.alt(46, 1), integer(-1))], [menu.value(46, 3, integer(1))])
    add(
        [e.cmp(menu.alt(46, 1), integer(-1)), e.cmp(menu.alt(46, 0), integer(1), 5)],
        [menu.value(46, 0, integer(0))],
    )
    # The supplementary update card also appears during the original intro.
    add(
        outside(),
        [
            action(2, 27, menu.PANEL, []),
            *[action(3, 26, oi, []) for oi in (85, 90, 92)],
        ],
    )
    add(
        outside() + [e.cmp(menu.alt(menu.PANEL, 8), integer(-1), 1)],
        [
            load(menu.PANEL, "classic-updates.png"),
            menu.value(menu.PANEL, 8, integer(-1)),
        ],
    )
    add(
        slots() + [e.cmp(menu.alt(menu.PANEL, 8), integer(0), 1)],
        [
            load(menu.PANEL, "native-panel.png"),
            menu.value(
                46,
                0,
                e.add(
                    ini_value(menu.GROUP, "SelectedSlot", 1, oi=menu.VIEW), integer(-1)
                ),
            ),
            menu.value(menu.PANEL, 8, integer(0)),
        ],
    )
    # The first Game/Options page also receives mouse hover updates.
    add(
        outside() + [e.cmp(menu.alt(menu.PANEL, 0),
                          ini_value(menu.GROUP, "Generation", 0, oi=menu.VIEW), 1)],
        [load(menu.PANEL, "classic-updates.png"),
         menu.value(menu.PANEL, 0, ini_value(menu.GROUP, "Generation", 0, oi=menu.VIEW))],
    )
    # The initial splash advances this deck once per application restart.
    # Returning from Options or replaying the title choreography reuses it.
    for variant in range(VARIANTS):
        acts = [
            load(
                oi,
                f"classic-intro/{variant}/{i:02d}.png",
                anim,
                direction,
                frame,
                hx,
                hy,
            )
            for i, (oi, anim, direction, frame, hx, hy) in enumerate(layout())
        ]
        acts.extend([load(30, f"classic-intro/theme/{variant}/00.png")])
        # Ground texture variations retain source anchors and alpha masks.
        from intro_themes import TARGETS

        _, raw = __import__("native_menu.classic_art", fromlist=["assets"]).assets()
        for index, (oi, direction, handle) in enumerate(TARGETS):
            if oi != 38:
                continue
            hx, hy = struct.unpack_from("<hh", raw[handle], 20)
            acts.append(
                load(
                    oi,
                    f"classic-intro/theme/{variant}/{index:02d}.png",
                    direction=direction,
                    hx=hx,
                    hy=hy,
                )
            )
        acts.append(action(33, 124, SESSION, []))
        add([e.start(), e.eq(4, "Options", "IntroVariant", variant)], acts)
    add(slots(), [menu.value(46, 3, integer(2))])
    # Keep the original animated digits in front of news, but behind modal pages.
    for modal, visibility in ((0, 27), (1, 26)):
        add(
            slots() + [e.eq(menu.VIEW, menu.GROUP, "Modal", modal)],
            [action(2, visibility, oi, []) for oi in (43, 44, 45)],
        )
    for index, (left, right) in enumerate(((211, 279), (283, 351), (362, 430))):
        mouse_x = struct.pack("<hhH", -6, 0, 6)
        mouse_y = struct.pack("<hhH", -6, 1, 6)
        click = menu.condition(
            -6, -5, 0, [parameter(32, struct.pack("<IH", 0, 0))], e.ident()
        )
        add(
            [
                click,
                *slots(),
                e.eq(menu.VIEW, menu.GROUP, "Modal", 0),
                e.cmp(mouse_x, integer(left), 4),
                e.cmp(mouse_x, integer(right), 3),
                e.cmp(mouse_y, integer(319), 4),
                e.cmp(mouse_y, integer(389), 3),
            ],
            [menu.value(46, 0, integer(index))],
        )
    # Report original slot changes without inventing a replacement selector.
    add(
        slots()
        + [e.cmp(menu.alt(menu.PANEL, 9), e.add(menu.alt(46, 0), integer(1)), 1)],
        [
            ini_expression(
                menu.GROUP, "Slot", e.add(menu.alt(46, 0), integer(1)), menu.INPUT
            ),
            menu.value(menu.PANEL, 9, e.add(menu.alt(46, 0), integer(1))),
            action(33, 124, menu.INPUT, []),
        ],
    )
    result.append(rows)
    return result, dict(
        **audit,
        classic_selector=True,
        online_removed=True,
        independent_intro_variants=VARIANTS,
        extra_events=len(rows),
    )
