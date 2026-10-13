"""User-facing save summaries and a preserving editor for game options."""
from pathlib import Path
import json,time,datetime
from native_session import atomic,write_json,digest
from PY.ini_utils import parse_ini,apply_values_in_section

FRAME_NAMES={1:'Startbildschirm',2:'Spielmenü',3:'Welt 1 · Prehistorik',4:'Hello Kitty',5:'Welt 2 · Green Greens',6:'King Dedede',7:'Biollante',8:'Welt 3 · Cheetahmen II',9:'Gastly',10:'Sonic',11:'Welt 4 · VVVVVV',12:'Skeleton King',13:'Welt 5 · Wario',14:'Mega Man',15:'Welt 6 · Castlevania',17:'Shang Tsung',22:'Welt 7 · Milons Secret Castle',23:'Welt 7½ · Metal Gear',24:'Ganon',25:'Welt 8 · Megaman',26:'Missingno',27:'Welt 9 · Kid Icarus',28:'Mario',30:'Solgryn',31:'Welt 10 · Ninja Gaiden',32:'Ryu',33:'Geheimlevel · 1-1',35:'Welt 11 · Desert',36:'Tutorial',37:'Geheimlevel · JTV',38:'Final Path',50:'Zusatzlevel 50',51:'Zusatzlevel 51',53:'Bonuswelt · WoW',54:'Cheetahman'}

# Match the canonical frame mapping used by the installed Boshy ASL reader.
FRAME_NAMES.update({7:'Ryu',10:'Mario',12:'Biollante',14:'Sonic',17:'Skeleton King',24:'Mega Man',26:'Shang Tsung',28:'Alte Boss-Szene 28',30:'Alte Boss-Szene 30',32:'Missingno',46:'Solgryn',47:'Solgryn besiegt',59:'Ganon'})

# Original optional destinations verified against the running engine.
FRAME_NAMES.update({29:'Teleport Room',33:'Secret Mario',37:'Justin.tv',38:'Final Path (Terranigma)',39:'Gradius',50:'Pokémon',51:'Tower',52:'Welt 6 · Castlevania',53:'World of Warcraft',28:'Bomberman',44:'Questionmark',45:'Ridley',60:'Old Sonic'})

def lower(data):return {str(k).casefold():str(v) for k,v in data.items()}
def ini(store,path):return {k:lower(v) for k,v in parse_ini(store.read_save(path)).items()}
def location(frame):return FRAME_NAMES.get(int(frame or 0),f'Szene {frame}')
def duration(seconds):
 n=max(0,int(float(seconds or 0)));return f'{n//3600:02}:{n//60%60:02}:{n%60:02}'
def owned(group):return [k for k,v in group.items() if v not in ('','0','false','False')]
def slot_summary(store,slot):
 path=store.base/'IWBTB'/f'SaveFile{slot}.ini';m=store.current(slot)
 if not path.exists() or (path.stat().st_size==0 and not (m and m['status']=='ready')):return dict(slot=slot,exists=False,managed=False,title='Freier Speicherplatz',seed='',items=[],characters=[])
 d=ini(store,path);managed=bool(m and m['status']=='ready');folder=store.root/m['run_id'] if managed else None
 profile=folder/'profile.ini' if managed and (folder/'profile.ini').exists() else store.base/'IWBTB/onlineLicense.ini'
 license=ini(store,profile);pos=d.get('positions',{});stats=d.get('stats',{});frame=int(pos.get('frame',0));live={}
 if managed and (folder/'status.json').exists():
  try:live=json.loads((folder/'status.json').read_text())
  except (ValueError,OSError):pass
 if managed and store.game_running():
  from native_profiles import lease
  active=lease(store)
  if active and active['run_id']==m['run_id'] and live:
   frame=live.get('frame',frame);stats={**stats,**live.get('stats',{})}
 checks=d.get('randochecks',{});plan=json.loads((store.base/'slot_reward_plan.json').read_text())
 chars_in_run=[reward['name'] for key,reward in (m['rewards'].items() if managed else ()) if reward['kind']=='character' and checks.get(key.casefold())=='1']
 completed=bool(managed and (folder/'summary.json').exists())
 return dict(slot=slot,exists=True,managed=managed,run_id=m['run_id'] if managed else None,
  title='Abgeschlossen' if completed else ('Randomizer-Lauf' if managed else 'Vorhandener Spielstand'),seed=m['seed'] if managed else '',
  items=owned(d.get('collectables',{})),characters=owned(license.get('unlockables',{})),characters_in_run=chars_in_run,
  character=license.get('license',{}).get('charactername','Boshy'),character_id=license.get('license',{}).get('character','12'),
  frame=frame,location=location(frame),position=[int(pos.get('xpos',0)),int(pos.get('ypos',0))],deaths=int(stats.get('deaths',0)),
  seconds=int(stats.get('timeseconds',0)),difficulty=int(stats.get('difficulty',1)),completed=completed,checks=checks,live=live)

OPTION_FIELDS={
 'ScreenSize':('Fensterbreite',1760,640,3840),
 'SpeechVolume':('Sprachlautstärke',100,0,100),
 'FrameRate':('Bildrate',50,50,50),
 'FPS':('FPS anzeigen',0,0,1),
 'MusicRestart':('Musik bei Neustart neu starten',0,0,1),
 'OnlineLicenseCharacter':('Ausgewählten Charakter verwenden',1,0,1),
 'ControlLEFT':('Nach links','Left',None,None),'ControlRIGHT':('Nach rechts','Right',None,None),
 'ControlUP':('Nach oben','Up',None,None),'ControlDOWN':('Nach unten','Down',None,None),
 'ControlJUMP':('Springen','Z',None,None),'ControlSHOOT':('Schießen','X',None,None),'ControlRESTART':('Neustart','R',None,None)}
KEYS=['Left','Right','Up','Down','Shift','Control','Space','Return']+list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')+list('0123456789')
class Options:
 def __init__(self,store):self.store=store;self.path=store.base/'IWBTB/options.ini'
 def read(self):
  data=ini(self.store,self.path).get('options',{});return {k:data.get(k.casefold(),str(v[1])) for k,v in OPTION_FIELDS.items()}
 def save(self,values):
  self.store._stopped();old=self.path.read_bytes();data={}
  if set(values)!=set(OPTION_FIELDS):raise ValueError('Unvollständige Einstellungen.')
  for k,(label,default,lo,hi) in OPTION_FIELDS.items():
   v=str(values[k]).strip()
   if lo is None:
    if v not in KEYS:raise ValueError('Ungültige Taste für '+label)
   else:
    try:n=int(v)
    except ValueError:raise ValueError(label+': Bitte eine ganze Zahl eingeben.')
    if not lo<=n<=hi:raise ValueError(f'{label}: Erlaubt sind {lo} bis {hi}.')
    if k=='ScreenSize' and n%4:raise ValueError('Die Fensterbreite muss durch 4 teilbar sein (4:3).')
    v=str(n)
   data[k]=v
  keys=[data[k].casefold() for k in data if k.startswith('Control')]
  if len(keys)!=len(set(keys)):raise ValueError('Bitte für jede Aktion eine eigene Taste wählen.')
  text=self.store.read_save(self.path);new=apply_values_in_section(text,'Options',data)
  backups=self.store.root/'settings-backups';backups.mkdir(parents=True,exist_ok=True)
  atomic(backups/(str(time.time_ns())+'-options.ini'),old)
  if self.path.read_bytes()!=old:raise RuntimeError('Die Einstellungen wurden zwischenzeitlich geändert. Bitte neu laden.')
  atomic(self.path,self.store.encode_save(new));return data
