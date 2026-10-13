"""Durable, run-bound chest receipts and stopped-game reconciliation.

The native pickup hook commits one receipt BEFORE invoking either original setter.
Receipts are monotonic; reapplying boolean ownership and a source marker is idempotent.
Only the stopped controller repairs saves. Live observation never overwrites game files.
"""
import json,struct,time,uuid
from pathlib import Path
from native_session import atomic,write_json,digest,section
from native_models import ini
from PY.ini_utils import parse_ini

class RewardStorageError(RuntimeError):pass
class ForeignSaveError(RewardStorageError):pass

def parsed(text):
 return {g:{k.casefold():v for k,v in values.items()} for g,values in parse_ini(text).items()}
def folder(store,m):return store.root/m['run_id']/'rewards'
def rows(store):return json.loads((store.base/'slot_reward_plan.json').read_text())['locations']
def fnv(data):
 h=2166136261
 for byte in data:h=((h^byte)*16777619)&0xffffffff
 return h
def receipt(m,key):
 raw=b'BRW1'+m['run_id'].encode('ascii')+key.lower().encode('ascii').ljust(8,b'\0')
 return raw+struct.pack('<I',fnv(raw))
def claims(store,m):
 out=[];root=folder(store,m);known={r['key'].lower():r['key'] for r in rows(store)}
 for p in sorted(root.glob('*.wal')):
  key=known.get(p.stem)
  if key is None or p.is_symlink() or p.read_bytes()!=receipt(m,key):raise RewardStorageError('Vergabeprotokoll beschädigt oder einem anderen Lauf zugeordnet; nichts überschrieben.')
  out.append(key)
 return out

def load_checkpoint(store,m):
 p=folder(store,m)/'checkpoint.json'
 try:
  envelope=json.loads(p.read_text());data=envelope['data']
  if envelope['sha256']!=digest(json.dumps(data,sort_keys=True).encode()):raise ValueError('checksum')
  if (data['version'],data['run_id'],data['binding'],data['slot'])!=(1,m['run_id'],m['session_binding'],m['slot']):raise ValueError('identity')
  validate_save(store,m,data['save']);validate_profile(data['profile'])
  return data
 except (OSError,ValueError,KeyError,TypeError) as e:raise RewardStorageError('Sicherung der Belohnungen fehlt oder ist beschädigt; Lauf nicht überschrieben.') from e

def checkpoint(store,m,save,profile):
 data=dict(version=1,run_id=m['run_id'],binding=m['session_binding'],slot=m['slot'],save=save,profile=profile)
 write_json(folder(store,m)/'checkpoint.json',dict(data=data,sha256=digest(json.dumps(data,sort_keys=True).encode())))

def validate_save(store,m,text,baseline=None):
 d=parsed(text);c=d.get('randochecks',{})
 if c.get('sessionid') not in (None,m['run_id']) or c.get('sessionbinding') not in (None,m['session_binding']) or c.get('slot') not in (None,str(m['slot'])):raise ForeignSaveError('Anderer Spielstand im Slot; Wiederherstellung abgebrochen.')
 # A readable ordinary save without our identity is not assumed to be corruption.
 if d and 'randochecks' not in d:raise ForeignSaveError('Nicht zugeordneter Spielstand; Wiederherstellung abgebrochen.')
 if c.get('sessionid')!=m['run_id'] or c.get('sessionbinding')!=m['session_binding'] or c.get('slot')!=str(m['slot']):raise ValueError('save binding incomplete')
 for r in rows(store):
  if c.get(r['key'].lower()) not in ('0','1'):raise ValueError('check incomplete')
 for g,keys in {'check':['saveversion'],'stats':['deaths','difficulty','timeseconds'],'positions':['frame','xpos','ypos'],'collectables':['awesomesauce','gastly','scouter','timer','cake']}.items():
  for k in keys:
   if k not in d.get(g,{}):raise ValueError('save incomplete')
 if baseline:
  for g,values in parsed(baseline).items():
   if any(k not in d.get(g,{}) for k in values):raise ValueError('save truncated')
 return d

def validate_profile(text,baseline=None):
 d=parsed(text)
 if not {'character','charactername'}<=d.get('license',{}).keys() or 'unlockables' not in d:raise ValueError('profile incomplete')
 if baseline:
  expected=parsed(baseline).get('randoprofile',{})
  actual=d.get('randoprofile',{})
  if any(k in actual and actual[k]!=v for k,v in expected.items()):raise ForeignSaveError('Charakterprofil gehört zu einem anderen Lauf.')
  for g,values in parsed(baseline).items():
   if any(k not in d.get(g,{}) for k in values):raise ValueError('profile truncated')
 return d

