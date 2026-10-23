from pathlib import Path
import os
import json
import subprocess
import select
import time
import struct
import hashlib
import sys
from runtime_paths import BASE, RUNNER, EXPECTED, environment, command
from host_platform import owned_process, LineReader, press


class Bridge:
    def __init__(self):
        assert (
            hashlib.sha256(
                (BASE / 'IWBTB/I Wanna Be The Boshy.exe').read_bytes()
            ).hexdigest()
            == EXPECTED
        )
        self.p = subprocess.Popen(
            command('bridge.exe'),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=open(BASE / 'evidence/bridge.log', 'a'),
            text=True,
            bufsize=1,
            env=environment(),
            **__import__('host_platform').child_options(),
        )
        self.lines = LineReader(self.p.stdout)
        self.ready = self.response()

    def response(self):
        line = self.lines.readline()
        if not line:
            raise RuntimeError('Bridge exited')
        data = json.loads(line)
        if 'error' in data:
            raise RuntimeError(data)
        return data

    def cmd(self, s):
        self.p.stdin.write(s + '\n')
        self.p.stdin.flush()
        return self.response()

    def read(self, addr, size):
        return bytes.fromhex(self.cmd(f'read {addr:x} {size}')['hex'])

    def snapshot(self):
        return self.cmd('snapshot')

    def scene(self, dest):
        before = self.snapshot()
        self.cmd(f'scene {dest} {before["scene"]}')
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            time.sleep(0.04)
            try:
                cur = self.snapshot()
            except RuntimeError:
                continue
            if cur['scene'] == dest and cur['next'] == 0:
                return cur
        raise TimeoutError(f'Scene {dest} not confirmed: {cur}')

    def close(self):
        process = self.p
        if process is None:
            return
        self.p = None
        try:
            if process.poll() is None:
                try:
                    process.stdin.write('quit\n')
                    process.stdin.flush()
                except (BrokenPipeError, OSError, ValueError):
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.terminate()
                    try:
                        process.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=2)
        finally:
            for stream in (process.stdin, process.stdout):
                if stream:
                    try:
                        stream.close()
                    except (OSError, ValueError):
                        pass


def game_window():
    import psutil
    from PY import platform_windows as gw

    candidates = []
    for w in gw.getWindowsWithTitle('I Wanna Be The Boshy'):
        try:
            p = psutil.Process(w.pid)
            if owned_process(p, BASE):
                candidates.append(w)
        except (psutil.Error, AttributeError):
            pass
    if len(candidates) != 1:
        raise RuntimeError(f'Expected one laboratory window: {len(candidates)}')
    return candidates[0]


def key(name, hold=0.12):
    from game_focus import activate_game

    if not activate_game():
        raise RuntimeError('Game focus unavailable')
    press(name, hold)


def screenshot(name):
    from PIL import ImageGrab
    from PY import platform_windows as gw

    w = game_window()
    active = next((v for v in gw.getAllWindows() if v.isActive), None)
    if active is None or active.pid != w.pid:
        w.activate()
    time.sleep(0.3)
    x, y, width, height = gw.window_rect(w)
    ImageGrab.grab(bbox=(x, y, x + width, y + height)).save(BASE / 'evidence' / name)


def objects(b, *, strict=False):
    s = b.snapshot()
    n = s['objects']
    if not 0 < n <= 20000:
        raise RuntimeError('Unexpected object capacity')
    table = bytearray()
    for off in range(0, n * 8, 64000):
        table.extend(b.read(s['object_list'] + off, min(64000, n * 8 - off)))
    arr = struct.unpack('<' + 'I' * (n * 2), table)
    result = []
    for i in range(n):
        p = arr[i * 2]
        if p < 0x10000:
            continue
        try:
            raw = b.read(p, 160)
            result.append(
                {
                    'slot': i,
                    'ptr': p,
                    'handle': struct.unpack_from('<h', raw, 0)[0],
                    'type': struct.unpack_from('<h', raw, 24)[0],
                    'oi': struct.unpack_from('<H', raw, 18)[0],
                    'x': struct.unpack_from('<i', raw, 76)[0],
                    'y': struct.unpack_from('<i', raw, 84)[0],
                    'w': struct.unpack_from('<i', raw, 96)[0],
                    'h': struct.unpack_from('<i', raw, 100)[0],
                    'raw': raw.hex(),
                }
            )
        except RuntimeError:
            if strict:
                raise
    return result


