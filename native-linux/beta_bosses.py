"""Read-only native beta-boss health observation and per-attempt victory gate."""
import struct,time
from beta_catalogue import BETA
SPECS={44:('questionmark',2372),45:('ridley',2380)}

class Reader:
 def __init__(self):self.identity=None;self.refs={};self.last_tick=None;self.scanned_tick=None
 def sample(self,bridge,snap):
  frame=snap['scene']+1
  if frame not in SPECS:return None
  key,oi=SPECS[frame];bank=struct.unpack('<I',bridge.read(snap['run']+0x88,4))[0];identity=(snap['run'],frame,bank)
  if self.identity!=identity or self.last_tick is None or snap['frame_count']<self.last_tick:
   self.identity=identity;self.refs={};self.scanned_tick=None
   # Original victory event: compare this boss's alterable value D to zero.
   event=bridge.read(bank+230842,330)
   if struct.unpack_from('<h',event)[0]!=-330 or event[2:4]!=b'\x03\x01' or struct.unpack_from('<HhhH',event,14)!=(46,2,-27,oi) or struct.unpack_from('<HH',event,32)!=(50,3) or b'Randomness\0' not in event:raise RuntimeError('Unbekannte Beta-Boss-Todesbedingung.')
  if self.scanned_tick is None or (('boss' not in self.refs or 'player' not in self.refs) and snap['frame_count']-self.scanned_tick>=10):
   self.scanned_tick=snap['frame_count']
   from lab import objects
   for obj in objects(bridge):
    if obj['type']!=2:continue
    if obj['oi']==oi:self.refs['boss']=obj
    meta=struct.unpack_from('<I',bytes.fromhex(obj['raw']),28)[0]
    if bridge.read(meta+90,24).split(b'\0')[0]==b'Player':self.refs['player']=obj
  self.last_tick=snap['frame_count']
  def present(kind):
   obj=self.refs.get(kind)
   if not obj:return None
   pointer=struct.unpack('<I',bridge.read(snap['object_list']+obj['slot']*8,4))[0]
   if pointer!=obj['ptr']:return None
   raw=bridge.read(pointer,132)
   return raw if struct.unpack_from('<H',raw,18)[0]==obj['oi'] and struct.unpack_from('<h',raw,24)[0]==2 else None
  raw=present('boss');player=present('player');result=dict(key=key,frame=frame,tick=snap['frame_count'],player_alive=player is not None,hp=None)
  if raw:
   pointer=self.refs['boss']['ptr'];relative=struct.unpack_from('<I',raw,128)[0]
   if not 128<=relative<4096:raise RuntimeError('Ungültige Beta-Boss-Werte.')
   value_array=struct.unpack('<I',bridge.read(pointer+relative,4))[0];health=bridge.read(value_array+48,16)
   if struct.unpack_from('<I',health)[0]!=0:raise RuntimeError('Unbekanntes Lebenspunkteformat.')
   phase=bridge.read(value_array,16)
   if struct.unpack_from('<I',phase)[0]!=0:raise RuntimeError('Unbekannter Beta-Intro-Zustand.')
   phase=struct.unpack_from('<i',phase,8)[0]
   result.update(intro_phase=phase,intro_active=phase<780,hp=struct.unpack_from('<i',health,8)[0],flags=struct.unpack('<I',bridge.read(pointer+relative+104,4))[0],object=pointer)
  after=bridge.snapshot()
  if (after['scene'],after['run'],after['object_list'])!=(snap['scene'],snap['run'],snap['object_list']) or after['frame_count']<snap['frame_count']:raise RuntimeError('Scene changed during observation')
  if result['hp'] is not None and not -1000<=result['hp']<=1000:raise RuntimeError('Ungültige Beta-Boss-Lebenspunkte.')
  return result

class Gate:
 def __init__(self,allow_fast=None):
  self.allow_fast=getattr(self,"allow_fast",False) if allow_fast is None else allow_fast
  self.intro_alive=False;self.identity=None;self.armed=False;self.since=None;self.deaths=None;self.tick=None;self.object=None;self.state={}
 def observe(self,spot,index,sample,deaths,now=None):
  now=time.monotonic() if now is None else now
  if not sample or sample.get('key') not in BETA:
   self.__init__();return False
  key=sample['key'];identity=(spot,index,key);hp=sample.get('hp');tick=sample['tick']
  if spot!=BETA[key][2] or sample.get('frame')!=BETA[key][1]:
   self.__init__();return False
  reset=(identity!=self.identity or self.deaths!=deaths or (self.tick is not None and tick<self.tick) or (self.object is not None and sample.get('object') not in (None,self.object)))
  if reset:self.identity=identity;self.armed=False;self.since=None;self.intro_alive=False
  self.deaths=deaths;self.tick=tick;self.object=sample.get('object')
  if not sample['player_alive']:self.armed=False;self.since=None;self.intro_alive=False
  elif sample.get('intro_active'):
   self.armed=False;self.since=None
   if hp is not None and hp>0:self.intro_alive=True
  elif hp is not None and hp>0:self.armed=True;self.since=None
  elif (self.armed or (self.allow_fast and (self.intro_alive or (sample.get('intro_phase',0)>=780 and sample.get('flags',0)&1)))) and hp is not None and hp<=0:
   if self.since is None:self.since=now
  else:self.since=None
  self.state=dict(key=key,intro_active=sample.get('intro_active',False),armed=self.armed,death_seen=self.since is not None,player_alive=sample['player_alive'],hp=hp,deaths=deaths)
  return self.since is not None and now-self.since>=1.5
