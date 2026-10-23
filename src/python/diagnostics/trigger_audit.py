"""Per-spot evidence; simulations never masquerade as natural gameplay tests."""

from pathlib import Path
import json
import hashlib
import struct
from native_level_route import catalogue
from beta_catalogue import EXTRA_POINTS
from minibosses import prepare_pool
from run_settings import defaults

FILES = (
    'spawn_guard.py',
    'gastly_route_lab.py',
    'lab.py',
    'native_menu_host.py',
    'menu_controller.py',
    'menu_gameplay.py',
    'fast_exit.py',
    'fast_exit.c',
    'intro_guard.py',
    'run_extras.py',
    'native_extras.c',
    'native_extras.dll',
    'native_triggers.py',
    'native_player.py',
    'native_progress.py',
    'native_level_route.py',
    'runtime_versions.py',
    'run_settings.py',
    'beta_catalogue.py',
    'minibosses.py',
    'beta_bosses.py',
    'old_sonic.py',
    'transition_guard.py',
    'native_menu_polished.dll',
    'native_spots.json',
    'INI/positions.json',
)


def fingerprint(base):
    def content(name):
        path = Path(base) / name
        if path.suffix == '.json':
            return json.dumps(
                json.loads(path.read_text(encoding='utf-8')),
                sort_keys=True,
                separators=(',', ':'),
            ).encode()
        raw = bytearray(path.read_bytes())
        # Reproducible packaging zeroes PE timestamps and its derived checksum.
        # Compare executable/data bytes unchanged; launch integrity checks stay strict.
        if path.suffix == '.dll' and raw[:2] == b'MZ':
            pe = struct.unpack_from('<I', raw, 60)[0]
            optional = pe + 24
            if (
                raw[pe : pe + 4] != b'PE\0\0'
                or struct.unpack_from('<H', raw, optional)[0] != 0x10B
            ):
                raise ValueError('Unknown audit DLL format')
            raw[pe + 8 : pe + 12] = bytes(4)
            raw[optional + 64 : optional + 68] = bytes(4)
            export = struct.unpack_from('<I', raw, optional + 96)[0]
            sections = optional + struct.unpack_from('<H', raw, pe + 20)[0]
            for i in range(struct.unpack_from('<H', raw, pe + 6)[0]):
                vsize, rva, size, offset = struct.unpack_from(
                    '<4I', raw, sections + 40 * i + 8
                )
                if export and rva <= export < rva + size:
                    stamp = offset + export - rva + 4
                    raw[stamp : stamp + 4] = bytes(4)
                    break
        return raw

    return hashlib.sha256(
        ''.join(hashlib.sha256(content(n)).hexdigest() for n in FILES).encode()
    ).hexdigest()


def points(base):
    base = Path(base)
    p = catalogue(json.loads((base / 'INI/positions.json').read_text(encoding='utf-8')))
    p.update(json.loads((base / 'native_spots.json').read_text(encoding='utf-8')))
    p.update(EXTRA_POINTS)
    from run_settings import pool_names

    opts = defaults()
    opts['mode'] = 'target'
    names = pool_names(opts)
    return {k: v for k, v in prepare_pool(p, opts).items() if k in names}


def rows(base):
    from debug_data import read_json
    from native_models import location
    from run_settings import LEVELS, BOSSES

    names = {
        **LEVELS,
        **{v[2]: v[0] for v in BOSSES.values()},
        'gastly_grass': 'Gastly',
        'boss_solgryn.ini': 'Solgryn',
    }
    data = read_json(Path(base) / 'trigger-test-results.json', {})
    fresh = data.get('fingerprint') == fingerprint(base)
    result = []
    for spot, p in points(base).items():
        evidence = data.get('spots', {}).get(spot, {}) if fresh else {}
        result.append(
            dict(
                spot=spot,
                name=p.get('label', names.get(spot, location(p['frame']))),
                frame=p['frame'],
                **{
                    k: evidence.get(k, 'Offen')
                    for k in ('start', 'exit', 'reset', 'hacks')
                },
                natural=evidence.get('natural', 'Offen'),
            )
        )
    return result