if __name__ == '__main__':
    b = Bridge()
    print(b.ready)
    print(b.snapshot())
    screenshot('initial.png')
    b.close()


class IniReadInProgress(RuntimeError):
    """The game rebuilt an INI tree during a non-atomic memory observation."""


def _ini_observation(fn):
    def read(b, *args, **kwargs):
        before = b.snapshot()
        try:
            result = fn(b, *args, **kwargs)
            confirmed = fn(b, *args, **kwargs)
            if result != confirmed:
                raise IniReadInProgress('INI contents changed during observation')
            after = b.snapshot()
            if (after['scene'], after['run'], after['object_list']) != (
                before['scene'],
                before['run'],
                before['object_list'],
            ) or after['frame_count'] < before['frame_count']:
                raise IniReadInProgress('INI read interrupted by scene reset')
            return result
        except KeyError:
            # A genuinely absent optional group does not invalidate object pointers.
            # Still reject a reset while finding it; all later uses validate identity.
            after = b.snapshot()
            if (after['scene'], after['run'], after['object_list']) != (
                before['scene'],
                before['run'],
                before['object_list'],
            ) or after['frame_count'] < before['frame_count']:
                b._ini_cache = None
                raise IniReadInProgress('INI read interrupted by scene reset')
            raise
        except (IniReadInProgress, StopIteration, RuntimeError):
            b._ini_cache = None
            raise

    return read


def ini_integer_fields(values, fields, *, required=False):
    """Reject partial save updates before a value reaches routing or counters."""
    result = {}
    for name in fields:
        if name not in values:
            if required:
                raise IniReadInProgress('INI numeric field not ready: ' + name)
            continue
        value = values[name]
        if (
            not isinstance(value, str)
            or not value
            or len(value) > 12
            or not value.isascii()
            or not value.lstrip('+-').isdigit()
        ):
            raise IniReadInProgress(
                'INI numeric field changed during observation: ' + name
            )
        try:
            result[name] = int(value)
        except ValueError as error:
            raise IniReadInProgress(
                'INI numeric field changed during observation: ' + name
            ) from error
    return result


def _ini_string(b, raw, off, limit):
    ptr, length, cap = struct.unpack_from('<III', raw, off)
    if length >= limit or length > cap or (length and ptr < 0x10000):
        raise IniReadInProgress('INI string changed during observation')
    return b.read(ptr, length).decode('latin1') if length else ''


def _ini_nodes(b, head, limit):
    if head < 0x10000:
        raise IniReadInProgress('INI tree not ready')
    root = struct.unpack('<I', b.read(head + 4, 4))[0]
    pending = [root]
    seen = {head}
    while pending:
        p = pending.pop()
        if p in seen:
            continue
        if p < 0x10000 or len(seen) > limit:
            raise IniReadInProgress('INI tree changed during observation')
        seen.add(p)
        raw = b.read(p, 64)
        left, parent, right = struct.unpack_from('<III', raw)
        if left == parent == right == 0:
            continue
        yield p, raw
        pending.extend((right, left))


@_ini_observation
def ini_groups(b, oi=109):
    known = ini_objects(b)
    obj = next((o for o in known.values() if o['oi'] == oi), None)
    if obj is None:
        obj = next(o for o in objects(b) if o['oi'] == oi)
    state = struct.unpack('<I', b.read(obj['ptr'] + 0x168, 4))[0]
    if state < 0x10000:
        raise IniReadInProgress('INI state not ready')
    head = struct.unpack('<I', b.read(state + 0x14, 4))[0]
    result = {}
    for p, raw in _ini_nodes(b, head, 512):
        key = _ini_string(b, raw, 16, 200)
        result[key] = {'node': p, 'raw': raw.hex()}
    return result


