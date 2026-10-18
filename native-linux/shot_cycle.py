"""Seeded projectile cosmetics, independent of character ownership and hitboxes."""
import hashlib,json,struct,time
from native_session import write_json
from character_cycle import roster

def selection(base,seed,index,previous=None):
 pool=sorted((c for c in roster(base) if 12<=c['id']<=152 and c['id']%4==0),key=lambda c:c['id'])
 pool=[c for c in pool if (c['id']-12)//4!=previous] or pool
 def score(c):return hashlib.sha256(f'{seed}\0shot-style-v1\0{index}\0{c["id"]}'.encode()).digest()
 c=min(pool,key=score)
 return dict(name=c['name'],frame=(c['id']-12)//4)
def interval(seed,index,maximum=300):
 return 1+int.from_bytes(hashlib.sha256(f'{seed}\0shot-interval-v1\0{index}'.encode()).digest()[:8],'little')%maximum
def initial(base,m):return selection(base,m['seed'],0)
TRANSPORT_VERSION=1

class ShotCycle:
 def __init__(self,store,m,clock=time.monotonic):
  self.store=store;self.m=m;self.clock=clock;self.path=store.root/m['run_id']/'shot-style.json';self.mode=m['options']['extras']['shot_mode']
  self.maximum=m['options']['extras'].get('shot_interval_seconds',300)
  self.data=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else dict(run_id=m['run_id'],binding=m['session_binding'],sequence=0,style=initial(store.base,m),remaining=float(interval(m['seed'],0,self.maximum)),deaths=None,spot=None)
  if self.data['run_id']!=m['run_id'] or self.data['binding']!=m['session_binding']:raise ValueError('Schussstil-Verlauf gehört zu anderem Lauf.')
  self.last=None;self.saved=self.clock()
 def save(self):write_json(self.path,self.data);self.saved=self.clock()
 def pause(self):self.last=None;self.save()
 def observe(self,stats,spot,bridge,menu):
  now=self.clock();elapsed=0 if self.last is None else max(0,now-self.last);self.last=now
  # A disconnected process or a suspended worker must not consume offline time.
  if elapsed>5:elapsed=0
  deaths=int(stats.get('deaths',0));old_deaths=self.data['deaths'];old_spot=self.data['spot']
  death=old_deaths is not None and deaths>old_deaths
  moved=old_spot is not None and spot!=old_spot
  self.data.update(deaths=deaths,spot=spot)
  changed=False
  if self.mode=='random_interval':
   self.data['remaining']-=elapsed
   while self.data['remaining']<=0:
    self.advance();self.data['remaining']+=interval(self.m['seed'],self.data['sequence'],self.maximum);changed=True
  elif (death and self.mode in ('death','death_and_spot')) or (moved and self.mode in ('spot','death_and_spot')):
   self.advance();changed=True
  if changed or old_deaths is None or now-self.saved>=2:self.save()
  # Shared control lives in the unused command padding, never in game profile data.
  # Character changes clear this padding; safely reapply it on the next poll.
  payload=bytearray(bridge.read(menu+1648,512));request,done=struct.unpack_from('<II',payload)
  if request!=done:return
  control=struct.pack('<III',0x42534531,self.data['style']['frame'],self.data['sequence'])
  if payload[476:488]!=control:
   if not bridge.cmd(f"shots {menu:x} {self.data['style']['frame']} {self.data['sequence']}").get('written'):raise RuntimeError('Nativer Schussstil konnte nicht gesetzt werden.')
   if bridge.read(menu+2124,12)!=control:raise RuntimeError('Nativer Schussstil wurde nicht bestätigt.')
 def advance(self):
  self.data['sequence']+=1
  self.data['style']=selection(self.store.base,self.m['seed'],self.data['sequence'],self.data['style']['frame'])
