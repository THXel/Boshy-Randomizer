"""Conservative structural checks; unknown platforming requirements remain explicit.

This does not claim to solve the game's full collision/enemy/ability graph.
Only catalogued entrances, explicit exits, reward assignments and declared gates
are evidence for this check. Never silently reroll a shared seed.
"""

from beta_catalogue import goals, BOSSES
from native_triggers import EXITS, BOSS_EXITS
from run_settings import route


def audit(base, seed, options, pool, rewards, locations):
    errors = []
    warnings = []
    planned = route(seed, options)
    required = goals(base, seed, options)
    for name, point in pool.items():
        if (
            not isinstance(point, dict)
            or any(type(point.get(k)) is not int for k in ('frame', 'x', 'y'))
            or point.get('category') not in ('rooms', 'bosses')
        ):
            errors.append('Ungültiger Startpunkt: ' + name)
    if errors:
        return dict(version=1, scope='structural', errors=errors, warnings=[])
    for name in planned:
        if name not in pool:
            errors.append('Routenziel fehlt: ' + name)
    frames = {pool[n]['frame'] for n in (planned or pool) if n in pool}
    # Disabling position randomization follows original progression; the native
    # spot pool is then not a complete map of the rooms that can be visited.
    if not options.get('levels', True):
        frames |= {l['scene'] + 1 for l in locations}
    reachable = set(frames)
    changed = True
    while changed:
        before = len(reachable)
        for f in tuple(reachable):
            reachable.update(EXITS.get(f, ()))
            if f == 22:
                reachable.add(23)  # Internal Random World section; never a trigger.
        changed = len(reachable) != before
    known = {l['key'] for l in locations}
    if set(rewards) != known:
        errors.append('Belohnungsliste passt nicht zu den Fundorten.')
    accessible = [l for l in locations if l['scene'] + 1 in reachable]
    item_names = {
        rewards.get(l['key'], {}).get('name', '').casefold()
        for l in accessible
        if rewards.get(l['key'], {}).get('kind') == 'item'
    }
    for item in required['items']:
        if item.casefold() not in item_names:
            errors.append('Kein zugeordneter Zugang zum Ziel-Item: ' + item)
    for boss in required['bosses']:
        if BOSSES[boss][1] not in reachable:
            errors.append('Kein zugeordneter Zugang zum Ziel-Boss: ' + BOSSES[boss][0])
    # Validate guaranteed route gates in order; optional Gastly is checked separately.
    available = set()
    for name in planned:
        point = pool.get(name, {})
        need = point.get('requires')
        if need and need.casefold() not in available:
            errors.append('Voraussetzung fehlt vor ' + name + ': ' + need)
        available.update(
            rewards.get(l['key'], {}).get('name', '').casefold()
            for l in locations
            if l['scene'] + 1 == point.get('frame')
            and rewards.get(l['key'], {}).get('kind') == 'item'
        )
    gastly = pool.get('gastly_grass')
    if gastly and (
        gastly.get('requires') != 'awesomesauce'
        or gastly.get('exclude_owned') != 'gastly'
    ):
        errors.append('Gastly-Sperre ist unvollständig.')
    if gastly and 'awesomesauce' not in item_names:
        warnings.append(
            'Awesomesauce liegt außerhalb der hier zugeordneten Räume; Gastly bleibt bis zum Fund gesperrt.'
        )
    return dict(
        version=1,
        scope='structural',
        errors=errors,
        warnings=warnings,
        route=planned,
        goals=required,
        known_frames=sorted(reachable),
        mapped_locations=len(accessible),
        total_locations=len(locations),
        remaining_checks=[
            'Gegner- und Bossbedingungen einzelner Truhen',
            'Plattformwege und Fähigkeiten',
            'Sonderausgänge außerhalb der erfassten Zuordnung',
        ],
    )