def _ini_group(b, oi, name):
    # Binary lookup of one group. ini_items still reads and compares the complete
    # result twice, with scene/reset checks around both observations.
    known = ini_objects(b)
    obj = next((o for o in known.values() if o['oi'] == oi), None)
    if obj is None:
        obj = next(o for o in objects(b) if o['oi'] == oi)
    state = struct.unpack('<I', b.read(obj['ptr'] + 0x168, 4))[0]
    if state < 0x10000:
        raise IniReadInProgress('INI state not ready')
    head = struct.unpack('<I', b.read(state + 0x14, 4))[0]
    if head < 0x10000:
        raise IniReadInProgress('INI tree not ready')
    node = struct.unpack('<I', b.read(head + 4, 4))[0]
    seen = set()
    while node != head:
        if node < 0x10000 or node in seen or len(seen) >= 128:
            raise IniReadInProgress('INI tree changed during observation')
        seen.add(node)
        raw = b.read(node, 64)
        if struct.unpack_from('<III', raw) == (0, 0, 0):
            raise KeyError(name)
        key = _ini_string(b, raw, 16, 200)
        if key == name:
            return raw
        node = struct.unpack_from('<I', raw, 0 if name < key else 8)[0]
    raise KeyError(name)


@_ini_observation
def ini_items(b, group, oi=109):
    raw = _ini_group(b, oi, group)
    head = struct.unpack_from('<I', raw, 32)[0]
    result = {}
    for p, raw in _ini_nodes(b, head, 2048):
        key = _ini_string(b, raw, 16, 8192)
        result[key] = {
            'value': _ini_string(b, raw, 48, 8192),
            'node': p,
            'raw': raw.hex(),
        }
    values = {k: v['value'] for k, v in result.items()}
    if group == 'positions':
        ini_integer_fields(values, ('frame', 'xpos', 'ypos'), required=True)
    elif group == 'stats':
        ini_integer_fields(values, ('difficulty', 'deaths', 'timeseconds'))
    elif group in ('achievements', 'collectables'):
        ini_integer_fields(values, values)
    return result


def ini_objects(b):
    # Cache only object locations, never their INI contents. Validate every use.
    before = b.snapshot()
    identity = (before['scene'], before['run'], before['object_list'])
    cached = getattr(b, '_ini_cache', None)
    valid = bool(
        cached
        and cached['identity'] == identity
        and before['frame_count'] >= cached['tick']
    )
    if valid:
        for o in cached['objects'].values():
            ptr = struct.unpack('<I', b.read(before['object_list'] + o['slot'] * 8, 4))[
                0
            ]
            if ptr != o['ptr']:
                valid = False
                break
            raw = b.read(ptr, 32)
            if (
                struct.unpack_from('<h', raw, 0)[0],
                struct.unpack_from('<H', raw, 18)[0],
                struct.unpack_from('<h', raw, 24)[0],
            ) != (o['handle'], o['oi'], 33):
                valid = False
                break
    if valid:
        result = cached['objects']
    else:
        b._ini_cache = None
        result = {}
        for o in objects(b):
            if o['type'] != 33:
                continue
            meta = struct.unpack_from('<I', bytes.fromhex(o['raw']), 28)[0]
            name = b.read(meta + 90, 24).split(b'\0')[0].decode('latin1')
            if name in ('Ini++', 'Ini++ 3'):
                result[name] = o
    after = b.snapshot()
    if (after['scene'], after['run'], after['object_list']) != identity or after[
        'frame_count'
    ] < before['frame_count']:
        b._ini_cache = None
        raise RuntimeError('Scene changed during observation')
    if result:
        b._ini_cache = dict(
            identity=identity, tick=after['frame_count'], objects=result
        )
    return result


def ini_object_ids(b):
    return {name: o['oi'] for name, o in ini_objects(b).items()}


def live_flags(b):
    oi = ini_object_ids(b)['Ini++']
    values = ini_items(b, 'collectables', oi)
    return {k: values.get(k, {}).get('value', '0') for k in ('scouter', 'timer')}


