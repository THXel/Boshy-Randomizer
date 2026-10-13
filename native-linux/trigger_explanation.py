"""Human-readable diagnostics derived from the active run's actual gates."""
def explain(player):
 p=player.progress;d=p.data;o=getattr(player,'debug_sample',{});gate=d.get('completion_gate',{});spot=d.get('trigger_spot',d['spot']);point=player.m['pool'].get(spot,{})
 rules=getattr(player,'rules',None);mod=rules.module('native_triggers') if rules else __import__('native_triggers')
 from native_models import location
 exits=mod.exits_for(spot,point) if point else ()
 expected=', '.join(f'{location(f)} (Raum {f})' for f in exits)
 segment=point.get('segment');special={'before_kracko':'Tatsächlicher Eintritt in Krackos Kampfschirm','kracko':'Bestätigter Sieg über Kracko','before_ninja_ryu':'Eintritt in Ryus Ausweichpassage','ninja_ryu':'Bestätigter Bildschirm nach Ryu'}
 expected=special.get(segment,expected)
 if spot=='gastly_grass':expected='Gastly mit Awesomesauce fangen, danach R oder automatische Rückkehr'
 if point.get('frame') in (44,45):expected='Bestätigter Boss-Tod nach dem Intro'
 if spot=='boss_solgryn.ini':expected='Solgryn-Sieg im Spiel und Spielstand bestätigt'
 if point.get('frame')==51:expected+=' · Kontrollpunkt 7871 / 553 am Final Path'
 reason='Warte auf den zugeordneten Ausgang.';state='waiting'
 if not player.m['options'].get('levels',True):reason='Position-Randomizer ist für diesen Lauf ausgeschaltet.';state='disabled'
 elif d.get('dialog_wait'):reason='Belohnungsfenster offen: Übergang wartet auf Bestätigung.';state='blocked'
 elif d.get('pending'):reason='Ziel bereits festgelegt: '+str(d['pending'])+'. Warte auf bestätigte Ankunft.';state='pending'
 elif not o.get('settled',True):reason='Spiel und gespeicherter Zustand stimmen noch nicht überein.';state='sync'
 elif o.get('beta_boss'):
  sample=o['beta_boss'];b=d.get('beta_gate',{})
  reason='Intro läuft; Boss ist geschützt. S überspringt das Intro.' if sample.get('intro_active') else 'Boshy ist gestorben; kein Sieg bestätigt.' if not sample.get('player_alive') else 'Boss-Tod beobachtet; Bestätigung läuft.' if b.get('death_seen') else f"Warte auf Boss-Tod. HP: {sample.get('hp','?')}."
 elif segment in special:
  mini=d.get('miniboss_gate',{})
  reason='Miniboss-Übergang beobachtet: '+str(mini['candidate']) if mini.get('candidate') else 'Start bestätigt; warte auf '+expected+'.' if mini.get('armed') else 'Ankunftsschutz aktiv; tatsächlichen Eintritt abwarten.'
 elif gate.get('candidate'):reason='Richtiger Ausgang erkannt; muss zwei Sekunden stabil bleiben.';state='confirming'
 elif not gate.get('seen_origin'):reason='Ankunftsschutz: zugehöriger Startbereich noch nicht beobachtet.';state='arrival_guard'
 elif gate.get('won'):reason='Boss-Sieg bestätigt; warte auf den vorgesehenen Ausgang.'
 remaining=None
 if player.m['options'].get('mode')=='target':
  got=d.get('targets_obtained',{});remaining={k:[x for x in v if x not in got.get(k,[])] for k,v in p.goals.items()}
 return dict(state=state,spot=spot,name=point.get('label',spot),expected=expected or 'Sonderregel des aktiven Abschnitts',reason=reason,remaining_targets=remaining,rules_version=rules.meta['identity'] if rules and rules.frozen else 'legacy')
