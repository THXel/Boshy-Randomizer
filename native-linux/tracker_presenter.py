"""Read-only tracker formatting shared by the UI and its regression tests."""
from ui_i18n import tr

DIFFICULTIES = {0: 'Ez Mode', 1: 'Totally Average', 2: 'Hardon Mode', 3: "You're Gonna Rage"}

def elapsed(state, now):
    value = max(0., float(state.get('elapsed', 0)))
    if state.get('timer_running'):
        # Freeze after a missing host update; never jump backwards at the timeout.
        value += min(8., max(0., now - float(state.get('updated_at', now))))
    return value

def progress(state):
    mode = state.get('play_mode', state.get('mode'))
    checks = tr('Fundorte: {0} / {1}', state.get('checks_done', 0), state.get('checks_total', 0))
    if mode == 'target':
        goals = state.get('goals', [])
        done, total = sum(bool(g.get('done')) for g in goals), len(goals)
        label = tr('◆ Ziele: {0} von {1}', done, total)
        if goals and done == total: label += ' · Solgryn'
        return label + '\n' + tr('◆ Ziel · ✓ Erledigt'), 100 * done / max(1, total)
    if mode == 'normal':
        return tr('Originaler Spielverlauf') + '\n' + checks, 100 * state.get('checks_done', 0) / max(1, state.get('checks_total', 0))
    total = state.get('route_limit')
    if total:
        done = total if state.get('phase') == 'finished' else min(total, max(0, state.get('route_index', 0)))
        return tr('Abschnitte: {0} / {1}', done, total) + '\n' + checks, 100 * done / total
    return tr('Wechsel: {0}', state.get('route_index', 0)) + '\n' + checks, 0


def overview(state):
    """Mode-specific rows; confirmed goal receipts override ordinary ownership."""
    mode=state.get('play_mode',state.get('mode'));result=[]
    def group(title,rows,**flags):
        result.extend({**row,'group':tr(title),**flags} for row in rows)
    required={(r.get('kind'),r['name']) for r in state.get('goals',[])} if mode=='target' else set()
    if mode=='target':
        group('Benötigte Ziele',sorted(state.get('goals',[]),key=lambda r:(bool(r.get('done')),r.get('kind')!='item')),goal=True)
    if mode in ('boss_rush','level_rush'):
        group('Route · Solgryn als Finale',state.get('route_stages',[]))
        for key,title in (('items','Gesammelte Items'),('characters','Gesammelte Charaktere')):
            group(title,[r for r in state.get(key,[]) if r.get('done')])
        return result
    for key,title in (('items','Items'),('characters','Charaktere'),('bosses','Bosse')):
        rows=[r for r in state.get(key,[]) if (r.get('kind'),r['name']) not in required]
        group(title,rows)
    return result

def route_entries(player,completed=False):
    if player.m['options'].get('mode') not in ('boss_rush','level_rush'):return []
    from run_settings import LEVELS
    from beta_catalogue import BOSSES
    bosses={v[2]:v[0] for v in BOSSES.values()};bosses['boss_solgryn.ini']='Solgryn'
    import json
    from pathlib import Path
    try:icons=json.loads((player.store.base/'loading-icons/index.json').read_text(encoding='utf-8'))
    except (AttributeError,OSError,ValueError):icons={}
    index=player.progress.data['index'];rows=[]
    for i,spot in enumerate(player.progress.plan):
        point=player.m['pool'][spot];kind='boss' if spot in bosses else 'level'
        rows.append(dict(name=bosses.get(spot,LEVELS.get(spot,spot)),icon_asset=Path(icons.get(str(point['frame']),{}).get('icon','boshy.webp')).name,kind=kind,spot=spot,frame=point['frame'],done=completed or i<index,current=not completed and i==index))
    return rows
