"""Version 3: original Mario pipe and Kracko victory + next-screen crossing."""

import hashlib
import struct
from . import cheetah
from .events import (
    commands,
    compare_ini,
    event,
    global_value,
    set_ini,
    expression,
    integer,
)

GROUP = 'FusionRandoV3'
TARGETS = {**cheetah.TARGETS, 3: {'spot': 'save4.ini', 'frame': 11, 'x': 35, 'y': 140}}


def split(row):
    cmds = commands(row)
    return [c[-1] for c in cmds if c[0]], [c[-1] for c in cmds if not c[0]]


def checked(row, digest):
    assert hashlib.sha256(row).hexdigest() == digest
    return split(row)


def route_actions(target, name, ini, save, jump):
    result = [
        global_value(1, target['x']),
        global_value(2, target['y']),
        global_value(8, target['frame']),
    ]
    result += [
        set_ini('Positions', key, target[field], oi=ini)
        for key, field in [('xPos', 'x'), ('yPos', 'y'), ('frame', 'frame')]
    ]
    return result + [set_ini(GROUP, name + 'Done', 1, oi=ini), save, jump]


def xy(player, axis, comparison, value, identifier):
    params = expression(integer(value), 23, comparison)
    return (
        struct.pack(
            '<HhhHHHBBH',
            16 + len(params),
            2,
            -17 if axis == 'x' else -16,
            player,
            0,
            0x20,
            1,
            0,
            identifier,
        )
        + params
    )


def mario(sections):
    result = [list(s) for s in sections]
    row = sections[25][2]
    cond, acts = checked(
        row, '3d90321452dfff48192e3acbb1fc9254befd5bc3938443d6765ebb29f90c778d'
    )
    save = split(sections[1][82])[1][-1]
    jump = split(sections[0][51])[1][-1]
    assert b'killboss\0' in acts[2] and b'save\0' in save
    fallback = event(
        row,
        cond
        + [
            compare_ini(GROUP, 'MarioRoute', code, 1, 0x9300 + code) for code in TARGETS
        ],
        acts,
    )
    routed = [
        event(
            row,
            cond + [compare_ini(GROUP, 'MarioRoute', code, 0, 0x9310 + code)],
            acts[2:5] + route_actions(target, 'Mario', 312, save, jump),
        )
        for code, target in TARGETS.items()
    ]
    result[25][2:3] = [fallback] + routed
    return result, {
        'boss': 'mario',
        'replaced': [25, 2],
        'original_sha256': hashlib.sha256(row).hexdigest(),
    }


def kracko(sections):
    result = [list(s) for s in sections]
    row = sections[88][35]
    cond, acts = checked(
        row, 'a965628fb2013ba11ce9ad3c77c5de738ec2f6983278a67dbc7c53c6e8367c33'
    )
    result[88][35] = event(
        row, cond, acts + [set_ini(GROUP, 'KrackoVictory', 1, oi=362)]
    )
    # Clear a receipt on every restart, so a previous life cannot unlock a route.
    startcond, _ = split(sections[88][3])
    assert len(startcond) == 1 and commands(sections[88][3])[0][1:3] == (-3, -1)
    reset = event(
        sections[88][3], startcond, [set_ini(GROUP, 'KrackoVictory', 0, oi=362)]
    )
    save = split(sections[1][82])[1][-1]
    jump = split(sections[0][51])[1][-1]
    area = [
        xy(358, 'x', 5, 3840, 0x9401),
        xy(358, 'x', 3, 4480, 0x9402),
        xy(358, 'y', 5, 0, 0x9403),
        xy(358, 'y', 3, 480, 0x9404),
    ]
    # Comparison 5 is >=, 3 is <, matching the engine's original conditions.
    routes = [
        event(
            sections[88][3],
            area
            + [
                compare_ini(GROUP, 'KrackoVictory', 1, 0, 0x9410, oi=362),
                compare_ini(GROUP, 'KrackoRoute', code, 0, 0x9420 + code, oi=362),
            ],
            route_actions(target, 'Kracko', 362, save, jump),
        )
        for code, target in TARGETS.items()
    ]
    result[88] = [reset] + result[88] + routes
    return result, {
        'boss': 'kracko',
        'victory_event': [88, 35],
        'original_sha256': hashlib.sha256(row).hexdigest(),
        'exit_rectangle': [3840, 0, 4480, 480],
        'restart_clears_victory': True,
    }


def cheetah_v3(sections):
    return cheetah.transform(sections, group=GROUP, targets=TARGETS)
