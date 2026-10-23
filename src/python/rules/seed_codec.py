"""BR12 wire format. Frozen tables/defaults; change the prefix if their meaning changes.

Only setting differences travel. Route revision 9 and extras revision 7 are
implicit. Exporter date is days since 2020; the rule fingerprint remains 64 bits.
No decompression, nested envelope, legacy decoder or local preference defaults.
"""

import base64
from datetime import date, timedelta
import hashlib
import struct

PREFIX = 'BR12-'
EPOCH = date(2020, 1, 1)
LEVELS = (
    'save1.ini',
    'save10.ini',
    'save11.ini',
    'save12.ini',
    'save13.ini',
    'save14.ini',
    'save15.ini',
    'save17.ini',
    'save18.ini',
    'save19.ini',
    'save2.ini',
    'save20.ini',
    'save21.ini',
    'save22.ini',
    'save23.ini',
    'save3.ini',
    'save4.ini',
    'save6.ini',
    'save7.ini',
    'save9.ini',
    'kid_icarus_after',
)
BOSSES = (
    'biollante',
    'bomberman',
    'cheetahman',
    'ganon',
    'gradius',
    'gravitron',
    'hellokitty',
    'kingdedede',
    'kracko',
    'mario',
    'megaman',
    'missingno',
    'ninja_ryu',
    'oldsonic',
    'questionmark',
    'ridley',
    'ryu',
    'shangtsung',
    'skeletonking',
    'sonic',
    'kid_icarus',
    'kappa',
)
HACKS = (
    'quiet_pickups',
    'no_mouse_ghost',
    'one_hp',
    'god_mode',
    'autofire',
    'mirror',
    'death_character',
    'skip_intro',
    'fast_chests',
    'music',
    'spider',
    'sprite_scenery',
)
SHOTS = ('off', 'random_interval', 'spot', 'death', 'death_and_spot')
FIELDS = (
    'difficulty',
    'levels',
    'items',
    'characters',
    'mode',
    'target_count',
    'boss_count',
    'level_pool',
    'boss_pool',
    'level_count',
    'route_boss_count',
    'start_character',
    *HACKS,
    'shot_mode',
    'shot_interval_seconds',
    'sprite_backgrounds',
    'sprite_decor',
    'sprite_tiles',
    'sprite_actors',
    'sprite_dim',
)
OLD_FORMAT = (
    'Dieser Seed verwendet ein altes Format. Bitte einen neuen BR12-Seed erstellen.'
)
INVALID = 'Der geteilte Seed ist unvollständig oder beschädigt.'


def defaults():
    return dict(
        difficulty=1,
        levels=True,
        items=True,
        characters=False,
        mode='randomizer',
        target_count=5,
        boss_count=0,
        route_version=9,
        level_pool=sorted(LEVELS),
        boss_pool=sorted(BOSSES),
        level_count=7,
        route_boss_count=7,
        start_character='Auto',
        extras=dict(
            version=7,
            sprite_backgrounds=True,
            sprite_decor=True,
            sprite_tiles=False,
            sprite_actors=False,
            sprite_dim=20,
            shot_mode='off',
            shot_interval_seconds=300,
            **{k: k in ('quiet_pickups', 'no_mouse_ghost', 'spider') for k in HACKS},
        ),
    )


def seed_text(value):
    value = str(value)
    if not value or len(value) > 128 or any(ord(c) < 32 or ord(c) > 126 for c in value):
        raise ValueError('Seed: 1–128 druckbare Zeichen verwenden.')
    return value


def number(value):
    out = bytearray()
    while value >= 128:
        out.append((value & 127) | 128)
        value >>= 7
    out.append(value)
    return bytes(out)


def text(value):
    raw = value.encode('utf-8')
    return number(len(raw)) + raw


class Reader:
    def __init__(self, data):
        self.data = data
        self.at = 0

    def take(self, n):
        if n < 0 or self.at + n > len(self.data):
            raise ValueError(INVALID)
        out = self.data[self.at : self.at + n]
        self.at += n
        return out

    def number(self):
        value = 0
        for shift in range(0, 35, 7):
            b = self.take(1)[0]
            value |= (b & 127) << shift
            if not b & 128:
                return value
        raise ValueError(INVALID)

    def text(self):
        n = self.number()
        if n > 200:
            raise ValueError(INVALID)
        return self.take(n).decode('utf-8')


