"""Main-menu state and save summaries, independent of the native renderer."""
from ui_i18n import tr, display, font_path, font_family, configure_tk, LANGUAGE, Localized
import json,secrets
from copy import deepcopy
from run_extras import EXTRAS,defaults as extra_defaults,upgrade,SHOT_MODES
from run_settings import defaults,normalize,decode,encode,character,LEVELS,BOSSES as ROUTE_BOSSES
from run_settings import ADVANCED_PAGE_SIZE,ADVANCED_PAGES,LEGACY_LEVELS,NEW_LEVELS
from beta_catalogue import catalogue,EXTRA_BOSSES,MINIBOSSES,stage_achievements
from native_models import slot_summary,ini
DIFFICULTIES={0:'Ez Mode',1:'Totally Average',2:'Hardon Mode',3:"You're Gonna Rage"}
BOSSES={'hellokitty':'Hello Kitty','kingdedede':'King Dedede','biollante':'Biollante','sonic':'Sonic','skeletonking':'Skeleton King','megaman':'Mega Man','shangtsung':'Shang Tsung','ganon':'Ganon','missingno':'Missingno','mario':'Mario','ryu':'Ryu','solgryn':'Solgryn','randomness':'Random World'}
def summary(store,slot):
 d=slot_summary(store,slot)
 if not d['exists']:return d
 data=ini(store,store.base/'IWBTB'/f'SaveFile{slot}.ini');a=data.get('achievements',{})
 d['worlds']=[i for i in range(1,12) if int(a.get(f'world{i}clear',0))>=1]
 d['bosses']=[v for k,v in BOSSES.items() if int(a.get(k,0))>=2]
 d['difficulty_name']=DIFFICULTIES.get(d['difficulty'],tr('Unbekannt'))
 m=store.current(slot);d['settings']=m.get('options',{}) if d['managed'] else {}
 if d['managed']:d['characters']=sorted(set(d.get('characters_in_run',[])))
 d['recovery']=None
 if d['managed']:
  path=store.root/m['run_id']/'progress.json'
  if path.exists():
   progress=json.loads(path.read_text())
   if progress.get('run_id')==m['run_id'] and progress.get('binding')==m['session_binding']:
    d['recovery']=progress.get('pending')
    point=m.get('pool',{}).get(progress.get('spot'),{})
    if point.get('frame')==d['frame'] and point.get('label'):d['location']=point['label']
    from beta_catalogue import BETA
    earned=stage_achievements(m['options'],progress,a)
    d['bosses']=[v[0] for k,v in catalogue(m['options']).items() if int(earned.get(k,0))>=2]
    if int(a.get('solgryn',0))>=2:d['bosses'].append('Solgryn')
 return d
