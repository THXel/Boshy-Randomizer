"""Read-only explanations of observed gates, never used as completion evidence."""

from ui_i18n import tr, display


def explain(player):
    p = player.progress
    d = p.data
    o = getattr(player, 'debug_sample', {})
    gate = d.get('completion_gate', {})
    spot = d.get('trigger_spot', d['spot'])
    point = player.m['pool'].get(spot, {})
    rules = getattr(player, 'rules', None)
    mod = rules.module('native_triggers') if rules else __import__('native_triggers')
    from native_models import location

    exits = mod.exits_for(spot, point) if point else ()
    expected = ', '.join(
        str(tr('{0} (Raum {1})', display(location(f)), f)) for f in exits
    )
    segment = point.get('segment')
    special = {
        'before_kid_icarus': 'Enter the Kid Icarus fight screen.',
        'kid_icarus': 'Defeat Kid Icarus completely and reach the open exit.',
        'before_kracko': 'Enter the Kracko fight screen.',
        'kracko': 'Confirm victory over Kracko.',
        'before_ninja_ryu': 'Enter the Ryu survival screen.',
        'ninja_ryu': 'Reach the confirmed screen after Ryu.',
    }
    if segment in special:
        expected = str(tr(special[segment]))
    if spot == 'boss23.ini':
        expected = str(tr('Old Sonic: zero HP, then six seconds of death animation.'))
    if spot == 'gastly_grass':
        expected = str(
            tr(
                'Catch Gastly with Awesomesauce, then reset or wait for the automatic return.'
            )
        )
    if point.get('frame') in (44, 45):
        expected = str(tr('Confirmed boss death after the intro.'))
    if spot == 'boss_solgryn.ini':
        expected = str(tr('Solgryn victory confirmed in memory and in the save.'))
    if point.get('frame') == 51:
        expected += ' · ' + str(tr('Final Path checkpoint: 7871 / 553.'))
    reason = 'Wait for the assigned exit.'
    args = ()
    state = 'waiting_exit'
    if (getattr(player, 'last', None) or {}).get('completed'):
        reason = 'Run completed. No further teleport is scheduled.'
        state = 'completed'
    elif not player.m['options'].get('levels', True):
        reason = 'Position randomization is disabled for this run.'
        state = 'disabled'
    elif d.get('dialog_wait'):
        reason = 'Reward window open. Confirm it before the transition.'
        state = 'dialog_wait'
    elif d.get('pending'):
        reason = 'Destination selected: {0}. Waiting for confirmed arrival.'
        args = (d['pending'],)
        state = 'pending'
    elif o.get('restart_down') or o.get('restart_pressed'):
        reason = 'Reset observed. Reset alone does not prove a stage exit.'
        state = 'reset_guard'
    elif not o.get('settled', True):
        reason = 'Live and saved states do not match yet.'
        state = 'sync'
    elif spot == 'boss_solgryn.ini':
        reason = 'Wait for the final victory confirmation; intermediate phases do not finish the run.'
        state = 'waiting_final'
    elif o.get('old_sonic'):
        sample = o['old_sonic']
        remaining = sample.get('cooldown_remaining')
        if remaining is not None:
            reason = 'Boss defeated. Death animation: {0} seconds remaining.'
            args = (f'{remaining:.1f}',)
            state = 'death_animation'
        elif not sample.get('player_alive'):
            reason = 'Player is dead. No new boss victory confirmed.'
            state = 'player_dead'
        elif sample.get('hp') is None:
            reason = 'Boss HP observation unavailable. Waiting for a valid sample.'
            state = 'unobserved'
        else:
            reason = 'Wait for boss death. HP: {0}.'
            args = (sample['hp'],)
            state = 'waiting_boss'
    elif o.get('beta_boss'):
        sample = o['beta_boss']
        b = d.get('beta_gate', {})
        if sample.get('intro_active'):
            reason = 'Boss intro protected. S skips the intro.'
            state = 'intro'
        elif not sample.get('player_alive'):
            reason = 'Player is dead. No new boss victory confirmed.'
            state = 'player_dead'
        elif b.get('death_seen'):
            reason = 'Boss death observed. Waiting for confirmation.'
            state = 'confirming'
        else:
            reason = 'Wait for boss death. HP: {0}.'
            args = (sample.get('hp', '?'),)
            state = 'waiting_boss'
    elif segment in special:
        mini = d.get('miniboss_gate', {})
        if mini.get('candidate'):
            reason = 'Miniboss exit observed: {0}.'
            args = (mini['candidate'],)
            state = 'confirming'
        elif mini.get('armed'):
            reason = (
                'Entry confirmed. Waiting for the required miniboss exit or victory.'
            )
            state = 'waiting_miniboss'
        else:
            reason = 'Arrival protection active. Waiting for actual entry.'
            state = 'arrival_guard'
    elif gate.get('candidate'):
        reason = 'Assigned exit confirmed. Transition is being processed.'
        state = 'confirming'
    elif not gate.get('seen_origin'):
        reason = 'Arrival protection: the assigned starting area has not been observed.'
        state = 'arrival_guard'
    elif gate.get('won'):
        reason = 'Boss victory confirmed. Waiting for its assigned exit.'
        state = 'waiting_exit'
    elif point.get('category') == 'bosses':
        reason = 'Wait for boss victory and its assigned exit.'
        state = 'waiting_boss'
    remaining = None
    if player.m['options'].get('mode') == 'target':
        got = d.get('targets_obtained', {})
        remaining = {
            k: [x for x in v if x not in got.get(k, [])] for k, v in p.goals.items()
        }
    evidence = dict(
        frame=o.get('frame'),
        expected_frames=list(exits),
        checkpoint=o.get('checkpoint'),
        settled=o.get('settled'),
        origin_seen=gate.get('seen_origin'),
        candidate=gate.get('candidate'),
        reset_pressed=o.get('restart_pressed'),
        reset_down=o.get('restart_down'),
        boss=o.get('old_sonic') or o.get('beta_boss'),
        miniboss=o.get('miniboss'),
        miniboss_gate=d.get('miniboss_gate'),
        pending=d.get('pending'),
    )
    return dict(
        state=state,
        spot=spot,
        name=point.get('label', spot),
        expected=expected or str(tr('Special rule for the active stage.')),
        reason=str(tr(reason, *args)),
        reason_key=reason,
        reason_args=list(args),
        evidence=evidence,
        remaining_targets=remaining,
        rules_version=rules.meta['identity'] if rules and rules.frozen else 'legacy',
    )