def set_reward_flags(b, scouter, timer):
    """Lab-only: update existing booleans in caches and disk with read-back verification (not yet a game-thread transaction)."""
    import psutil
    from PY.file_utils import smart_read
    from PY.ini_utils import apply_values_in_section
    from PY.save_utils import encrypt_save_atomic

    p = psutil.Process(game_window().pid)
    # Do not SIGSTOP Wine: WriteProcessMemory may need the target to service it.
    try:
        ids = ini_object_ids(b)
        for name, fn in [('Ini++', 'SaveFile1.ini'), ('Ini++ 3', 'onlineLicense.ini')]:
            oi = ids[name]
            text, _ = smart_read(str(BASE / 'IWBTB' / fn))
            # Use actual cached Stats, not stale disk counters.
            groups = ini_groups(b, oi)
            if 'stats' in groups:
                from PY.ini_utils import parse_ini

                canonical = {k.lower(): k for k in parse_ini(text).get('stats', {})}
                vals = {
                    canonical.get(k, k): v['value']
                    for k, v in ini_items(b, 'stats', oi).items()
                }
                text = apply_values_in_section(text, 'Stats', vals)
            for group in ('collectables', 'achievements'):
                values = ini_items(b, group, oi)
                for key, new in [('scouter', str(scouter)), ('timer', str(timer))]:
                    if key not in values:
                        continue
                    old = values[key]['value']
                    assert old in ('0', '1')
                    if old != new:
                        assert b.cmd(f'value {oi} {group} {key} {old} {new}')['written']
                text = apply_values_in_section(
                    text, group, {'Scouter': str(scouter), 'Timer': str(timer)}
                )
            assert encrypt_save_atomic(text, str(BASE / 'IWBTB' / fn), b'BLOB')
    finally:
        pass


def transition(b, frame, x, y, save_name="SaveFile1.ini", *, stabilize=False):
    if stabilize:
        from spawn_guard import perform

        return perform(
            b,
            frame,
            x,
            y,
            lambda: _transition(
                b, frame, x, y, save_name, notify_arrival=False, require_generation=True
            ),
        )
    return _transition(b, frame, x, y, save_name)


def _transition(
    b, frame, x, y, save_name, *, notify_arrival=True, require_generation=False
):
    if save_name not in ("SaveFile1.ini", "SaveFile2.ini", "SaveFile3.ini"):
        raise ValueError("Invalid save slot")
    from PY.file_utils import smart_read
    from PY.ini_utils import apply_values_in_section
    from PY.save_utils import encrypt_save_atomic

    # This uses the attached bridge, not emulated keys: no focus change or delay.
    try:
        before = b.snapshot()
        text, _ = smart_read(str(BASE / 'IWBTB' / save_name))
        text = apply_values_in_section(
            text, 'Positions', {'frame': str(frame), 'xPos': str(x), 'yPos': str(y)}
        )
        assert encrypt_save_atomic(text, str(BASE / 'IWBTB' / save_name), b'BLOB')
        assert b.cmd(f'scene {frame-1} {before["scene"]}')['requested']
        from transition_timing import observe

        observe(b, 'requested')
    finally:
        pass
    deadline = time.monotonic() + 8
    generation_changed = False
    pause_released = False
    while time.monotonic() < deadline:
        time.sleep(0.005)
        try:
            s = b.snapshot()
            if require_generation:
                generation_changed = (
                    generation_changed
                    or s['next'] != 0
                    or any(s[k] != before[k] for k in ('scene', 'run', 'object_list'))
                    or s['frame_count'] < before['frame_count']
                )
                if not generation_changed:
                    continue
                # A same-scene reload can reuse RunHeader. Release the old pause after
                # confirmed engine processing instead of waiting for its two-second cap.
                address = getattr(b, 'spawn_guard_address', None)
                if (
                    not pause_released
                    and s['scene'] == frame - 1
                    and s['next'] == 0
                    and address is not None
                ):
                    b.cmd(f'menu {address:x} 60 1')
                    pause_released = True
            if s['scene'] != frame - 1 or s['next'] != 0 or s['frame_count'] < 2:
                continue
            ids = ini_object_ids(b)
            pos = ini_items(b, 'positions', ids['Ini++'])
            confirmed = all(
                int(pos[k]['value']) == v
                for k, v in [('frame', frame), ('xpos', x), ('ypos', y)]
            )
            if not confirmed and require_generation:
                from spawn_guard import adjusted_checkpoint

                confirmed = adjusted_checkpoint(b, s, frame, x, y, pos)
            if confirmed:
                if notify_arrival:
                    observe(b, 'arrived')
                return s
        except (RuntimeError, KeyError, StopIteration):
            continue
    raise TimeoutError('Engine did not confirm scene and spawn')


def dismiss_pickup():
    from PY import platform_windows as gw

    w = game_window()
    dialogs = [
        d for d in gw.getAllWindows() if d.pid == w.pid and d.title == 'SCOUTER GET!'
    ]
    if dialogs:
        dialogs[0].activate()
        press('Return')
        time.sleep(0.25)
    return bool(dialogs)