class Menu:
 def __init__(self,store,slot=1):
  self.advanced_page=0;self.clipboard=None;self.seed_text='';self.seed_selected=False;self.character_names=[];self.store=store;self.slot=slot;self.page='slots';self.focus=0;self.seed=secrets.token_hex(4).upper();self.options=dict(difficulty=1,levels=True,items=True,characters=False,mode='randomizer',target_count=5,boss_count=0);self.options.update(defaults());self.options['extras']=extra_defaults();self.message='';self.dirty=True;self.action=None;self.reload()
 def reload(self):
  self.saves={i:summary(self.store,i) for i in (1,2,3)};self.dirty=True
  if self.page=='slots':self.focus=0
 def select(self,slot):
  if self.slot!=slot:self.focus=0
  self.slot=slot;self.dirty=True
 def key(self,key):
  self.dirty=True
  if self.page=='slots':
   if key==37:self.select((self.slot-2)%3+1)
   elif key==39:self.select(self.slot%3+1)
   elif key in (38,40,9):
    order=[0,1] if self.saves[self.slot]['exists'] else [2,0,1]
    self.focus=order[(order.index(self.focus) + (-1 if key==38 else 1))%len(order)]
   elif key==13:
    if self.focus==2:self.open_advanced()
    elif self.focus==1:
     if not self.open_saved_result():self.page='targets'
    elif self.saves[self.slot]['exists']:self.action=('resume',self.slot,None)
    else:self.page='new';self.focus=1
   elif key==46 and self.saves[self.slot]['exists']:self.page='delete';self.focus=0
   elif key==27:self.action=('quit',0,None)
  elif self.page=='new':
   if key==27:self.page='slots';self.focus=0
   elif key in (38,40,9):
    order=[9,1,2,3,4,5,8,7,0,6]
    self.focus=order[(order.index(self.focus)+(-1 if key==38 else 1))%len(order)]
   elif self.focus==0 and key==13:self.open_seed()
   elif key in (37,39,13) and 1<=self.focus<=5:
    delta=-1 if key==37 else 1
    if self.focus==1:self.options['mode']='target' if self.options['mode']=='randomizer' else 'randomizer'
    elif self.focus==2:self.options['difficulty']=(self.options['difficulty']+delta)%4
    elif self.focus==5:self.options['characters']=not self.options['characters']
    elif self.options['mode']=='target':
     name,limit=('target_count',19) if self.focus==3 else ('boss_count',len(catalogue(self.options))+1)
     self.options[name]=((self.options[name]-1+delta)%limit)+1 if self.focus==3 else (self.options[name]+delta)%limit
    else:
     name='levels' if self.focus==3 else 'items';self.options[name]=not self.options[name]
   elif self.focus==6 and key==13:
    try:
     seed,options=decode(self.seed,self.options);self.action=('new',self.slot,dict(seed=seed,options=options));self.message=''
    except ValueError as e:self.message=str(display(str(e)));self.focus=0
   elif self.focus==9 and key==13:self.page='presets';self.focus=0;self.message=''
   elif self.focus==8 and key in (13,37,39):
    extra=upgrade(self.options)
    if key!=13 or extra['shot_mode']!='random_interval':extra['shot_mode']=SHOT_MODES[(SHOT_MODES.index(extra['shot_mode'])+(-1 if key==37 else 1))%len(SHOT_MODES)]
    if extra['shot_mode']=='random_interval':self.open_interval()
   elif self.focus==7 and key==13:self.open_advanced()

  elif self.page=='interval':self.interval_key(key)
  elif self.page=='presets':self.preset_key(key)
  elif self.page=='result':self.result_key(key)
  elif self.page=='seed':self.seed_key(key)
  elif self.page=='characters':self.character_key(key)
  elif self.page=='advanced':self.advanced_key(key)
  elif self.page=='extras':self.extras_key(key)
  elif self.page=='targets':
   if key in (27,13,9):self.page='slots'
  elif self.page=='delete':
   if key==27:self.page='slots'
   elif key in (37,39,9):self.focus=1-self.focus
   elif key==13:
    if self.focus==1:self.action=('delete',self.slot,None)
    else:self.page='slots'
 def char(self,value):
  if self.page=='interval' and self.focus<2 and 48<=value<=57:
   old=self.interval_fields[self.focus]
   self.interval_fields[self.focus]=(old+chr(value))[-4:] if not self.interval_selected else chr(value)
   self.interval_selected=False;self.dirty=True;self.message='';return
  if self.page=='seed' and self.focus==0 and 32<=value<=126:
   if self.seed_selected:self.seed_text='';self.seed_selected=False
   if len(self.seed_text)<4096:self.seed_text+=chr(value)
   self.message='';self.dirty=True
 def click(self,x,y):
  self.dirty=True
  if self.page=='slots':
   if 614<=x<=860 and 600<=y<=624:self.focus=0;self.key(13)
   elif 614<=x<=860 and 570<=y<=593:
    if self.saves[self.slot]['exists']:self.key(46)
    else:self.open_advanced()
   elif 614<=x<=860 and 630<=y<=649:
    if not self.open_saved_result():self.page='targets'
  elif self.page=='new':
   if 635<=x<=854 and 263<=y<=291:self.page='presets';self.focus=0;return
   for row,i in enumerate([1,2,3,4,5,8]):
    if 245<=x<=856 and 295+row*35<=y<=327+row*35:self.focus=i;self.key(13);return
   if 245<=x<=856 and 603<=y<=642:self.focus=6;self.key(13)
   elif 245<=x<=856 and 508<=y<=539:self.open_advanced()
   elif 245<=x<=856 and 546<=y<=580:self.focus=0;self.open_seed()
  elif self.page=='interval':
   for i,(left,right) in enumerate(((260,535),(555,840))):
    if left<=x<=right and 354<=y<=414:self.focus=i;self.interval_selected=True;return
   if 251<=x<=546 and 604<=y<=640:self.focus=2;self.interval_key(13)
   elif 558<=x<=851 and 604<=y<=640:self.interval_key(27)
  elif self.page=='presets':
   for i in range(4):
    if 251<=x<=851 and 315+i*73<=y<=375+i*73:self.focus=i;self.preset_key(13);return
  elif self.page=='result':
   if 251<=x<=546 and 604<=y<=640:self.focus=0;self.result_key(13)
   elif 558<=x<=851 and 604<=y<=640:self.focus=1;self.result_key(13)
  elif self.page=='seed':
   if 251<=x<=851 and 329<=y<=486:self.focus=0;return
   for i,(left,right) in enumerate(((251,443),(455,647),(659,851)),1):
    if left<=x<=right and 499<=y<=533:self.focus=i;self.seed_key(13);return
   if 251<=x<=546 and 604<=y<=640:self.focus=4;self.seed_key(13)
   elif 558<=x<=851 and 604<=y<=640:self.focus=5;self.seed_key(13)
  elif self.page=='characters':
   for i in range(len(self.character_names)):
    left=249+i%7*87;top=303+i//7*49
    if left<=x<=left+82 and top<=y<=top+45:self.focus=i;self.character_key(13);return
   if 249<=x<=852 and 608<=y<=640:self.character_key(27)
  elif self.page=='extras':
   for i in range(len(EXTRAS)):
    if 245<=x<=856 and 293+i*33<=y<=324+i*33:self.focus=i;self.extras_key(13);return
   if 245<=x<=856 and 608<=y<=642:self.extras_key(27)
  elif self.page=='advanced':
   if 245<=x<=548 and 608<=y<=642:self.page='new';self.focus=7;return
   if 558<=x<=856 and 608<=y<=642:self.open_extras();return
   for i in range(3):
    if 245<=x<=856 and 299+i*25<=y<=322+i*25:self.focus=i;self.advanced_key(13 if i==2 else 39);return
   if 751<=x<=791 and 374<=y<=395:self.flip_advanced(-1);return
   if 799<=x<=845 and 374<=y<=395:self.flip_advanced(1);return
   for i in range(len(LEVELS)+len(ROUTE_BOSSES)):
    col=0 if i<len(LEVELS) else 1;row=i if col==0 else i-len(LEVELS)
    if row//ADVANCED_PAGE_SIZE!=self.advanced_page:continue
    row%=ADVANCED_PAGE_SIZE
    if 249+col*304<=x<=541+col*304 and 399+row*15<=y<=413+row*15:self.focus=3+i;self.advanced_key(13);return
  elif self.page=='delete':
   if 255<=x<=525 and 530<=y<=578:self.focus=0;self.key(13)
   elif 550<=x<=850 and 530<=y<=578:self.focus=1;self.key(13)
  elif self.page=='targets':self.key(27)
 def open_advanced(self):
  if self.options['mode']=='target':self.open_extras();return
  self.page='advanced';self.focus=0;self.advanced_page=0
 def open_extras(self):
  self.extras_parent='advanced' if self.page=='advanced' else 'new'
  # Explicitly opening the page does not silently alter an imported old seed.
  self.page='extras';self.focus=0;self.message=''
 def extras_key(self,key):
  if key==27 or (key==13 and self.focus==len(EXTRAS)):
   self.page=self.extras_parent;self.focus=(len(LEVELS)+len(ROUTE_BOSSES)+4) if self.page=='advanced' else 7;return
  if key in (38,40,9):self.focus=(self.focus+(-1 if key==38 else 1))%(len(EXTRAS)+1)
  elif key in (13,32,37,39) and self.focus<len(EXTRAS):
   upgrade(self.options)
   name=EXTRAS[self.focus][0];self.options['extras'][name]=not self.options['extras'][name]
 def clipboard_access(self):
  if self.clipboard is None:
   from menu_clipboard import Clipboard
   self.clipboard=Clipboard()
  return self.clipboard
 def pump(self):
  if self.clipboard:self.clipboard.pump()
 def close(self):
  if self.clipboard:self.clipboard.close();self.clipboard=None
 def open_seed(self):
  try:self.seed_text=encode(self.seed,self.options)
  except ValueError as e:self.message=str(display(str(e)));return
  self.page='seed';self.focus=0;self.seed_selected=False;self.message='';self.dirty=True
 def seed_value(self,value):
  if not isinstance(value,str) or not value.strip().startswith('BR2-'):
   raise ValueError(tr('Bitte einen vollständigen geteilten Seed mit BR2- am Anfang einfügen.'))
  seed,options=decode(value)
  if options.get('route_version') not in (2,3,4,5):raise ValueError(tr('Dieser ältere Seed enthält keine Advanced-Route. Bestehenden Lauf über Fortsetzen laden.'))
  character(self.store.base,seed,options)
  return seed,options
 def paste_seed(self):
  try:
   value=self.clipboard_access().get()
   seed,options=self.seed_value(value)
   self.seed_text=encode(seed,options);self.seed_selected=False
   self.message=tr('Gültiger Seed. Übernehmen lädt auch seine Einstellungen.')
  except Exception as e:self.message=tr('Nicht eingefügt: ')+str(display(str(e)))
  self.dirty=True
 def import_seed(self,value):
  seed,options=self.seed_value(value)
  self.seed=seed;self.options=options;self.message=tr('Seed und Einstellungen übernommen.');self.dirty=True
 def seed_key(self,key):
  if key==27:self.page='new';self.focus=0;self.message='';return
  if key==4098:self.paste_seed();return
  if key==4099:
   self.copy_seed();return
  if key in (38,40,9):self.focus=(self.focus+(-1 if key==38 else 1))%6;return
  if self.focus==0:
   if key==4097:self.seed_selected=True;return
   if key in (8,46):
    self.seed_text='' if self.seed_selected or key==46 else self.seed_text[:-1];self.seed_selected=False;self.message='';return
  elif key in (37,39):self.focus=(self.focus+(-1 if key==37 else 1))%6;return
  if key!=13:return
  if self.focus in (0,4):
   try:self.import_seed(self.seed_text);self.page='new';self.focus=0
   except ValueError as e:self.message=str(display(str(e)))
  elif self.focus==1:
   # Keep the draft's imported settings when generating a new random seed.
   try:_,options=self.seed_value(self.seed_text)
   except ValueError:options=deepcopy(self.options)
   self.seed_text=encode(secrets.token_hex(4).upper(),options);self.seed_selected=False;self.message=tr('Neuer Seed erstellt. Mit Übernehmen bestätigen.')
  elif self.focus==2:self.copy_seed()
  elif self.focus==3:self.paste_seed()
  elif self.focus==5:self.seed_key(27)
 def copy_seed(self):
  try:
   seed,options=self.seed_value(self.seed_text);self.clipboard_access().put(encode(seed,options));self.message=tr('Seed mit allen Einstellungen kopiert.')
  except Exception as e:self.message=tr('Nicht kopiert: ')+str(display(str(e)))
 def open_characters(self):
  from character_cycle import roster
  self.character_names=['Auto']+[c['name'] for c in roster(self.store.base)]
  self.focus=self.character_names.index(self.options['start_character']);self.page='characters';self.message=''
 def character_key(self,key):
  if key==27:self.page='advanced';self.focus=2;return
  if key in (37,39,9):self.focus=(self.focus+(-1 if key==37 else 1))%len(self.character_names)
  elif key in (38,40):self.focus=(self.focus+(-7 if key==38 else 7))%len(self.character_names)
  elif key==13:self.options['start_character']=self.character_names[self.focus];self.page='advanced';self.focus=2
 def flip_advanced(self,delta):
  self.advanced_page=(self.advanced_page+delta)%ADVANCED_PAGES
  self.focus=3+self.advanced_page*ADVANCED_PAGE_SIZE
 def advanced_key(self,key):
  count=3+len(LEVELS)+len(ROUTE_BOSSES)
  if key==27:self.page='new';self.focus=7;return
  if key in (40,9,38):
   self.focus=(self.focus+(-1 if key==38 else 1))%(count+2)
   if 3<=self.focus<count:
    row=self.focus-3;row=row if row<len(LEVELS) else row-len(LEVELS);self.advanced_page=row//ADVANCED_PAGE_SIZE
   return
  if key not in (13,37,39,32):return
  if self.focus==count:self.page='new';self.focus=7;return
  if self.focus==count+1:self.open_extras();return
  delta=-1 if key==37 else 1
  if self.focus<2:
   name,pool=('level_count','level_pool') if self.focus==0 else ('route_boss_count','boss_pool')
   self.options[name]=(self.options[name]+delta)%(len(self.options[pool])+1)
  elif self.focus==2:self.open_characters()
  else:
   i=self.focus-3;pool='level_pool' if i<len(LEVELS) else 'boss_pool';values=list(LEVELS) if pool=='level_pool' else list(ROUTE_BOSSES);name=values[i if pool=='level_pool' else i-len(LEVELS)]
   if (pool=='level_pool' and name in NEW_LEVELS) or (pool=='boss_pool' and name in MINIBOSSES):self.options['route_version']=5
   elif (pool=='level_pool' and name not in LEGACY_LEVELS) or (pool=='boss_pool' and name in EXTRA_BOSSES):self.options['route_version']=max(4,self.options['route_version'])
   elif pool=='boss_pool' and name in ('questionmark','ridley'):self.options['route_version']=max(3,self.options['route_version'])
   selected=self.options[pool]
   if name in selected:selected.remove(name)
   else:selected.append(name)
   number='level_count' if pool=='level_pool' else 'route_boss_count';self.options[number]=min(self.options[number],len(selected))
  self.message=''
 def event(self,kind,a,b):
  if kind==4:
   if self.page!='slots':return
   self.select(a)
   if b==1:self.key(13)
   elif b==2:self.key(46)
   elif b==3:
    if not self.open_saved_result():self.page='targets'
  elif kind==1:self.key(a)
  elif kind==2:self.char(a)
  elif kind==3:self.click(a,b)

 def open_interval(self):
  seconds=self.options['extras'].get('shot_interval_seconds',300)
  self.interval_fields=[str(seconds//60),str(seconds%60)];self.interval_selected=True
  self.page='interval';self.focus=0;self.message=''
 def interval_key(self,key):
  if key==27 or (key==13 and self.focus==3):self.page='new';self.focus=8;self.message='';return
  if key in (9,38,40):self.focus=(self.focus+(-1 if key==38 else 1))%4;self.interval_selected=True;return
  if self.focus<2:
   if key in (8,46):self.interval_fields[self.focus]='' if self.interval_selected or key==46 else self.interval_fields[self.focus][:-1];self.interval_selected=False
   elif key in (37,39):self.interval_fields[self.focus]=str(max(0,min(1440 if self.focus==0 else 59,int(self.interval_fields[self.focus] or 0)+(-1 if key==37 else 1))));self.interval_selected=True
   elif key==13:self.focus+=1;self.interval_selected=True
  elif key==13:
   minutes,seconds=(int(v or 0) for v in self.interval_fields);total=minutes*60+seconds
   if seconds>59 or not 1<=total<=86400:self.message=tr('Sekunden: 0–59. Gesamtzeit: 1 Sekunde bis 24 Stunden.');return
   upgrade(self.options)['shot_interval_seconds']=total;self.page='new';self.focus=8;self.message=tr('Zeitgrenze übernommen.')
 def preset_key(self,key):
  if key==27 or (key==13 and self.focus==3):self.page='new';self.focus=9;return
  if key in (38,40,9):self.focus=(self.focus+(-1 if key==38 else 1))%4
  elif key==13:
   keep={k:self.options[k] for k in ('mode','target_count','boss_count')}
   self.options=dict(difficulty=1,levels=True,items=True,characters=False,**keep,**defaults(),extras=extra_defaults())
   if self.focus==1:self.options['characters']=True;self.options['extras'].update(shot_mode='death_and_spot',death_character=True)
   if self.focus==2:self.options['extras'].update(god_mode=True,one_hp=True,autofire=True,skip_intro=True,fast_chests=True)
   self.message=(tr('Standard'),tr('Chaos'),tr('Training'))[self.focus]+tr(' übernommen. Alles bleibt einzeln einstellbar.');self.page='new';self.focus=9
 def open_result(self,manifest):
  path=self.store.root/manifest['run_id']/'summary.json'
  if not path.exists():return False
  self.result=json.loads(path.read_text());self.result_manifest=manifest;self.page='result';self.focus=0;self.message='';self.dirty=True;return True
 def result_key(self,key):
  if key in (37,39,9,38,40):self.focus=1-self.focus
  elif key==27 or (key==13 and self.focus==1):self.page='slots';self.focus=0;self.action=('result_back',self.slot,None)
  elif key==13:
   self.reload();free=next((i for i in (1,2,3) if not self.saves[i]['exists']),None)
   if free is None:self.message=tr('Kein freier Slot. Zurück gehen und zuerst einen Spielstand löschen.');return
   self.slot=free;self.seed=self.result_manifest['seed'];self.options=deepcopy(self.result_manifest['options']);self.page='new';self.focus=6
   self.message=tr('Derselbe Seed mit denselben Einstellungen. Enter startet im freien Slot.');self.action=('result_back',self.slot,None)

 def open_saved_result(self):
  m=self.store.current(self.slot)
  return bool(m and m['status']=='ready' and self.open_result(m))
