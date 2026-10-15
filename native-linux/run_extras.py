"""Versioned optional native rules. Missing settings preserve legacy runs."""
EXTRAS = (
 ('quiet_pickups','Item-Pop-ups unterdrücken','Belohnung und Anzeige im Spiel bleiben erhalten.',True),
 ('no_mouse_ghost','Mausgeist deaktivieren','Mauszeiger frei im Spiel benutzen.',True),
 ('one_hp','Bosse mit 1 HP','Ein Treffer pro verwundbarer Bossphase.',False),
 ('god_mode','God Mode','Schutz vor Gefahren; R und absichtlicher Tod mit Q bleiben.',False),
 ('autofire','Dauerfeuer','Schusstaste halten – auch außerhalb von Ez Mode.',False),
 ('mirror','Spiegelmodus','Originaler gespiegelter Spielmodus.',False),
 ('death_character','Charakterwechsel nach Tod','Zufällig aus Startpool und gesammelten Charakteren.',False),
 ('skip_intro','Boss-Intro überspringen','Originalen S-Skip automatisch auslösen.',False),
 ('fast_chests','Truhenanimation überspringen','Belohnung oben links anzeigen und direkt weiterspielen.',False),
 ('music','Musik mischen','Level- und Bossmusik gemeinsam mischen; feste Zuordnung pro Seed.',False),
 ('spider','Spinnen-Überraschung','Zufallsangriff alle 5–30 Spielminuten, auch bei Bossen.',True),
)
SHOT_MODES=('off','random_interval','spot','death','death_and_spot')
SHOT_LABELS=('AUS','Zufällig innerhalb 5 Min.','Nach jedem Spot','Nach jedem Tod','Nach Tod & Spot')
def defaults():return dict(version=5,shot_mode='off',shot_interval_seconds=300,**{key:default for key,_,_,default in EXTRAS})
def normalize(value):
 if not isinstance(value,dict) or type(value.get('version')) is not int or value['version'] not in (1,2,3,4,5):raise ValueError('Ungültige Extras im Seed.')
 rows=EXTRAS[:7] if value['version']==1 else EXTRAS[:9] if value['version']<4 else EXTRAS[:10] if value['version']==4 else EXTRAS
 keys={'version',*(r[0] for r in rows)} | ({'shot_mode'} if value['version']>=2 else set()) | ({'shot_interval_seconds'} if value['version']>=3 else set())
 if set(value)!=keys or any(type(value[k]) is not bool for k,_,_,_ in rows):raise ValueError('Ungültige Extras im Seed.')
 if value['version']>=2 and value['shot_mode'] not in SHOT_MODES:raise ValueError('Ungültiger Schussstil-Modus.')
 if value['version']>=3 and (type(value['shot_interval_seconds']) is not int or not 1<=value['shot_interval_seconds']<=86400):raise ValueError('Schusswechsel: Bitte 1 Sekunde bis 24 Stunden wählen.')
 return dict(value)
def upgrade(options):
 value=options.get('extras')
 if value and value['version']==5:return value
 options['extras']={**dict(version=5,shot_mode='off',shot_interval_seconds=300,**{r[0]:False for r in EXTRAS}),**(value or {}),'version':5}
 return options['extras']
def flags(options):
 value=options.get('extras',{})
 return int(options['characters']) | (2 if options.get('mode')=='target' else 0) | (2048 if value.get('shot_mode','off')!='off' else 0) | sum((4096 if k=='music' else 8192 if k=='spider' else 4<<i) for i,(k,_,_,_) in enumerate(EXTRAS) if value.get(k,False))
def enabled(options,key):return options.get('extras',{}).get(key,False)

def shot_label(options):
 extra=options.get('extras',{});mode=extra.get('shot_mode','off')
 if mode=='random_interval':
  seconds=extra.get('shot_interval_seconds',300);minutes,seconds=divmod(seconds,60)
  return f'Zufällig bis {minutes}:{seconds:02d} · Enter'
 return SHOT_LABELS[SHOT_MODES.index(mode)]

def presentation(options,shots=None):
 rows=[dict(key=key,icon=icon,label=label,hint=hint) for (key,label,hint,_),icon in zip(EXTRAS,('P','M','1','G','A','↔','C','S','T','♪','S')) if options.get('extras',{}).get(key,False)]
 if shots:
  row=dict(key='shot_style',icon='✦',label='Schussstil: '+shots['style']['name'],hint=shot_label(options),style=shots['style']['name'])
  if options.get('extras',{}).get('shot_mode')=='random_interval':row['remaining']=max(0,float(shots['remaining']))
  rows.append(row)
 return rows