def stable_read(store,path):
 a=path.read_bytes();text=store.read_save(path)
 if not text or a!=path.read_bytes():raise ValueError('save being written')
 return text

def initialize(store,m):
 store._stopped();root=folder(store,m);root.mkdir()
 save=stable_read(store,store.base/'IWBTB'/f"SaveFile{m['slot']}.ini");profile=stable_read(store,store.root/m['run_id']/'profile.ini')
 validate_save(store,m,save);validate_profile(profile);checkpoint(store,m,save,profile)

def set_flag(text,group,key):
 data=parse_ini(text);values=data.get(group.lower(),{});actual=next((k for k in values if k.casefold()==key.casefold()),key)
 if values.get(actual)=='1':return text
 values[actual]='1';return section(text,group,values)

def reconcile(store,m,*,active_profile=False):
 """Replay earned rewards with the game stopped; retain all unrelated valid data."""
 store._stopped();store.validate_binding(m)
 current=store.current(m['slot'])
 if m['status']!='ready' or not current or current['run_id']!=m['run_id']:raise ForeignSaveError('Lauf ist nicht mehr im angegebenen Slot aktiv.')
 baseline=load_checkpoint(store,m);earned=claims(store,m)
 sp=store.base/'IWBTB'/f"SaveFile{m['slot']}.ini";pp=store.base/'IWBTB/onlineLicense.ini' if active_profile else store.root/m['run_id']/'profile.ini'
 if active_profile:
  from native_profiles import lease
  j=lease(store)
  if not j or j['phase']!='active' or j['run_id']!=m['run_id'] or j['slot']!=m['slot']:raise ForeignSaveError('Charakterprofil ist nicht diesem Lauf zugeordnet.')
 def read(path,kind):
  try:
   text=stable_read(store,path)
   if kind=='save':validate_save(store,m,text,baseline[kind])
   else:validate_profile(text,baseline[kind])
   return text
  except ForeignSaveError:raise
  except (OSError,ValueError):return baseline[kind]
 save,profile=read(sp,'save'),read(pp,'profile')
 for key in earned:
  reward=m['rewards'][key]
  if reward['kind']=='item':save=set_flag(save,'Collectables',reward['name'])
  else:profile=set_flag(profile,'Unlockables',reward['name'])
  save=set_flag(save,'RandoChecks',key)
 # Save the complete repair BEFORE touching either game file. A second interruption
 # reuses the same receipts/checkpoint and cannot turn one receipt into two rewards.
 checkpoint(store,m,save,profile)
 for path,text in ((sp,save),(pp,profile)):
  data=store.encode_save(text);old=path.read_bytes() if path.exists() else None
  if old==data:continue
  backups=folder(store,m)/'repair-backups';backups.mkdir(exist_ok=True)
  if old is not None:atomic(backups/(uuid.uuid4().hex+'-'+path.name),old)
  atomic(path,data)
  if path.read_bytes()!=data:raise RewardStorageError('Wiederherstellung konnte nicht bestätigt werden; Vergabeprotokoll bleibt erhalten.')
 return earned

class Observer:
 def __init__(self,store,m):self.store=store;self.m=m;self.last=0.;self.incomplete=None
 def poll(self):
  now=time.monotonic()
  if now-self.last<.4:return
  self.last=now;baseline=load_checkpoint(self.store,self.m);earned=claims(self.store,self.m)
  try:
   save=stable_read(self.store,self.store.base/'IWBTB'/f"SaveFile{self.m['slot']}.ini")
   profile=stable_read(self.store,self.store.base/'IWBTB/onlineLicense.ini')
   d=validate_save(self.store,self.m,save,baseline['save']);p=validate_profile(profile,baseline['profile'])
   for key in earned:
    r=self.m['rewards'][key];values=d.get('collectables',{}) if r['kind']=='item' else p.get('unlockables',{})
    if values.get(r['name'].lower())!='1' or d['randochecks'][key.lower()]!='1':raise ValueError('pending award')
   checkpoint(self.store,self.m,save,profile);self.incomplete=None
  except ForeignSaveError:raise
  except (OSError,ValueError) as e:
   if self.incomplete is None:self.incomplete=now
   if now-self.incomplete>2:raise RewardStorageError('Belohnung nicht vollständig gespeichert. Lauf wird zur gesicherten Wiederherstellung angehalten.') from e

def recover_all(store):
 store._stopped()
 from native_profiles import lease
 if lease(store):raise RewardStorageError('Aktives Profil muss zuerst wiederhergestellt werden.')
 for slot in (1,2,3):
  m=store.current(slot)
  if m and m['status']=='ready':reconcile(store,m)
