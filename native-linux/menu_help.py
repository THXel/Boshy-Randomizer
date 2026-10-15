"""Shared mouse/keyboard help and paginated seed differences; no run mutations."""
from ui_i18n import tr,display
from run_extras import EXTRAS,SHOT_MODES
from run_settings import LEVELS,BOSSES,normalize

HELP={
 'mode':('Modus','Randomizer follows a route. Target Select continues until all goals are complete.'),
 'difficulty':('Schwierigkeit','Choose the original game difficulty for this run.'),
 'levels':('Position-Randomizer','Move to the next seeded stage only after its assigned exit or boss victory.'),
 'items':('Item-Randomizer','Item and character chests share one shuffled reward pool.'),
 'characters':('Charakter-Randomizer','Change character at each randomizer transition. New unlocks join the pool. F3 is locked.'),
 'target_count':('Ziel-Items','The seed selects this many required items. Chest contents stay original.'),
 'boss_count':('Ziel-Bosse','Optionally require these seeded boss victories before Solgryn.'),
 'level_count':('Level-Anzahl','How many stages to draw from the selected level pool. Zero allows bosses only.'),
 'route_boss_count':('Boss-Anzahl','How many bosses to draw from the selected boss pool. Zero allows levels only.'),
 'start_character':('Startcharakter','Auto uses Dark Boshy, or a seeded character when character randomization is enabled.'),
 'shot_mode':('Schussstil-Randomizer','Only projectile appearance and shooting effects change; your character stays the same.'),
 'seed':('Seed','Share the complete code. Import shows a preview before changing your settings.'),
 'advanced':('Advanced','Changes stay in this draft until you apply them. Escape offers apply, discard or continue editing.'),
 'pool':('Seed pool','Enter or click includes this stage. Arrows only move the selection.'),
 'time':('Zeitgrenze einstellen','Each timed change draws a new delay between one second and your chosen maximum.'),
 'off':('AUS','Keep the normal projectile and shooting effects.'),
 'random_interval':('Zufällige Wartezeit','Draw a random delay within your limit. Loading and paused runs do not consume this time.'),
 'spot':('Nach jedem Spot','Change at each randomizer transition, including level and boss transitions.'),
 'death':('Nach jedem Tod','Change after a newly observed death, once per death.'),
 'death_and_spot':('Nach Tod & Spot','Change after deaths and randomizer transitions. One observation never changes twice.'),
 'presets':('Vorlagen · Standard / …','Use a starting preset, then adjust every option individually.'),
 'start':('Lauf starten','Start this seed in the selected empty save slot.'),
}

def help_for(m):
 p=m.page;f=m.focus;key=None
 if p=='new':
  key={0:'seed',1:'mode',2:'difficulty',3:'target_count' if m.options['mode']=='target' else 'levels',4:'boss_count' if m.options['mode']=='target' else 'items',5:'characters',6:'start',7:'advanced',8:'shot_mode',9:'presets'}.get(f)
 elif p=='advanced':key={0:'level_count',1:'route_boss_count',2:'start_character'}.get(f,'pool' if 3<=f<3+len(LEVELS)+len(BOSSES) else 'advanced')
 elif p=='extras' and f<len(EXTRAS):return EXTRAS[f][1:3]
 elif p=='shots':key=SHOT_MODES[f] if f<5 else 'time' if f==5 else 'shot_mode'
 elif p=='choice':key=m.choice_name
 elif p=='interval':key='time'
 elif p in ('seed','seed_preview'):key='seed'
 elif p=='characters':key='start_character'
 elif p=='presets':key='presets'
 elif p=='discard':key='advanced'
 return HELP.get(key)

LABELS={'difficulty':'Schwierigkeit','levels':'Position-Randomizer','items':'Item-Randomizer','characters':'Charakter-Randomizer','mode':'Modus','target_count':'Ziel-Items','boss_count':'Ziel-Bosse','route_version':'Route revision','level_count':'Level-Anzahl','route_boss_count':'Boss-Anzahl','start_character':'Startcharakter','level_pool':'Level pool','boss_pool':'Boss pool','shot_mode':'Schussstil-Randomizer','shot_interval_seconds':'Time limit'}

def preview_rows(old_seed,old,new_seed,new):
 # A changed-only view, with explicit per-stage changes so a count cannot hide
 # that one enabled stage was exchanged for another.
 old=dict(old);new=normalize(new);rows=[]
 def fmt(k,v):
  if type(v) is bool:return str(tr('AN' if v else 'AUS'))
  if k=='difficulty':
   from menu_model import DIFFICULTIES
   return DIFFICULTIES[v]
  if k=='mode':return 'Target Select' if v=='target' else 'Randomizer'
  if k=='shot_mode':return str(tr(HELP[v][0]))
  if k=='shot_interval_seconds':return f'{v//60}:{v%60:02d}'
  return str(tr('Automatisch')) if v=='Auto' else str(v)
 def row(label,a,b,changed):rows.append((str(tr(label)),str(a),str(b),changed))
 row('Seed',old_seed,new_seed,old_seed!=new_seed)
 for k in LABELS:
  if k not in new or k in ('level_pool','boss_pool','shot_mode','shot_interval_seconds'):continue
  row(LABELS[k],fmt(k,old.get(k,'–')),fmt(k,new[k]),old.get(k)!=new[k])
 for k,table in [('level_pool',LEVELS),('boss_pool',{k:v[0] for k,v in BOSSES.items()})]:
  a=set(old.get(k,[]));b=set(new.get(k,[]));row(LABELS[k],len(a),len(b),a!=b)
  for name in sorted(a^b):row(table[name],tr('AN' if name in a else 'AUS'),tr('AN' if name in b else 'AUS'),True)
 for k,label,_,_ in EXTRAS:
  a=old.get('extras',{}).get(k,False);b=new.get('extras',{}).get(k,False);row(label,fmt(k,a),fmt(k,b),a!=b)
 for k,default in [('shot_mode','off'),('shot_interval_seconds',300)]:
  a=old.get('extras',{}).get(k,default);b=new.get('extras',{}).get(k,default);row(LABELS[k],fmt(k,a),fmt(k,b),a!=b)
 changes=[v for v in rows if v[3]]
 return changes or rows
