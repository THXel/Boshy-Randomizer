"""Versioned, portable seed settings and deterministic level/boss routes."""

import hashlib
from beta_catalogue import BOSSES, ROOMS, normalize_core, catalogue

LEGACY_LEVELS = dict(
    zip(
        ROOMS,
        (
            'Prehistorik',
            'Green Greens',
            'Cheetahmen II',
            'VVVVVV',
            'Wario',
            'Castlevania',
            'Milons Secret Castle',
            'Metal Gear',
            'Megaman',
            'Kid Icarus',
            'Ninja Gaiden',
            'Desert',
        ),
    )
)
V4_LEVELS = {
    **LEGACY_LEVELS,
    'tutorial': 'Tutorial',
    'save14.ini': 'Secret Mario',
    'save17.ini': 'Justin.tv',
    'save19.ini': 'Pokémon',
    'save20.ini': 'Tower',
    'save21.ini': 'World of Warcraft',
    'save18.ini': 'Final Path (Terranigma)',
}
NEW_LEVELS = {
    'save23.ini': 'Green Greens · nach Kracko',
    'save22.ini': 'Ninja Gaiden · nach Ryu',
}
V5_LEVELS = {**V4_LEVELS, **NEW_LEVELS}
NEW_LEVELS = {**NEW_LEVELS, 'kid_icarus_after': 'Kid Icarus · nach Miniboss'}
V6_LEVELS = {
    **V5_LEVELS,
    'save12.ini': 'Kid Icarus · vor Miniboss',
    'kid_icarus_after': NEW_LEVELS['kid_icarus_after'],
}
V8_LEVELS = {
    **V6_LEVELS,
    'save9.ini': 'Random World · Teil 1',
    'save10.ini': 'Random World · Teil 2',
}
LEVELS = {k: v for k, v in V8_LEVELS.items() if k != 'tutorial'}
RUSH_MODES = ('boss_rush', 'level_rush')
MODE_NAMES = {
    'randomizer': 'Randomizer',
    'target': 'Target Select',
    'normal': 'Normal',
    'boss_rush': 'Boss Rush',
    'level_rush': 'Level Rush',
}


def mode_name(mode):
    return MODE_NAMES.get(mode, 'Randomizer')


def level_catalogue(version):
    return (
        LEVELS
        if version >= 9
        else (
            V8_LEVELS
            if version >= 7
            else (
                V6_LEVELS
                if version >= 6
                else (
                    V5_LEVELS
                    if version >= 5
                    else V4_LEVELS if version >= 4 else LEGACY_LEVELS
                )
            )
        )
    )


ADVANCED_PAGE_SIZE = 13
ADVANCED_PAGES = (
    max(len(LEVELS), len(BOSSES)) + ADVANCED_PAGE_SIZE - 1
) // ADVANCED_PAGE_SIZE
ADVANCED = {
    'route_version',
    'level_pool',
    'boss_pool',
    'level_count',
    'route_boss_count',
    'start_character',
}


def defaults(version=9):
    return dict(
        route_version=version,
        level_pool=list(level_catalogue(version)),
        boss_pool=list(catalogue({"route_version": version})),
        level_count=7,
        route_boss_count=7,
        start_character='Auto',
    )


