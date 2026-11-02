"""One source-level route edge; ordinary runs keep the original exit.

The only routing input is FusionRandoV2/CheetahRoute in the active game save.
0/missing/unsupported -> original teleporter room. 1/2 -> tested route targets.
The existing victory animation and exit collision remain the trigger.
"""

import hashlib
from .events import commands, compare_ini, event, global_value, set_ini

GROUP = 'FusionRandoV2'
TARGETS = {
    1: {'spot': 'save1.ini', 'frame': 3, 'x': 30, 'y': 40},
    2: {'spot': 'save7.ini', 'frame': 15, 'x': 30, 'y': 1300},
}


def transform(sections, *, group=GROUP, targets=TARGETS):
    original = sections[101][0]
    cmds = commands(original)
    assert [(c, k, n, oi) for c, k, n, oi, _ in cmds] == [
        (True, 2, -14, 574),
        (False, -1, 3, 0),
        (False, -1, 3, 0),
        (False, -1, 3, 0),
        (False, -3, 2, 0),
    ]
    assert (
        cmds[0][4].hex() == '1c000200f2ff3e02000000000100788e0c0001000000800b02000000'
    )
    collision = cmds[0][4]
    original_actions = [c[4] for c in cmds[1:]]
    # Reuse the exact native gate that reveals the exit after the victory animation.
    victory_gate = commands(sections[91][152])[0][4]
    assert (
        victory_gate.hex()
        == '2e000200e5ff690b0000200002001e8e0a003200000000000000140017000400ffff00000a00f41a000000000000'
    )
    # The same "save" fastloop used by the game's checkpoint code.
    save = commands(sections[1][82])[-1][4]
    assert b'save\0' in save
    fallback = event(
        original,
        [collision]
        + [
            compare_ini(group, 'CheetahRoute', route, 1, 0x9200 + route)
            for route in targets
        ],
        original_actions,
    )
    routes = []
    for route, target in targets.items():
        conditions = [
            collision,
            victory_gate,
            compare_ini(group, 'CheetahRoute', route, 0, 0x9210 + route),
        ]
        actions = [
            global_value(1, target['x']),
            global_value(2, target['y']),
            global_value(8, target['frame']),
        ]
        actions += [
            set_ini('Positions', key, target[field])
            for key, field in [('xPos', 'x'), ('yPos', 'y'), ('frame', 'frame')]
        ]
        actions += [set_ini(group, 'CheetahDone', 1), save, original_actions[-1]]
        routes.append(event(original, conditions, actions))
    result = [list(s) for s in sections]
    result[101] = [fallback] + routes + result[101][1:]
    return result, {
        'section': 101,
        'row': 0,
        'original_sha256': hashlib.sha256(original).hexdigest(),
        'added_route_rows': len(routes),
        'targets': targets,
    }
