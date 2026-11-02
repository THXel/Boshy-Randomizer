"""Pure adapter from current seed routes to the private Fusion exit prototype.

This is not a complete Fusion run exporter. Only three outgoing boss edges
are implemented by the pinned prototype. Never filter or reroll an unsupported
route: its actual successor must be supported, otherwise export fails.
"""

import configparser
import hashlib
import io
import json

from run_settings import normalize, route
from seed_codec import seed_text
from position_names import legacy_key, legacy_positions

SCHEMA = 3
GROUP = 'FusionRandoV3'
SOURCE_SPOT = 'boss21.ini'
SOURCES = {
    'boss21.ini': {'name': 'Cheetah', 'frame': 54, 'xPos': 100, 'yPos': 100},
    'boss2.ini': {'name': 'Kracko', 'frame': 5, 'xPos': 3400, 'yPos': 300},
    'boss6.ini': {'name': 'Mario', 'frame': 10, 'xPos': 1400, 'yPos': 400},
}
BUILD_SHA256 = '712a0fe5a3f0689dedad523b488ea701ea3818ac64a616d6da068dacd939fd15'
# Frozen ABI of the already compiled/tested Fusion prototype.
TARGETS = {
    'save1.ini': {'code': 1, 'frame': 3, 'x': 30, 'y': 40},
    'save4.ini': {'code': 3, 'frame': 11, 'x': 35, 'y': 140},
    'save7.ini': {'code': 2, 'frame': 15, 'x': 30, 'y': 1300},
}


def plan(seed, options, positions, game_sha256, *, source=SOURCE_SPOT):
    """Resolve the exact next spot from the existing deterministic route."""
    source = legacy_key(source)
    positions = legacy_positions(positions)
    if source not in SOURCES:
        raise ValueError('Unsupported Fusion source: ' + str(source))
    origin = SOURCES[source]
    seed = seed_text(seed)
    settings = normalize(options)
    if game_sha256 != BUILD_SHA256:
        raise ValueError('Fusion prototype build does not match its tested ABI.')
    if (
        settings.get('route_version') != 9
        or settings.get('mode') != 'randomizer'
        or not settings['levels']
    ):
        raise ValueError('Fusion exit probe requires a version-9 randomizer route.')
    ordered = route(seed, settings)
    if source not in ordered:
        raise ValueError('The seed route does not contain ' + origin['name'] + '.')
    index = ordered.index(source)
    target = ordered[index + 1]
    if target not in TARGETS:
        raise ValueError('Fusion exit prototype cannot yet reach: ' + target)
    destination = TARGETS[target]
    point = positions['rooms'].get(target, {})
    if tuple(int(point.get(k, -1)) for k in ('frame', 'xPos', 'yPos')) != tuple(
        destination[k] for k in ('frame', 'x', 'y')
    ):
        raise ValueError('Destination catalogue differs from the tested Fusion build.')
    boss = positions['bosses'].get(source, {})
    if any(int(boss.get(key, -1)) != origin[key] for key in ('frame', 'xPos', 'yPos')):
        raise ValueError('Boss source position differs from the tested build.')
    result = {
        'schema': SCHEMA,
        'scope': 'single_boss_exit_probe_only',
        'seed': seed,
        'options': settings,
        'route': ordered,
        'source': source,
        'origin': dict(origin),
        'source_index': index,
        'target': target,
        'destination': dict(destination),
        'game_sha256': game_sha256,
    }
    binding = json.dumps(result, sort_keys=True, separators=(',', ':')).encode()
    return {**result, 'binding': hashlib.sha256(binding).hexdigest()}


def probe_save(seed, options, positions, game_sha256, *, source=SOURCE_SPOT):
    """Create a NEW test save at the chosen boss, never resume/rewrite a user save.

    All other seed settings are recorded for provenance, not implemented by
    this prototype. This deliberately starts at the edge under test rather
    than pretending that preceding route stages were played or completed.
    """
    result = plan(seed, options, positions, game_sha256, source=source)
    save = configparser.ConfigParser(interpolation=None)
    save.optionxform = str
    save.read_dict(
        {
            'Check': {'SaveVersion': 1},
            'Stats': {
                'Deaths': 0,
                'Difficulty': result['options']['difficulty'],
                'TimeSeconds': 0,
            },
            'Collectables': {'Awesomesauce': 0},
            'Positions': {k: result['origin'][k] for k in ('frame', 'xPos', 'yPos')},
            GROUP: {
                'Schema': SCHEMA,
                'SeedHex': result['seed'].encode('ascii').hex(),
                'Binding': result['binding'],
                result['origin']['name'] + 'Route': result['destination']['code'],
            },
        }
    )
    buffer = io.StringIO()
    save.write(buffer, space_around_delimiters=False)
    return result, buffer.getvalue().replace('\n', '\r\n')