def normalize(options):
    raw = dict(options or dict(difficulty=1, levels=True, items=True, characters=False))
    has_hacks = 'extras' in raw
    hacks = raw.pop('extras', None)
    if has_hacks:
        from run_extras import normalize as normalize_extras

        hacks = normalize_extras(hacks)
    extra = {k: raw.pop(k) for k in ADVANCED if k in raw}
    d = normalize_core(raw, extra.get('route_version', 1))
    if hacks is not None:
        d['extras'] = hacks
    if not extra:
        if d.get('mode') in RUSH_MODES:
            raise ValueError('Rush benötigt die aktuelle Routen-Version.')
        return d  # Existing manifests retain their exact binding.
    if set(extra) != ADVANCED or extra['route_version'] not in (2, 3, 4, 5, 6, 7, 8, 9):
        raise ValueError('Unbekannte Routen-Version.')
    if d.get('mode') in RUSH_MODES:
        if extra['route_version'] < 9:
            raise ValueError('Rush benötigt die aktuelle Routen-Version.')
        pool, count = (
            ('level_pool', 'level_count')
            if d['mode'] == 'boss_rush'
            else ('boss_pool', 'route_boss_count')
        )
        extra[pool] = []
        extra[count] = 0
        d['levels'] = True
    for key, valid in [
        ('level_pool', level_catalogue(extra['route_version'])),
        ('boss_pool', catalogue(extra)),
    ]:
        values = extra[key]
        if (
            not isinstance(values, list)
            or any(type(v) is not str or v not in valid for v in values)
            or len(values) != len(set(values))
        ):
            raise ValueError('Ungültige Level-/Boss-Auswahl.')
        extra[key] = sorted(values)
    for key, pool in [('level_count', 'level_pool'), ('route_boss_count', 'boss_pool')]:
        if type(extra[key]) is not int or not 0 <= extra[key] <= len(extra[pool]):
            raise ValueError('Anzahl übersteigt die ausgewählten Level/Bosse.')
    if extra['level_count'] + extra['route_boss_count'] == 0:
        raise ValueError('Mindestens ein Level oder Boss muss ausgewählt sein.')
    if (
        type(extra['start_character']) is not str
        or not 1 <= len(extra['start_character']) <= 50
    ):
        raise ValueError('Ungültiger Startcharakter.')
    if d.get('mode') == 'target':
        extra = defaults(extra['route_version'])
        extra.update(
            level_pool=sorted(level_catalogue(extra["route_version"])),
            boss_pool=sorted(catalogue(extra)),
        )
    elif d.get('mode') == 'normal':
        chosen = extra['start_character']
        extra = defaults(extra['route_version'])
        extra.update(
            start_character=chosen,
            level_pool=sorted(level_catalogue(extra['route_version'])),
            boss_pool=sorted(catalogue(extra)),
        )
    return {**d, **extra}


def route(seed, options):
    if (
        options.get('route_version') not in (2, 3, 4, 5, 6, 7, 8, 9)
        or options.get('mode') in ('target', 'normal')
        or not options.get('levels', True)
    ):
        return []

    def pick(values, n, kind):
        return sorted(
            values,
            key=lambda v: hashlib.sha256(
                f'{seed}\0route-v{options["route_version"]}\0{kind}\0{v}'.encode()
            ).digest(),
        )[:n]

    levels = pick(options['level_pool'], options['level_count'], 'level')
    bosses = [
        BOSSES[k][2]
        for k in pick(options['boss_pool'], options['route_boss_count'], 'boss')
    ]
    result = []
    for i in range(max(len(levels), len(bosses))):
        if i < len(levels):
            result.append(levels[i])
        if i < len(bosses):
            result.append(bosses[i])
    return result + ['boss_solgryn.ini']


def pool_names(options):
    if options.get('mode') == 'target':
        return (
            *level_catalogue(options.get("route_version", 1)),
            *(v[2] for v in catalogue(options).values()),
            'gastly_grass',
            'boss_solgryn.ini',
        )
    return (
        *options['level_pool'],
        *(BOSSES[k][2] for k in options['boss_pool']),
        'boss_solgryn.ini',
    )


def character(base, seed, options):
    from character_cycle import initial, roster

    name = options.get('start_character', 'Auto')
    if name == 'Auto' or options.get('mode') == 'target':
        return initial(base, seed, options['characters'])
    return (
        next(
            (
                dict(name=c['name'], id=c['id'])
                for c in roster(base)
                if c['name'] == name
            ),
            None,
        )
        or _invalid_character()
    )


def _invalid_character():
    raise ValueError('Dieser Startcharakter ist nicht verfügbar.')


def encode(seed, options):
    from seed_share import encode as share

    return share(seed, options)


def decode(value, options=None):
    value = str(value).strip()
    if value.startswith('BR'):
        from seed_share import decode as shared

        return shared(value)
    from seed_codec import seed_text

    return seed_text(value), normalize(options)
