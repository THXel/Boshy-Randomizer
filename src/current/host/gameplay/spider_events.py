"""Native optional surprise attack: straight flight, player-facing artwork.

A separate unqualified object owns motion and transient counters. Only the
schedule/statistics go into the run-local profile. Original enemies, mouse,
physics and event rows are unchanged; contact invokes the original Die loop.
"""

import struct
from functools import lru_cache
from gameplay import spider_plan as plan
from gameplay.spider_object import OBJECT as SPIDER
from gameplay.native_events import Events
from gameplay import profile_batch
from gameplay.native_extras import group, operator, MODULUS
from gameplay.normal_plan import FRAMES
from gameplay import god_mode
from native_menu.events import alt, value, condition
from transition.events import action, commands, expression, integer, ini_value
from transition.router import frame_metadata, count, ini_expression, params

# Native controller values.
ACTIVE, GRACE, CLOCK, X, Y, DX, DY, AGE, SIDE, ALONG, LENGTH, READY = range(12)


def number(value):
    if type(value) is int:
        return integer(value)
    return struct.pack("<hhHdf", -1, 23, 18, value, value)


def calc(a, op, b):
    return group(a) + operator(op) + group(b)


def function(code, *args):
    return (
        struct.pack("<hhH", -1, code, 6)
        + struct.pack("<hhH", -1, -3, 6).join(args)
        + struct.pack("<hhH", -1, -2, 6)
    )


def modulo(tokens, divisor=MODULUS):
    return calc(tokens, 10, integer(divisor))


def xy(oi, axis):
    return struct.pack("<hhHHH", 2, 11 if axis == 0 else 1, 10, oi, 0)


def window(axis):
    return struct.pack("<hhH", -3, 2 if axis == 0 else 4, 6)


@lru_cache(maxsize=1)
def roar():
    """Reuse the original attack sample on channel 8, excluding blood effects."""
    from recover_boshy_classic import routes, sections as original_sections

    payload = next(p for p, n in routes.payloads.items() if n == 3)
    candidates = [
        c[-1]
        for ss in original_sections(payload)
        for row in ss
        for c in commands(row)
        if not c[0]
        and c[1:3] == (-2, 11)
        and b"aaaaaaaaaaaah_newandlouder\0" in c[-1]
        and params(c[-1])[-1][1] == expression(integer(8))
    ]
    assert candidates and len(set(candidates)) == 1
    return candidates[0]


