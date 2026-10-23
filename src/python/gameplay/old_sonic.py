"""Read Old Sonic's native HP and confirm a living encounter before zero HP."""

import hashlib
import struct
import time

FRAME = 60
BOSS_OI = 3062
PLAYER_OI = 307
# Original event sets Sonic's defeat flag when alterable value B is <= zero.
DEATH_EVENT = (
    250804,
    298,
    'af5d4291d59881dbe7704660443638966bb8246da54b1edf693e668e2aedc1c8',
)


class Reader:
    def __init__(self):
        self.identity = None
        self.refs = {}
        self.tick = None

    def sample(self, bridge, snap):
        if snap['scene'] + 1 != FRAME:
            self.__init__()
            return None
        identity = (snap['run'], snap['object_list'])
        if (
            identity != self.identity
            or self.tick is None
            or snap['frame_count'] < self.tick
        ):
            self.refs = {}
            self.identity = identity
            bank = struct.unpack('<I', bridge.read(snap['run'] + 0x88, 4))[0]
            offset, size, want = DEATH_EVENT
            if hashlib.sha256(bridge.read(bank + offset, size)).hexdigest() != want:
                raise RuntimeError('Unbekannte Old-Sonic-Todesbedingung.')
        self.tick = snap['frame_count']

        def present(oi):
            obj = self.refs.get(oi)
            if not obj:
                return None
            pointer = struct.unpack(
                '<I', bridge.read(snap['object_list'] + obj['slot'] * 8, 4)
            )[0]
            if pointer != obj['ptr']:
                return None
            raw = bridge.read(pointer, 132)
            if (
                struct.unpack_from('<H', raw, 18)[0] != oi
                or struct.unpack_from('<h', raw, 24)[0] != 2
                or struct.unpack_from('<h', raw)[0] != obj['handle']
            ):
                return None
            return raw

        boss = present(BOSS_OI)
        player = present(PLAYER_OI)
        if boss is None or player is None:
            from lab import objects

            self.refs = {
                o['oi']: o
                for o in objects(bridge, strict=True)
                if o['type'] == 2 and o['oi'] in (BOSS_OI, PLAYER_OI)
            }
            boss = present(BOSS_OI)
            player = present(PLAYER_OI)
        result = dict(
            frame=FRAME,
            tick=self.tick,
            generation=list(identity),
            player_alive=player is not None,
            hp=None,
            boss_object=None,
        )
        if boss:
            ptr = self.refs[BOSS_OI]['ptr']
            relative = struct.unpack_from('<I', boss, 128)[0]
            if not 128 <= relative < 4096:
                raise RuntimeError('Ungültige Old-Sonic-Werte.')
            values = struct.unpack('<I', bridge.read(ptr + relative, 4))[0]
            raw = bridge.read(values + 16, 16)
            if struct.unpack_from('<I', raw)[0] != 0:
                raise RuntimeError('Unbekanntes Old-Sonic-Lebenspunkteformat.')
            hp = struct.unpack_from('<i', raw, 8)[0]
            if not -1000 <= hp <= 10000:
                raise RuntimeError('Ungültige Old-Sonic-Lebenspunkte.')
            result.update(hp=hp, boss_object=ptr)
        after = bridge.snapshot()
        if (after['scene'], after['run'], after['object_list']) != (
            snap['scene'],
            snap['run'],
            snap['object_list'],
        ) or after['frame_count'] < snap['frame_count']:
            raise RuntimeError('Scene changed during observation')
        return result


class Gate:
    COOLDOWN = 6.0

    def __init__(self):
        self.identity = None
        self.tick = None
        self.deaths = None
        self.armed = False
        self.reported = False
        self.since = None
        self.boss = None

    def remaining(self, now=None):
        if self.since is None:
            return None
        return max(
            0.0,
            self.COOLDOWN - ((time.monotonic() if now is None else now) - self.since),
        )

    def observe(self, spot, index, sample, deaths, now=None):
        now = time.monotonic() if now is None else now
        if spot != 'boss23.ini' or not sample or sample.get('frame') != FRAME:
            self.__init__()
            return False
        identity = (spot, index, tuple(sample['generation']))
        obj = sample.get('boss_object')
        reset = (
            identity != self.identity
            or self.deaths != deaths
            or (self.tick is not None and sample['tick'] < self.tick)
            or (self.boss is not None and obj is not None and self.boss != obj)
        )
        if reset:
            self.armed = False
            self.reported = False
            self.since = None
            self.boss = None
        self.identity = identity
        self.tick = sample['tick']
        self.deaths = deaths
        if obj is not None:
            self.boss = obj
        hp = sample.get('hp')
        if not sample.get('player_alive'):
            self.armed = False
            self.since = None
            return False
        if hp is not None and hp > 0:
            self.armed = True
            self.since = None
            return False
        if hp is not None and hp <= 0 and self.armed and self.since is None:
            self.since = now
        # The boss may disappear as part of its death animation. Only a prior,
        # explicitly observed zero-HP value can keep that cooldown alive.
        if self.since is None:
            return False
        if not self.reported and now - self.since >= self.COOLDOWN:
            self.reported = True
            return True
        return False


def confirm(progress, gate, sample, stats):
    """Credit only the active Old Sonic stage; let normal routing choose its next spot."""
    d = progress.data
    active = d.get('trigger_spot', d['spot'])
    won = gate.observe(active, d['index'], sample, int(stats.get('deaths', 0)))
    if sample is not None:
        sample['cooldown_remaining'] = gate.remaining()
    if not won or d.get('pending') or not progress.m['options'].get('levels', True):
        return False
    d.setdefault('stage_bosses', {})['oldsonic'] = dict(
        index=d['index'],
        frame=FRAME,
        native_hp=0,
        exit='Old Sonic besiegt (HP 0)',
        cooldown_seconds=gate.COOLDOWN,
    )
    progress.trace('stage-boss-defeated', frame=FRAME, boss='oldsonic', native_hp=0)
    progress.save()
    return True
