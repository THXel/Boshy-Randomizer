"""One portable BR12 code with settings, exporter date and rule fingerprint."""

import hashlib
import json
from pathlib import Path
from functools import lru_cache

RELEASE = 20261018
RULE_FILES = (
    'seed_codec.py',
    'seed_share.py',
    'spider_randomizer.py',
    'music_randomizer.py',
    'sprite_scenery.py',
    'sprite_scenery_catalogue.json',
    'sprite_chaos.py',
    'sprite_chaos_catalogue.json',
    'run_settings.py',
    'run_extras.py',
    'native_level_route.py',
    'native_triggers.py',
    'native_progress.py',
    'mixed_rewards.py',
    'shot_cycle.py',
    'character_cycle.py',
    'beta_catalogue.py',
    'minibosses.py',
    'beta_bosses.py',
    'native_targets.py',
    'INI/positions.json',
    'slot_reward_plan.json',
    'INI/characters_rando.json',
)


def fingerprint(base):
    base = Path(base)
    try:
        signature = tuple(
            (name, (base / name).stat().st_mtime_ns, (base / name).stat().st_size)
            for name in RULE_FILES
        )
    except FileNotFoundError:
        return bytes(8)
    return _fingerprint(str(base.resolve()), signature)


@lru_cache(maxsize=16)
def _fingerprint(base, signature):
    rows = []
    for name in RULE_FILES:
        p = Path(base) / name
        if not p.is_file():
            return bytes(8)
        data = p.read_bytes()
        if name.endswith('.json'):
            data = json.dumps(
                json.loads(data), sort_keys=True, separators=(',', ':')
            ).encode()
        rows.append((name, hashlib.sha256(data).hexdigest()))
    return hashlib.sha256(json.dumps(rows, separators=(',', ':')).encode()).digest()[:8]


def encode(seed, options, base=None):
    from seed_codec import pack

    return pack(seed, options, RELEASE, fingerprint(base or Path(__file__).parent))


def decode(value):
    from seed_codec import unpack

    seed, options, _ = unpack(value)
    return seed, options


def metadata(value):
    from seed_codec import unpack

    return unpack(str(value).strip())[2]


def compatibility(value, base):
    info = metadata(value)
    current = fingerprint(base).hex()
    if (
        not info['rules']
        or info['rules'] == '0000000000000000'
        or current == '0000000000000000'
    ):
        status = 'unknown'
    elif info['rules'] != current:
        status = 'different'
    else:
        status = 'matching'
    return dict(**info, status=status, current=RELEASE)


def version_text(value):
    if not value:
        return '–'
    s = str(value)
    return f'{s[:4]}.{s[4:6]}.{s[6:8]}'


def encode_saved(seed, options, base, rules=None):
    """Use an existing run's own wire format; never relabel archived rules."""
    if rules is not None and hasattr(rules, 'module'):
        return rules.module('seed_share').encode(seed, options, base)
    return encode(seed, options, base)
