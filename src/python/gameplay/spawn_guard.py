"""One target reload after a routed jump; bounded, read-only spawn validation."""

import struct
import time
from contextlib import nullcontext
from transition_timing import observe

# Original Player OIs shared with the verified native sprite reader.
PLAYER_OIS = {
    2: 93,
    3: 307,
    4: 358,
    5: 307,
    6: 574,
    7: 358,
    8: 688,
    9: 574,
    10: 358,
    11: 574,
    12: 905,
    13: 574,
    14: 905,
    16: 574,
    21: 1465,
    22: 358,
    23: 307,
    24: 93,
    25: 307,
    26: 1725,
    27: 574,
    29: 307,
    30: 93,
    31: 574,
    32: 307,
    34: 93,
    35: 307,
    36: 307,
    37: 307,
    43: 574,
    44: 574,
    45: 574,
    49: 307,
    50: 307,
    52: 307,
    53: 574,
    58: 574,
    59: 307,
    38: 307,
    39: 307,
    40: 307,
}
# Other boss arenas have fixed native starts; their INI coordinates are tokens.
POSITION_FRAMES = frozenset(
    (3, 5, 8, 11, 13, 15, 22, 23, 25, 27, 31, 33, 35, 36, 37, 38, 50, 51, 53, 54)
)
X_MARGIN = 96
Y_MARGIN = 160


def player_position(bridge, snap):
    from lab import IniReadInProgress

    oi = PLAYER_OIS.get(snap['scene'])
    if oi is None:
        raise RuntimeError('Unknown Player identity for spawn verification')
    count = snap['objects']
    table = snap['object_list']
    if not 0 < count <= 20000 or table < 0x10000:
        raise IniReadInProgress('Player table not ready')
    raw = b''.join(
        bridge.read(table + off, min(64000, count * 8 - off))
        for off in range(0, count * 8, 64000)
    )
    entries = struct.unpack('<' + 'I' * (count * 2), raw)
    for slot in range(count):
        ptr = entries[slot * 2]
        if ptr < 0x10000:
            continue
        header = bridge.read(ptr, 26)
        if (
            struct.unpack_from('<H', header, 18)[0] != oi
            or struct.unpack_from('<h', header, 24)[0] != 2
        ):
            continue
        data = bridge.read(ptr, 128)
        if data[:26] != header or struct.unpack_from('<H', data, 124)[0] & 1:
            continue
        if struct.unpack('<I', bridge.read(table + slot * 8, 4))[0] != ptr:
            raise IniReadInProgress('Player replaced while checking spawn')
        after = bridge.snapshot()
        if (
            any(after[k] != snap[k] for k in ('scene', 'run', 'object_list'))
            or after['frame_count'] < snap['frame_count']
            or after['next'] != 0
        ):
            raise IniReadInProgress('Scene changed while checking spawn')
        return [
            struct.unpack_from('<i', data, 76)[0],
            struct.unpack_from('<i', data, 84)[0],
        ]
    return None


def position_matches(frame, expected, actual):
    if actual is None:
        return False
    return frame not in POSITION_FRAMES or (
        abs(actual[0] - expected[0]) <= X_MARGIN
        and abs(actual[1] - expected[1]) <= Y_MARGIN
    )


def perform(bridge, frame, x, y, load):
    """Two scene requests total; no key presses, rerolls or automatic retry loop."""
    from lab import IniReadInProgress
    from transition_guard import protect

    check = dict(
        time=time.time(),
        frame=frame,
        expected=[x, y],
        position=None,
        status='loading',
        target_resets=0,
        coordinates_checked=frame in POSITION_FRAMES,
        tolerance=[X_MARGIN, Y_MARGIN],
    )
    bridge.last_spawn_check = check
    try:
        load()
        address = getattr(bridge, 'spawn_guard_address', None)
        observe(bridge, 'spawn-reset')
        with protect(bridge, address) if address is not None else nullcontext():
            load()
        check['target_resets'] = 1
        check['status'] = 'checking'
        end = time.monotonic() + 1.5
        while time.monotonic() < end:
            try:
                snap = bridge.snapshot()
                if (
                    snap['scene'] == frame - 1
                    and snap['next'] == 0
                    and snap['frame_count'] >= 2
                ):
                    check['position'] = player_position(bridge, snap)
                    check['scene_tick'] = snap['frame_count']
                    if position_matches(frame, [x, y], check['position']):
                        check['status'] = 'confirmed'
                        observe(bridge, 'arrived')
                        return snap
            except (IniReadInProgress, KeyError, StopIteration):
                pass
            except RuntimeError as error:
                if not (
                    error.args
                    and isinstance(error.args[0], dict)
                    and error.args[0].get('error')
                    in ('read failed', 'state unavailable')
                ):
                    raise
            time.sleep(0.005)
        raise TimeoutError('Spawn not confirmed after target reset: ' + str(check))
    except Exception:
        check['status'] = 'failed'
        raise


def adjusted_checkpoint(bridge, snap, frame, x, y, position):
    """Allow a native checkpoint's <=8px settling only beside the real player.
    VVVVVV can hit its entrance save at y=143 before the y=140 load is read.
    This does not relax the final wrong-warp check or accept a different screen.
    """
    if frame not in POSITION_FRAMES or snap['scene'] != frame - 1 or snap['next']:
        return False
    try:
        saved = [int(position[k]['value']) for k in ('frame', 'xpos', 'ypos')]
    except (KeyError, ValueError, TypeError):
        return False
    if saved[0] != frame or abs(saved[1] - x) > 8 or abs(saved[2] - y) > 8:
        return False
    actual = player_position(bridge, snap)
    return actual is not None and abs(actual[0] - x) <= 8 and abs(actual[1] - y) <= 8
