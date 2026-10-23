"""Seeded character choice with the game's ordinary starter roster."""

import json
import hashlib
import struct
import time
from native_session import write_json
from native_models import ini
from mixed_rewards import action, string_param


def roster(base):
    data = json.loads((base / 'INI/characters_rando.json').read_text(encoding='utf-8'))[
        'characters'
    ]
    # Dark Boshy is a native unlockable omitted from the old JSON roster.
    if not any(c['name'] == 'Dark Boshy' for c in data):
        data.append(dict(name='Dark Boshy', id=84, status='locked'))
    return data


def available(base, unlocks):
    return [
        c
        for c in roster(base)
        if c['status'] == 'unlocked' or str(unlocks.get(c['name'].lower(), '0')) == '1'
    ]


def choose(seed, index, pool, previous=None):
    candidates = (
        sorted((c for c in pool if c['name'] != previous), key=lambda c: c['name'])
        or pool
    )
    score = lambda c: hashlib.sha256(
        f"{seed}\0character-cycle-v1\0{index}\0{c['name']}".encode()
    ).digest()
    c = min(candidates, key=score)
    return dict(name=c['name'], id=c['id'])


def initial(base, seed, enabled):
    return (
        choose(seed, 0, available(base, {}))
        if enabled
        else dict(name='Dark Boshy', id=84)
    )


class CharacterCycle:
    def __init__(self, store, m):
        self.store = store
        self.m = m
        self.path = store.root / m['run_id'] / 'characters.json'
        self.data = (
            json.loads(self.path.read_text(encoding='utf-8'))
            if self.path.exists()
            else {
                'run_id': m['run_id'],
                'choices': {'0': initial(store.base, m['seed'], True)},
            }
        )
        if self.data['run_id'] != m['run_id']:
            raise ValueError('Charakterverlauf gehört zu anderem Lauf.')

    def observe_normal(self, frame, stats, bridge, menu_address, *, settled=True):
        # Engine frames are whole levels/boss rooms, not individual scrolling screens.
        # Menus, the teleport hub and ending scenes never consume a character choice.
        playable = {
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            11,
            12,
            13,
            14,
            15,
            17,
            22,
            23,
            24,
            25,
            26,
            27,
            28,
            31,
            32,
            33,
            35,
            36,
            37,
            38,
            39,
            44,
            45,
            46,
            50,
            51,
            52,
            53,
            54,
            59,
            60,
        }
        if not settled or frame not in playable:
            return
        deaths = int(stats.get('deaths', 0))
        state = self.data.setdefault(
            'normal', dict(frame=None, deaths=deaths, sequence=0)
        )
        if not getattr(self, 'normal_observing', False):
            state.update(frame=frame, deaths=deaths)
            self.normal_observing = True
            write_json(self.path, self.data)
            return
        previous = state['frame']
        old_deaths = state['deaths']
        if previous == frame:
            if old_deaths != deaths:
                state['deaths'] = deaths
                write_json(self.path, self.data)
            return
        if deaths != old_deaths:
            state.update(frame=frame, deaths=deaths)
            write_json(self.path, self.data)
            return
        sequence = state['sequence'] + 1
        picked = self.prepare(sequence, bridge, menu_address)
        state.update(frame=frame, deaths=deaths, sequence=sequence)
        write_json(self.path, self.data)
        return picked

    def prepare(self, index, bridge, menu_address):
        from lab import ini_object_ids, ini_items
        from native_profiles import snapshot

        ids = ini_object_ids(bridge)
        unlocks = {
            k: v['value']
            for k, v in ini_items(bridge, 'unlockables', ids['Ini++ 3']).items()
        }
        k = str(index)
        if k not in self.data['choices']:
            previous = self.data['choices'].get(str(index - 1), {}).get('name')
            self.data['choices'][k] = choose(
                self.m['seed'], index, available(self.store.base, unlocks), previous
            )
            write_json(self.path, self.data)
        picked = self.data['choices'][k]
        snap = bridge.snapshot()
        plan = json.loads(
            (self.store.base / 'slot_reward_plan.json').read_text(encoding='utf-8')
        )
        loc = next((l for l in plan['locations'] if l['scene'] == snap['scene']), None)
        if loc:
            ref = bytes.fromhex(loc['license_ref'])
        else:
            # Read the exact current frame's Ini++ reference from an existing getter.
            bank = struct.unpack('<I', bridge.read(snap['run'] + 0x88, 4))[0]
            off = 0
            ref = None
            for _ in range(6000):
                h = bridge.read(bank + off, 14)
                n = -struct.unpack_from('<h', h)[0]
                if n == 0:
                    break
                if not 14 <= n < 32768:
                    raise ValueError('Ungültiger Ereignisblock für Charakterwechsel.')
                b = bridge.read(bank + off, n)
                needle = bytes.fromhex('210058000a00') + struct.pack(
                    '<H', ids['Ini++ 3']
                )
                at = b.find(needle)
                if at >= 0:
                    ref = b[at + 6 : at + 10]
                    break
                off += n
            if ref is None:
                raise ValueError('Charakterprofil-Referenz fehlt.')
        # Ini++ native action 95: Set string (group, key, value), as in the original dresser.
        template = struct.pack(
            '<HhHHHBBBB', 14, 33, 95, *struct.unpack('<HH', ref), 0, 0, 3, 0
        )
        make = lambda key, value: action(
            template,
            [string_param('License'), string_param(key), string_param(str(value))],
            ref,
        )
        a, b = make('Character', picked['id']), make('CharacterName', picked['name'])
        assert len(a) <= 224 and len(b) <= 224
        address = menu_address + 1648
        h = struct.unpack('<7I', bridge.read(address, 28))
        assert h[0] == h[1]
        seq = h[0] + 1
        payload = (
            struct.pack(
                '<7I', seq, h[1], snap['scene'], ids['Ini++'], 0, len(a), len(b)
            )
            + a.ljust(224, b'\0')
            + b.ljust(224, b'\0')
            + bytes(36)
        )
        if not bridge.cmd(f'character {menu_address:x} {payload.hex()}').get('written'):
            raise RuntimeError('Nativer Charakterwechsel wurde abgewiesen.')
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            h = struct.unpack('<7I', bridge.read(address, 28))
            if h[1] == seq:
                break
            time.sleep(0.03)
        if h[1] != seq or h[4] != 1:
            raise RuntimeError('Nativer Charakterwechsel wurde nicht bestätigt.')
        actual = ini_items(bridge, 'license', ids['Ini++ 3'])
        assert (
            actual['character']['value'] == str(picked['id'])
            and actual['charactername']['value'] == picked['name']
        )
        snapshot(self.store, self.m)
        return picked
