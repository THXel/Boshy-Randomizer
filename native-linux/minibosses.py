"""Read native player coordinates and Kracko health; never sample screen pixels."""
import hashlib,struct,time

REGIONS={'kracko':(3200,0,3840,480),'ninja_ryu':(4480,0,5120,480),'gravitron':(2560,1440,3200,1920)}
RYU_EXIT=(5120,0,5760,480)
PLAYER_OI={5:358,11:358,31:93}
# Filled from the original event bank in the inspected executable.
KRACKO_EVENT_OFFSET=329818
KRACKO_EVENT_SIZE=148
KRACKO_EVENT_HASH='f58e84604ce23fb0095ef30d95f359cffe318fad8ff01e26ddd1fa40f829a024'

def inside(position,region):
 return bool(position is not None and region[0]<=position[0]<region[2] and region[1]<=position[1]<region[3])

class Reader:
 def __init__(self):self.identity=None;self.refs={};self.tick=None;self.scanned=None
 def sample(self,bridge,snap):
  frame=snap['scene']+1
  if frame not in PLAYER_OI:return None
  identity=(frame,snap['run'],snap['object_list'])
  if identity!=self.identity or self.tick is None or snap['frame_count']<self.tick:
   self.identity=identity;self.refs={};self.scanned=None
   if frame==5:
    bank=struct.unpack('<I',bridge.read(snap['run']+0x88,4))[0]
    if hashlib.sha256(bridge.read(bank+KRACKO_EVENT_OFFSET,KRACKO_EVENT_SIZE)).hexdigest()!=KRACKO_EVENT_HASH:raise RuntimeError('Unbekannte Kracko-Todesbedingung.')
  self.tick=snap['frame_count']
  def present(name):
   obj=self.refs.get(name)
   if not obj:return None
   if struct.unpack('<I',bridge.read(snap['object_list']+obj['slot']*8,4))[0]!=obj['ptr']:return None
   raw=bridge.read(obj['ptr'],132)
   return raw if struct.unpack_from('<H',raw,18)[0]==obj['oi'] and struct.unpack_from('<h',raw,24)[0]==2 and struct.unpack_from('<h',raw,0)[0]==obj['handle'] else None
  player=present('player');boss=present('boss') if frame==5 else None
  if self.scanned is None or ((player is None or (frame==5 and boss is None)) and self.tick-self.scanned>=10):
   from lab import objects
   self.scanned=self.tick;self.refs={}
   for obj in objects(bridge):
    if obj['type']!=2:continue
    if obj['oi']==PLAYER_OI[frame]:self.refs['player']=obj
    elif frame==5 and obj['oi']==464:self.refs['boss']=obj
   player=present('player');boss=present('boss') if frame==5 else None
  result=dict(frame=frame,tick=snap['frame_count'],player_alive=player is not None,position=None,hp=None,boss_object=None)
  if player:result['position']=[struct.unpack_from('<i',player,76)[0],struct.unpack_from('<i',player,84)[0]]
  if boss:
   ptr=self.refs['boss']['ptr'];relative=struct.unpack_from('<I',boss,128)[0]
   if not 128<=relative<4096:raise RuntimeError('Ungültige Kracko-Werte.')
   values=struct.unpack('<I',bridge.read(ptr+relative,4))[0];health=bridge.read(values+16,16)
   if struct.unpack_from('<I',health)[0]!=0:raise RuntimeError('Unbekanntes Kracko-Lebenspunkteformat.')
   result.update(hp=struct.unpack_from('<i',health,8)[0],boss_object=ptr)
   if not -1000<=result['hp']<=10000:raise RuntimeError('Ungültige Kracko-Lebenspunkte.')
  after=bridge.snapshot()
  if (after['scene'],after['run'],after['object_list'])!=(snap['scene'],snap['run'],snap['object_list']) or after['frame_count']<snap['frame_count']:raise RuntimeError('Scene changed during observation')
  return result

class Gate:
 def __init__(self):self.reset()
 def reset(self):
  self.identity=None;self.armed=False;self.candidate=None;self.since=None;self.deaths=None;self.tick=None;self.previous=None;self.boss_object=None
 def snapshot(self):
  return dict(version=1,identity=list(self.identity) if self.identity else None,armed=self.armed,candidate=self.candidate,deaths=self.deaths,previous=self.previous,boss_object=self.boss_object)
 def restore(self,data):
  self.reset()
  if not data or data.get('version')!=1:return
  self.identity=tuple(data['identity']) if data.get('identity') else None
  for key in ('armed','candidate','deaths','previous','boss_object'):setattr(self,key,data.get(key))
  if self.candidate:self.since=time.monotonic()
 def observe(self,spot,index,point,sample,deaths,now=None):
  now=time.monotonic() if now is None else now;segment=point.get('segment')
  if segment not in ('before_kracko','before_ninja_ryu','before_gravitron','kracko','ninja_ryu'):
   self.reset();return None
  identity=(spot,index,segment)
  if not sample or sample.get('frame')!=point['frame'] or not sample.get('player_alive'):
   self.reset();return None
  tick=sample['tick'];position=sample.get('position')
  if identity!=self.identity or (self.deaths is not None and deaths!=self.deaths) or (self.tick is not None and tick<self.tick):self.reset();self.identity=identity
  self.deaths=deaths;self.tick=tick
  valid=False;reason=None
  if segment.startswith('before_'):
   region=REGIONS[segment[7:]]
   if not inside(position,region):self.armed=True
   valid=inside(position,region) and self.armed;reason='Miniboss-Eingang'
  elif segment=='ninja_ryu':
   if inside(position,REGIONS['ninja_ryu']):self.armed=True
   valid=self.armed and inside(position,RYU_EXIT) and (self.candidate is not None or inside(self.previous,REGIONS['ninja_ryu']))
   reason='Ryu-Passage verlassen'
  elif segment=='kracko':
   obj=sample.get('boss_object');hp=sample.get('hp')
   if obj is not None and self.boss_object not in (None,obj):self.armed=False;self.candidate=None;self.since=None
   if obj is not None:self.boss_object=obj
   if hp is not None and hp>0:self.armed=True
   valid=self.armed and inside(position,REGIONS['kracko']) and ((hp is not None and hp<=0) or (self.candidate is not None and obj is None))
   reason='Kracko besiegt'
  self.previous=position
  if not valid:self.candidate=None;self.since=None;return None
  if self.candidate is None:self.candidate=reason;self.since=now
  # Native outside -> inside samples already prove a screen crossing.
  # Do not wait for another slow inventory poll while a miniboss can attack.
  return reason if segment!='kracko' or now-self.since>=1.0 else None


def prepare_pool(pool,options):
 # Metadata is bound into each new manifest; old seeds retain their old stages.
 if options.get('route_version',1)<5:return pool
 segments={'save2.ini':'before_kracko','boss2.ini':'kracko','save23.ini':'after_kracko',
           'save13.ini':'before_ninja_ryu','boss16.ini':'ninja_ryu','save22.ini':'after_ninja_ryu',
           'save4.ini':'before_gravitron','boss7.ini':'gravitron'}
 labels={'save2.ini':'Green Greens · vor Kracko','boss2.ini':'Kracko','save23.ini':'Green Greens · nach Kracko','save13.ini':'Ninja Gaiden · vor Ryu','boss16.ini':'Ryu (Ausweichen)','save22.ini':'Ninja Gaiden · nach Ryu','save4.ini':'VVVVVV · vor Gravitron','boss7.ini':'Gravitron'}
 return {name:dict(point,segment=segments[name],label=labels[name]) if name in segments else point for name,point in pool.items()}
