"""Durable native checkpoint routing and save-local completion; no screen reads."""
import hashlib,json,time
from native_session import write_json
from native_level_route import eligible
from beta_catalogue import is_target,goals,confirmed,BOSSES

class Progress:
 def __init__(self,store,m):
  self.store=store;self.m=m;self.folder=store.root/m['run_id'];self.path=self.folder/'progress.json'
  self.data=json.loads(self.path.read_text(encoding='utf-8')) if self.path.exists() else dict(run_id=m['run_id'],binding=m['session_binding'],index=0,limit=10,spot='save1.ini',pending=None,baseline=None,history=[],solgryn_armed=False)
  if self.data['run_id']!=m['run_id'] or self.data['binding']!=m['session_binding']:raise ValueError('Route gehört zu einem anderen Lauf.')
  self.goals=goals(store.base,m['seed'],m.get('options',{}))
  from run_settings import route
  from native_triggers import CompletionGate
  self.plan=route(m['seed'],m.get('options',{}));self.gate=CompletionGate();self.gate.restore(self.data.get('completion_gate'))
  if self.plan and not self.path.exists():self.data.update(spot=self.plan[0],limit=len(self.plan))
  if m['options'].get('mode')=='normal':self.data['limit']=0
  from beta_bosses import Gate
  self.beta_gate=Gate(allow_fast=m.get('options',{}).get('extras',{}).get('one_hp',False))
  from minibosses import Gate as MiniGate
  self.mini_gate=MiniGate();self.mini_gate.restore(self.data.get('miniboss_gate'))
  self.entry_frame=None;self.entry_tick=None;self.entry_started=0.;self.entry_changed=0.;self.entry_ready=False;self.entry_deaths=None
  self.save()
 def save(self):write_json(self.path,self.data)
 def trace(self,event,**details):
  rows=self.data.setdefault('transition_trace',[])
  rows.append(dict(time=time.time(),event=event,index=self.data['index'],spot=self.data['spot'],**details))
  del rows[:-80]
 def persist_gate(self,frame):
  state=self.gate.snapshot()
  if self.data.get('completion_gate')!=state:
   self.data['completion_gate']=state
   self.trace('completion-observed',frame=frame,evidence=state)
   self.save()
 def pause(self):
  self.gate.pause()
  self.beta_gate.__init__();self.mini_gate.reset()
 def recovery(self):
  target=self.data.get('pending')
  if target is None:return None
  point=self.destination(target)
  if target not in self.m['pool'] or not isinstance(point,dict):raise ValueError('Ungültiges Wiederaufnahmeziel.')
  return dict(target=target,point=dict(point),index=self.data['index'])
 def observe(self,*,frame,position,collectables,achievements,disk_achievements,stats,settled=True,disk_collectables=None,saved_frame=None,disk_frame=None,disk_position=None,scene_tick=None,restart_pressed=False,beta_sample=None,mini_sample=None):
  d=self.data
  if not settled:return None
  if d['pending']:return self.recovery()['target']
  from beta_catalogue import BETA
  beta_won=False;beta_key=None
  active=d.get('trigger_spot',d['spot'])
  if is_target(self.m) and beta_sample and beta_sample.get('key') in BETA:active=BETA[beta_sample['key']][2]
  if self.m.get('options',{}).get('levels',True) and active in self.m['pool'] and beta_sample and beta_sample.get('key') in BETA:
   beta_key=beta_sample['key']
   beta_won=self.beta_gate.observe(active,d['index'],beta_sample,int(stats.get('deaths',0)))
   receipt=d.get('beta_bosses',{}).get(beta_key,{})
   recovered=bool(receipt and receipt.get('index')==d['index'] and active==BETA[beta_key][2] and frame==BETA[beta_key][1])
   if beta_won and not recovered:
    d.setdefault('beta_bosses',{})[beta_key]=dict(time=time.time(),frame=frame,index=d['index'],native_hp=beta_sample['hp'])
    self.trace('beta-boss-defeated',frame=frame,boss=beta_key)
   beta_won=beta_won or recovered
   if d.get('beta_gate')!=self.beta_gate.state or beta_won:
    d['beta_gate']=dict(self.beta_gate.state);self.save()
  else:
   self.beta_gate.observe(None,d['index'],None,0)
  from beta_catalogue import stage_achievements,RECEIPT_BOSSES
  point=self.m['pool'].get(active);normal_reason=None
  if self.m.get('options',{}).get('levels',True) and point and frame>2 and frame!=9 and d['spot']!='boss_solgryn.ini' and active not in {v[2] for v in BETA.values()}:
   spot='save1.ini' if active.startswith('prehistorik_') else active
   normal_reason=self.gate.observe(spot,point,frame,achievements,disk_achievements,stats,scene_tick,restart_pressed,position=position)
   mini_reason=self.mini_gate.observe(active,d['index'],point,mini_sample,int(stats.get('deaths',0)))
   mini_state=self.mini_gate.snapshot()
   if d.get('miniboss_gate')!=mini_state:
    d['miniboss_gate']=mini_state;self.trace('miniboss-observed',frame=frame,evidence=mini_state);self.save()
   normal_reason=mini_reason or normal_reason
   self.persist_gate(frame)
   key=next((k for k,v in BOSSES.items() if v[2]==active),None)
   if normal_reason and point['category']=='bosses' and key in RECEIPT_BOSSES and self.m.get('options',{}).get('route_version',1)>=4:
    if key not in d.setdefault('stage_bosses',{}):
     d['stage_bosses'][key]=dict(time=time.time(),frame=frame,index=d['index'],exit=normal_reason)
     self.trace('stage-boss-defeated',frame=frame,boss=key);self.save()
  achievements=stage_achievements(self.m.get('options',{}),d,achievements)
  disk_achievements=stage_achievements(self.m.get('options',{}),d,disk_achievements)
  target_mode=is_target(self.m)
  if target_mode:
   got=confirmed(self.goals,collectables,disk_collectables or {},achievements,disk_achievements)
   if d.get('targets_obtained')!=got:d['targets_obtained']=got;self.save()
   complete=got==self.goals
   if not complete and frame==46:return self.request(collectables,frame,'Solgryn noch gesperrt',stats)
   if complete and d['spot']!='boss_solgryn.ini':return self.request(collectables,frame,'Alle Ziele erreicht',stats,target='boss_solgryn.ini')
  if frame==46 and int(achievements.get('solgryn',0))<2 and not d['solgryn_armed']:
   d['solgryn_armed']=True;self.save()
  if d['solgryn_armed'] and int(achievements.get('solgryn',0))>=2 and int(disk_achievements.get('solgryn',0))>=2:
   if not (self.folder/'summary.json').exists():
    from native_models import slot_summary
    summary=slot_summary(self.store,self.m['slot']);summary.update(completed=True,completed_at=time.time(),route=d['history'],native_route_version=self.m.get('options',{}).get('route_version',1))
    from run_settings import encode
    summary.update(share_seed=encode(self.m['seed'],self.m.get('options',{})),options=self.m.get('options',{}),goals=self.goals)
    summary['deaths']=int(stats.get('deaths',summary['deaths']));summary['seconds']=int(stats.get('timeseconds',summary['seconds']))
    write_json(self.folder/'summary.json',summary)
   return None
  if not self.m.get('options',{}).get('levels',True):return None
  if d['pending']:return d['pending']
  if frame<=2 or frame==9 or d['spot']=='boss_solgryn.ini':return None
  self.rebase(frame,position)
  if target_mode:
   completed=[k for k in BOSSES if int(achievements.get(k,0))>=2 and int(disk_achievements.get(k,0))>=2]
   if d.get('completed_bosses')!=completed:d['completed_bosses']=completed;self.save()
   if saved_frame==frame==disk_frame and disk_position is not None and list(position)==list(disk_position) and frame not in {b[1] for b in BOSSES.values()}:
    if d.setdefault('checkpoints',{}).get(str(frame))!=list(position):d['checkpoints'][str(frame)]=list(position);self.save()
   # Both modes keep the selected stage until its confirmed exit is handled.
  active=d.get('trigger_spot',d['spot']);point=self.m['pool'].get(active)
  if not point:return None
  # Old experimental starts are removed from new seeds; existing saves can
  # still finish their world, without a checkpoint-distance teleport.
  spot='save1.ini' if active.startswith('prehistorik_') else active
  if spot in {v[2] for v in BETA.values()}:
   return self.request(collectables,frame,BETA[beta_key][0]+' besiegt',stats) if beta_won else None
  if normal_reason:return self.request(collectables,frame,normal_reason,stats)
  return None
 def rebase(self,frame,position):
  if self.data['pending']:return
  value=[int(frame),*[int(v) for v in position]]
  if self.data['baseline']!=value:self.data['baseline']=value;self.save()
 def request(self,collectables,frame,reason,stats,target=None):
  d=self.data
  if d['pending']:return d['pending']
  explicit=target is not None
  if target is None:
   if self.plan:target=self.plan[min(d['index']+1,len(self.plan)-1)]
   elif not is_target(self.m) and d['index']>=d['limit']-1:target='boss_solgryn.ini'
   else:
    choices=sorted(k for k,p in eligible(self.m['pool'],collectables).items() if k!='boss_solgryn.ini' and not k.startswith('prehistorik_') and (p['frame']!=frame or (p.get('segment') and k!=d.get('trigger_spot',d['spot']))))
    if is_target(self.m):
     done={BOSSES[k][2] for k in d.get('completed_bosses',[])}
     choices=[k for k in choices if k not in done]
     category='rooms' if self.m['pool'].get(d.get('trigger_spot',d['spot']),{}).get('category')=='bosses' else 'bosses'
     alternate=[k for k in choices if self.m['pool'][k]['category']==category]
     choices=alternate or choices
    if not choices:raise ValueError('Kein freier Level-Spot verfügbar.')
    n=int.from_bytes(hashlib.sha256(f"{self.m['seed']}\0native-route-v1\0{d['index']}".encode()).digest(),'big');target=choices[n%len(choices)]
  if is_target(self.m) and target=='boss_solgryn.ini' and d.get('targets_obtained')!=self.goals:raise ValueError('Die Ziel-Liste ist noch nicht erfüllt.')
  if target not in eligible(self.m['pool'],collectables):raise ValueError('Dieses Ziel ist noch gesperrt.')
  point=dict(self.m['pool'][target])
  checkpoint=d.get('checkpoints',{}).get(str(point['frame']))
  if is_target(self.m) and not explicit and reason!='Gastly gefangen' and point['category']=='rooms' and target!='gastly_grass' and not point.get('segment') and not point.get('fixed_start') and checkpoint:point.update(x=checkpoint[0],y=checkpoint[1])
  d['pending_point']=point
  d['pending']=target;d['pending_event']=dict(from_spot=d['spot'],target=target,reason=reason,seconds=int(stats.get('timeseconds',0)),deaths=int(stats.get('deaths',0)))
  self.trace('transition-requested',frame=frame,target=target,point=point,reason=reason)
  self.save();return target
 def destination(self,target):return self.data.get('pending_point') if self.data['pending']==target and self.data.get('pending_point') else self.m['pool'][target]
 def arrive(self,target,frame,position):
  d=self.data;p=self.destination(target)
  if d['pending']!=target or frame!=p['frame'] or tuple(position)!=(p['x'],p['y']):raise ValueError('Ankunft nicht bestätigt.')
  self.mini_gate.reset();d['miniboss_gate']=self.mini_gate.snapshot()
  self.gate.reset();d['completion_gate']=self.gate.snapshot();self.trace('arrival-confirmed',target=target,frame=frame,position=list(position));self.entry_frame=None;self.entry_tick=None;self.entry_ready=False
  d.pop('pending_point',None);d.pop('trigger_spot',None)
  d['history'].append(d.pop('pending_event'));d.update(pending=None,spot=target,index=d['index']+1,baseline=[frame,*position]);self.save()
