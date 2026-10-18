"""Reject unlisted Teleport Room exits without advancing or rerolling a run."""
from lab import transition,IniReadInProgress
from transition_guard import protect
HUB=29
# Frame 64 is outside this game's route table; the native hook uses this bit
# only as a notice flag. It is never considered a captured destination.
NOTICE_FLAG=64

class HubGuard:
 def __init__(self,player):self.player=player
 def context(self):
  p=self.player;d=p.progress.data;spot=d.get('trigger_spot',d['spot']);point=p.m['pool'].get(spot)
  if not p.m['options'].get('levels') or d.get('pending') or not point:return None
  mod=p.rules.module('native_triggers')
  if getattr(mod,'RULE_VERSION',0)!=3:return None
  key='save1.ini' if spot.startswith('prehistorik_') else spot
  if HUB in mod.exits_for(key,point):return None
  return dict(index=d['index'],spot=spot,frames=mod.stage_frames(key,point))
 def checkpoint(self):
  c=self.context();saved=self.player.progress.data.get('hub_checkpoint')
  if not c or not saved or any(saved.get(k)!=c[k] for k in ('index','spot')):return None
  if saved.get('frame') not in c['frames'] or saved['frame'] in (1,2,9,21,HUB):return None
  if any(type(saved.get(k)) is not int for k in ('frame','xpos','ypos')):return None
  return saved
 def remember(self,frame,live,disk,settled):
  c=self.context();p=self.player
  if not c or not settled or frame not in (*c['frames'],HUB) or live!=disk or live.get('frame') not in c['frames']:return
  if any(type(live.get(k)) is not int for k in ('frame','xpos','ypos')):return
  saved={k:live[k] for k in ('frame','xpos','ypos')};saved.update(index=c['index'],spot=c['spot'])
  if p.progress.data.get('hub_checkpoint')!=saved:
   p.progress.data['hub_checkpoint']=saved;p.progress.save()
 def intercept(self,frame):
  c=self.context()
  return bool(c and frame in c['frames'] and self.checkpoint())
 def restore(self,frame,captured=None):
  p=self.player;d=p.progress.data;c=self.context();saved=self.checkpoint()
  pending=d.get('hub_return')
  if not c or not saved:return False
  if pending and any(pending.get(k)!=c[k] for k in ('index','spot')):
   d.pop('hub_return',None);p.progress.save();pending=None
  if not pending and frame!=HUB and captured!=HUB:return False
  if p.watch.down or not p.can_transition():raise IniReadInProgress('Waiting to restore forbidden portal')
  if not pending:
   d['hub_return']=dict(saved);p.progress.trace('forbidden-hub',frame=frame,captured=captured,checkpoint=dict(saved));p.progress.save()
  else:saved=pending
  with protect(p.bridge,p.metadata['menu']):
   # Suppress replay of the intercepted portal before resetting to the saved
   # checkpoint. The usual route request/arrival path would advance the seed.
   p.fast_exit.release(frame,committed=True)
   transition(p.bridge,saved['frame'],saved['xpos'],saved['ypos'],p.save_name,stabilize=True)
  p.progress.gate.reset();p.progress.pause()
  d['completion_gate']=p.progress.gate.snapshot();d['miniboss_gate']=p.progress.mini_gate.snapshot()
  d.pop('hub_return',None)
  p.progress.rebase(saved['frame'],(saved['xpos'],saved['ypos']))
  p.progress.trace('forbidden-hub-restored',checkpoint=dict(saved));p.progress.save()
  p.watch.pressed.clear();p.watch.ready.clear()
  # Restart the observation with fresh scene objects; the host already treats
  # this as a transient read, not as a crash or a new route step.
  raise IniReadInProgress('Checkpoint restored after forbidden portal')
