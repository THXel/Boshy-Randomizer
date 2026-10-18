from ui_i18n import tr
"""Native menu transactions; all live writes require a game-thread lock."""
from contextlib import contextmanager
from types import SimpleNamespace
import struct,time,json
from native_session import atomic
from native_telemetry import NativeReader
from mixed_rewards import CONTEXT_SIZE
from intro_guard import extras_compatible

class LiveSession:
 def __init__(self,store,game):
  self.store=store;self.game=game;self.reader=NativeReader(SimpleNamespace(store=store,bridge=game.bridge));self.lock_run=None
 def command(self,op,slot=0,flags=0,payload=b''):
  sequence=time.monotonic_ns()&0xffffffff or 1
  data=struct.pack('<8I',0x42524c31,self.game.bridge.ready['pid'],sequence,op,slot,flags,len(payload),0)+payload
  atomic(self.store.base/'menu-runtime/session-command.bin',data)
  end=time.monotonic()+5
  while time.monotonic()<end:
   state=self.reader.read('SessionState',8)
   if state and state[1]==sequence and state[2]!=1:
    if state[2]:raise RuntimeError(tr('Nativer Laufwechsel abgelehnt: {0}',str(state[2])))
    return state
   time.sleep(.025)
  raise TimeoutError(tr('Nativer Laufwechsel wurde nicht bestätigt.'))
 def check(self):
  snap=self.game.bridge.snapshot();state=self.reader.read('SessionState',8)
  if self.lock_run is None or snap['scene']!=1 or snap['run']!=self.lock_run or not state or state[2]!=0 or state[3]!=1 or state[4]!=self.lock_run:raise RuntimeError(tr('Hauptmenü ist nicht für den Laufwechsel gesperrt.'))
 @contextmanager
 def transaction(self):
  if getattr(self.store,'_menu_guard',None) is not None:raise RuntimeError(tr('Laufwechsel bereits aktiv.'))
  self.game.write(60,2)
  try:
   state=self.command(1);self.lock_run=state[4];self.store._menu_guard=self.check
   self.check();yield self;self.check()
  finally:
   self.store._menu_guard=None
   if self.lock_run is not None:
    self.command(3);self.lock_run=None
 def compatible(self,m):
  from runtime_versions import Rules
  r=Rules(self.store,m)
  if 'extras' not in m['options']:return False
  off=json.loads((r.base/'slot_reward_extras_symbols.json').read_text(encoding='utf-8'))['context_offset']
  blob=(r.base/'slot_reward_extras.bin').read_bytes()
  return self.game.metadata['context']-self.game.metadata['hook']==off and self.game.bridge.read(self.game.metadata['hook'],off)==blob[:off] and extras_compatible(self.store.base,r.base)
 def bind(self,m):
  self.check()
  from launch_slot_reward import prepare_payload
  payload,offset=prepare_payload(self.store,m);blob=payload.read_bytes()
  # Preserve the original injected dispatcher and DLL ABI. Old incompatible
  # frozen runs require the existing cold-start path, never a guessed upgrade.
  from runtime_versions import Rules
  r=Rules(self.store,m)
  if 'extras' not in m['options'] or self.game.metadata['context']-self.game.metadata['hook']!=offset or self.game.bridge.read(self.game.metadata['hook'],offset)!=blob[:offset]:raise RuntimeError(tr('Lauf benötigt einen anderen nativen Patch.'))
  if not extras_compatible(self.store.base,r.base):raise RuntimeError(tr('Lauf benötigt eine andere Extras-Version.'))
  context=blob[offset:offset+CONTEXT_SIZE];menu=offset+CONTEXT_SIZE
  self.command(2,m['slot'],struct.unpack_from('<I',blob,menu+32)[0],context+blob[menu+2124:menu+2136]);self.check()
  if self.game.bridge.read(self.game.metadata['context']+64,32)!=m['run_id'].encode():raise RuntimeError(tr('Laufkennung wurde nicht übernommen.'))
  self.verify_profile()
  from lab import ini_items,ini_object_ids
  ids=ini_object_ids(self.game.bridge)
  if ini_items(self.game.bridge,'randochecks',ids['Ini++']).get('sessionid',{}).get('value')!=m['run_id']:raise RuntimeError(tr('Spielstand wurde nicht neu eingelesen.'))
 def clear(self):self.check();self.command(5)
 def verify_profile(self):
  from lab import ini_items,ini_object_ids
  from PY.ini_utils import parse_ini
  self.game.bridge._ini_cache=None
  profile=parse_ini(self.store.read_save(self.store.base/'IWBTB/onlineLicense.ini'))
  oi=ini_object_ids(self.game.bridge)['Ini++ 3']
  for group in ('license','unlockables','randoprofile'):
   try:actual={k:v['value'] for k,v in ini_items(self.game.bridge,group,oi).items()}
   except KeyError:actual={}
   expected={k.casefold():str(v) for k,v in profile.get(group,{}).items()}
   if actual!=expected:raise RuntimeError(tr('Charakterprofil wurde nicht vollständig neu eingelesen.'))
 def reload(self,slot=0):
  self.check();self.command(4,slot);self.verify_profile()
