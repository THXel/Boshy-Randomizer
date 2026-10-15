"""Arm only already established room-exit rules; no new trigger positions."""
import struct
MAGIC=0x42584531
class FastExit:
 def __init__(self,player):self.player=player;self.armed=None
 def control(self):
  return struct.unpack('<4I',self.player.bridge.read(self.player.metadata['menu']+2144,16))
 def command(self,scene,op,exits=()):
  mask=sum(1<<(f-1) for f in exits)
  return self.player.bridge.cmd(f"exit {self.player.metadata['menu']:x} {scene} {op} {mask&0xffffffff} {mask>>32}").get('written',False)
 def allowed(self,frame):
  p=self.player;d=p.progress.data;spot=d.get('trigger_spot',d['spot']);point=p.m['pool'].get(spot);g=p.progress.gate
  if (not p.m['options']['levels'] or not point or d['pending'] or d['spot'] in ('boss_solgryn.ini','boss23.ini') or point['frame']==51 or p.watch.down or p.watch.pressed.is_set()):return ()
  mod=p.rules.module('native_triggers')
  if getattr(mod,'RULE_VERSION',0)!=3 or not hasattr(mod,'stage_frames'):return ()
  spot='save1.ini' if spot.startswith('prehistorik_') else spot
  if not g.seen_origin or frame not in mod.stage_frames(spot,point) or g.identity!=(spot,point['frame']):return ()
  return mod.exits_for(spot,point)
 def arm(self,frame,stats):
  p=self.player;c=self.control()
  if c[0]!=MAGIC:return
  if c[3]>=256:return
  exits=self.allowed(frame)
  identity=(p.progress.data['index'],p.progress.data['spot'],frame,int(stats.get('deaths',0)),tuple(exits))
  if exits:
   if self.armed!=identity or c[3]!=1:
    if self.command(frame-1,1,exits):self.armed=identity
  elif c[3]==1:self.command(frame-1,0);self.armed=None
 def captured(self,frame,stats):
  c=self.control()
  if c[0]!=MAGIC or c[3]<256:return None
  target=c[3]-256+1;p=self.player;d=p.progress.data
  valid=(self.armed and self.armed[:4]==(d['index'],d['spot'],frame,int(stats.get('deaths',0))) and target in self.armed[4] and not p.watch.down and not p.watch.pressed.is_set())
  if not valid:self.command(frame-1,2);self.armed=None;return None
  return target
 def release(self,frame,committed=False):
  self.command(frame-1,3 if committed else 2);self.armed=None
 def request(self,target,collectables,stats):
  p=self.player;d=p.progress.data;active=d.get('trigger_spot',d['spot']);point=p.m['pool'][active]
  reason='Boss-Ausgang' if point['category']=='bosses' else 'Level-Ausgang'
  # Preserve the existing save-local completion receipts for optional bosses.
  mod=p.rules.module('beta_catalogue')
  key=next((k for k,v in mod.BOSSES.items() if v[2]==active),None)
  if point['category']=='bosses' and key in mod.RECEIPT_BOSSES and p.m['options'].get('route_version',1)>=4:
   import time
   d.setdefault('stage_bosses',{}).setdefault(key,dict(time=time.time(),frame=target,index=d['index'],exit=reason))
  p.progress.trace('native-exit-captured',frame=self.armed[2],exit_frame=target)
  return p.progress.request(collectables,target,reason,stats)