def transform(frame, sections, objects, instances, profile_oi=None):
    if frame not in FRAMES:
        return sections, []
    save, player, _ = frame_metadata(frame, sections, objects, instances)
    license = Events.profile(sections) if profile_oi is None else profile_oi
    windows = {
        i["objectInfo"]
        for i in instances
        if objects[i["objectInfo"]]["name"] == "Window Control"
    }
    assert len(windows) == 1, (frame, windows)
    win = windows.pop()
    e = Events(sections, low=0x1000, high=0xFFFE)

    def a(key):
        return alt(SPIDER, key)

    def v(key, tokens):
        return value(SPIDER, key, tokens)

    def st(key):
        return ini_value(plan.STATE, key, oi=license)

    def write(key, tokens):
        return ini_expression(plan.STATE, key, tokens, license)

    def eq(key, n, comparison=0):
        return e.cmp(a(key), integer(n), comparison)

    def focused(neg=False):
        return condition(44, -85, win, [], e.ident(), 0x120 if neg else 0x20)

    def flag(set_):
        return condition(
            2, -25 if set_ else -24, player, [expression(integer(5))], e.ident()
        )

    def alive():
        return [count(player, 0, 5, e.ident()), flag(False), focused()]

    def enabled():
        return [
            e.eq(save, plan.GROUP, "Schema", 1),
            e.eq(save, plan.GROUP, "Enabled", 1),
            e.eq(license, plan.STATE, "Schema", 1),
        ]

    stop = [
        action(2, 26, SPIDER, []),
        v(ACTIVE, integer(0)),
        v(GRACE, integer(plan.GRACE)),
        v(CLOCK, integer(0)),
    ]
    rows = [
        e.row(
            [e.start()],
            stop
            + [
                v(READY, integer(0)),
                action(
                    2, 85, SPIDER, [expression(number(2 / 3)), expression(integer(1))]
                ),
            ],
        )
    ]
    # Recompute readiness each frame; pause/countdown never runs without focus,
    # during player death or when the player is far outside the visible room.
    rows.append(e.row([e.cmp(integer(1), integer(1))], [v(READY, integer(0))]))
    bounds = [
        e.cmp(function(29, calc(xy(player, axis), 4, window(axis))), integer(8192), 3)
        for axis in (0, 1)
    ]
    rows.append(e.row(enabled() + alive() + bounds, [v(READY, integer(1))]))
    rows.append(e.row([eq(READY, 0), eq(ACTIVE, 1)], stop))
    rows.append(
        e.row(
            [count(player, 0, 0, e.ident())],
            [v(GRACE, integer(plan.GRACE)), v(CLOCK, integer(0))],
        )
    )

    def ready():
        return [eq(READY, 1)]

    rows.append(
        e.row(ready() + [eq(GRACE, 0, 5)], [v(GRACE, calc(a(GRACE), 4, integer(1)))])
    )
    rows.append(
        e.row(
            ready() + [eq(GRACE, 0), eq(ACTIVE, 0)],
            [v(CLOCK, calc(a(CLOCK), 2, integer(1)))],
        )
    )
    rows.append(
        e.row(
            ready()
            + [
                eq(GRACE, 0),
                eq(ACTIVE, 0),
                eq(CLOCK, 50, 4),
                e.cmp(st("Remaining"), integer(0), 5),
            ],
            [
                write("Remaining", calc(st("Remaining"), 4, integer(1))),
                v(CLOCK, integer(0)),
            ],
        )
    )
    rng = modulo(calc(calc(st("Rng"), 6, integer(109)), 2, integer(1021)), MODULUS)
    sounds = [roar()]
    interval = calc(
        integer(plan.MINIMUM),
        2,
        calc(calc(st("Rng"), 6, integer(1501)), 8, integer(MODULUS)),
    )
    rows.append(
        e.row(
            ready()
            + [eq(GRACE, 0), eq(ACTIVE, 0), e.cmp(st("Remaining"), integer(0), 2)],
            [
                profile_batch.begin(license),
                write("Rng", rng),
                write("Remaining", interval),
                write("Rng", rng),
                v(SIDE, modulo(st("Rng"), 4)),
                write("Rng", rng),
                v(ALONG, st("Rng")),
                write("Attacks", calc(st("Attacks"), 2, integer(1))),
                *profile_batch.finish(license),
                v(ACTIVE, integer(1)),
                v(AGE, integer(0)),
                v(CLOCK, integer(0)),
                action(2, 27, SPIDER, []),
                action(2, 57, SPIDER, []),
                sounds[0],
            ],
        )
    )
    for side in range(4):
        x = integer(-112 if side == 0 else 752) if side < 2 else modulo(a(ALONG), 641)
        y = modulo(a(ALONG), 481) if side < 2 else integer(-112 if side == 2 else 592)
        rows.append(
            e.row(
                ready() + [eq(ACTIVE, 1), eq(AGE, 0), eq(SIDE, side)],
                [v(X, calc(window(0), 2, x)), v(Y, calc(window(1), 2, y))],
            )
        )
    rows.append(
        e.row(
            ready() + [eq(ACTIVE, 1), eq(AGE, 0)],
            [
                v(DX, calc(xy(player, 0), 4, a(X))),
                v(DY, calc(xy(player, 1), 4, a(Y))),
                v(
                    LENGTH,
                    function(
                        41,
                        integer(1),
                        function(
                            13, calc(calc(a(DX), 6, a(DX)), 2, calc(a(DY), 6, a(DY)))
                        ),
                    ),
                ),
                v(DX, calc(calc(a(DX), 6, number(plan.SPEED / 50)), 8, a(LENGTH))),
                v(DY, calc(calc(a(DY), 6, number(plan.SPEED / 50)), 8, a(LENGTH))),
            ],
        )
    )
    angle = calc(
        function(59, calc(a(Y), 4, xy(player, 1)), calc(xy(player, 0), 4, a(X))),
        2,
        integer(90),
    )
    rows.append(
        e.row(
            ready() + [eq(ACTIVE, 1)],
            [
                v(X, calc(a(X), 2, a(DX))),
                v(Y, calc(a(Y), 2, a(DY))),
                action(2, 2, SPIDER, [expression(a(X))]),
                action(2, 3, SPIDER, [expression(a(Y))]),
                action(2, 88, SPIDER, [expression(angle), expression(integer(1))]),
                v(AGE, calc(a(AGE), 2, integer(1))),
            ],
        )
    )
    deaths = [
        c[-1]
        for ss in sections
        for row in ss
        if god_mode.manual_death(commands(row))
        for c in commands(row)
        if god_mode.death_call(c)
    ]
    assert len(set(deaths)) == 1, (frame, deaths)
    contact = [
        e.cmp(function(29, calc(xy(player, axis), 4, a(pos))), integer(32), 3)
        for axis, pos in ((0, X), (1, Y))
    ]
    rows.append(
        e.row(
            ready()
            + [
                eq(ACTIVE, 1),
                e.cmp(ini_value(god_mode.GROUP, god_mode.KEY, 1, oi=save), integer(1)),
            ]
            + contact,
            stop + [write("Hits", calc(st("Hits"), 2, integer(1))), deaths[0]],
        )
    )
    rows.append(
        e.row(
            [eq(ACTIVE, 1), eq(AGE, 175, 5)],
            [action(2, 26, SPIDER, []), v(ACTIVE, integer(0))],
        )
    )
    for axis, pos, lower, upper in ((0, X, -180, 820), (1, Y, -180, 660)):
        for bound, comp in ((lower, 3), (upper, 5)):
            rows.append(
                e.row(
                    [
                        eq(ACTIVE, 1),
                        e.cmp(calc(a(pos), 4, window(axis)), integer(bound), comp),
                    ],
                    [action(2, 26, SPIDER, []), v(ACTIVE, integer(0))],
                )
            )
    # Run after all original events so scene-start profile loading is complete.
    return [*sections, rows], [
        dict(frame=frame, object=SPIDER, player=player, profile=license, rows=len(rows))
    ]