def flatten(options):
    return {
        **{k: v for k, v in options.items() if k not in ('route_version', 'extras')},
        **{k: v for k, v in options['extras'].items() if k != 'version'},
    }


def settings(options):
    from run_settings import normalize

    result = normalize(options)
    baseline = defaults()
    if (
        set(result) != set(baseline)
        or result['route_version'] != 9
        or result['extras']['version'] != 7
        or set(result['extras']) != set(baseline['extras'])
    ):
        raise ValueError(OLD_FORMAT)
    return result


def pack(seed, options, release, rules):
    seed = seed_text(seed)
    values = flatten(settings(options))
    baseline = flatten(defaults())
    day = date(int(str(release)[:4]), int(str(release)[4:6]), int(str(release)[6:8]))
    if not EPOCH <= day <= date(2099, 12, 31) or len(rules) != 8:
        raise ValueError(INVALID)
    hex_seed = len(seed) == 8 and all(c in '0123456789ABCDEF' for c in seed)
    payload = bytearray([int(hex_seed)])
    payload.extend(struct.pack('>H', (day - EPOCH).days) + rules)
    payload.extend(bytes.fromhex(seed) if hex_seed else text(seed))
    changed = sum(1 << i for i, k in enumerate(FIELDS) if values[k] != baseline[k])
    payload.extend(number(changed))
    for i, k in enumerate(FIELDS):
        if not changed & (1 << i):
            continue
        value = values[k]
        if isinstance(baseline[k], bool):
            continue
        if k == 'mode':
            payload.append(
                ('randomizer', 'target', 'normal', 'boss_rush', 'level_rush').index(
                    value
                )
            )
        elif k == 'shot_mode':
            payload.append(SHOTS.index(value))
        elif k in ('level_pool', 'boss_pool'):
            table = LEVELS if k == 'level_pool' else BOSSES
            payload.extend(number(sum(1 << table.index(v) for v in value)))
        elif k == 'start_character':
            payload.extend(text(value))
        else:
            payload.extend(number(value))
    payload.extend(hashlib.sha256(b'BR12\0' + payload).digest()[:4])
    return PREFIX + base64.urlsafe_b64encode(payload).decode().rstrip('=')


def unpack(code):
    if not isinstance(code, str) or not code.startswith(PREFIX):
        raise ValueError(OLD_FORMAT)
    try:
        if len(code) > 1024:
            raise ValueError()
        body = code[len(PREFIX) :]
        packet = base64.b64decode(
            body + '=' * (-len(body) % 4), altchars=b'-_', validate=True
        )
        if len(packet) < 18:
            raise ValueError()
        payload, checksum = packet[:-4], packet[-4:]
        if hashlib.sha256(b'BR12\0' + payload).digest()[:4] != checksum:
            raise ValueError()
        r = Reader(payload)
        flags = r.take(1)[0]
        if flags not in (0, 1):
            raise ValueError()
        day = EPOCH + timedelta(days=struct.unpack('>H', r.take(2))[0])
        release = int(day.strftime('%Y%m%d'))
        rules = r.take(8)
        seed = r.take(4).hex().upper() if flags else r.text()
        changed = r.number()
        if changed >> len(FIELDS):
            raise ValueError()
        options = defaults()
        values = flatten(options)
        for i, k in enumerate(FIELDS):
            if not changed & (1 << i):
                continue
            baseline = values[k]
            if isinstance(baseline, bool):
                value = not baseline
            elif k == 'mode':
                value = ('randomizer', 'target', 'normal', 'boss_rush', 'level_rush')[
                    r.take(1)[0]
                ]
            elif k == 'shot_mode':
                value = SHOTS[r.take(1)[0]]
            elif k in ('level_pool', 'boss_pool'):
                table = LEVELS if k == 'level_pool' else BOSSES
                mask = r.number()
                if mask >> len(table):
                    raise ValueError()
                value = sorted(v for j, v in enumerate(table) if mask & (1 << j))
            elif k == 'start_character':
                value = r.text()
            else:
                value = r.number()
            values[k] = value
        for k, value in values.items():
            if k in options['extras']:
                options['extras'][k] = value
            else:
                options[k] = value
        if (
            r.at != len(payload)
            or settings(options) != options
            or pack(seed, options, release, rules) != code
        ):
            raise ValueError()
        return seed, options, dict(release=release, rules=rules.hex())
    except (
        ValueError,
        TypeError,
        KeyError,
        IndexError,
        OverflowError,
        struct.error,
    ) as e:
        raise ValueError(INVALID) from e
