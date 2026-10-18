import sys
"""Controller-owned diagnostics and explicit, run-bound test commands."""
from pathlib import Path
import os,time,json,uuid,struct,subprocess
from debug_data import read_json,write_json,Recorder

class DebugRuntime:
 def __init__(self,store,start_window=True):
  self.store=store;self.token=uuid.uuid4().hex;self.folder=store.base/'.debug-runtime'/self.token;self.folder.mkdir(parents=True)
  self.recorder=Recorder(store.base);self.last_error_report=None
  self.last=0.;self.sequence=0;self.events=[];self.player_key=None;self.player_ptr=None;self.player_oi=None;self.closed=False;self.window=None
  if start_window:
   self.window=subprocess.Popen(__import__('host_platform').python_command('debug_window.py','--host',str(os.getpid()),'--session',str(self.folder)),cwd=store.base,stdout=subprocess.DEVNULL,stderr=open(self.folder/'window-errors.log','a'),start_new_session=True,**__import__('host_platform').child_options())
 def event(self,event,**fields):
  self.events.append(dict(time=time.time(),event=event,**fields));self.events=self.events[-80:]
 def error(self,error):
  self.event('Fehler',message=str(error))
  try:
   state={**getattr(self,'state',{}),'sequence':self.sequence+1,'time':time.time(),'phase':'error','events':list(self.events),'exception_type':type(error).__name__}
   if getattr(self,'timings',None):state['transition_timings']=self.timings.snapshot()
   if getattr(getattr(self,'spawn_bridge',None),'last_spawn_check',None):state['spawn_guard']=dict(self.spawn_bridge.last_spawn_check)
   self.last_error_report=str(self.recorder.finish(str(error),state))
   write_json(self.store.base/'debug-reports/latest-error.json',dict(path=self.last_error_report,time=time.time(),error=str(error)))
  except Exception as export_error:self.event('Bericht fehlgeschlagen',message=str(export_error))
 def graphics_state(self,player):
  identity=(player.m['run_id'],id(player),id(player.bridge))
  if getattr(self,'graphics_run',None)!=identity:
   from graphics_debug import Telemetry
   self.graphics_run=identity;self.graphics=Telemetry(player)
  return self.graphics.read()
 def demands(self):return read_json(self.folder/'watch.json',{}).get('observe',False)
 def commands(self,player=None):
  for p in sorted(self.folder.glob('request-*.json'))[:8]:
   req=read_json(p,{})
   # Claim before executing; a leftover file after a crash is never replayed.
   claimed=p.with_suffix('.claimed');p.rename(claimed)
   response={'ok':False,'time':time.time()}
   try:
    if req.get('session')!=self.token:raise ValueError('Veraltete Debug-Sitzung.')
    if not 0<=time.time()-float(req.get('created_at',0))<=10:raise ValueError('Testaktion ist abgelaufen; bitte erneut auslösen.')
    if player is None or not player.progress or not player.last:raise ValueError('Testaktionen sind nur im geladenen Randomizer-Lauf verfügbar.')
    if req.get('run_id')!=player.m['run_id'] or req.get('binding')!=player.m['session_binding']:raise ValueError('Der aktive Spielstand hat sich geändert.')
    if req.get('action')!='graphics_mask' and not req.get('enabled'):raise ValueError('Testaktionen zuerst freigeben.')
    response.update(ok=True,message=self.execute(player,req))
   except Exception as e:response.update(ok=False,message=str(e));self.event('Testaktion abgewiesen',message=str(e))
   write_json(self.folder/(p.stem.replace('request-','response-')+'.json'),response)
 def mark(self,player,req):
  folder=player.folder/'debug-actions';folder.mkdir(exist_ok=True)
  record={k:req.get(k) for k in ('action','value','run_id','created_at')};record.update(time=time.time(),phase='requested')
  identity=uuid.uuid4().hex
  # Retain the exact pre-action files once for each user-requested test mutation.
  from native_session import atomic
  backup=folder/identity;backup.mkdir()
  for path in (self.store.base/'IWBTB'/player.save_name,self.store.base/'IWBTB/onlineLicense.ini',player.progress.path):
   if path.exists():atomic(backup/path.name,path.read_bytes())
  write_json(backup/'action.json',record)
  write_json(player.folder/'debug-state.json',{'modified':True,'last_action':record})
  self.event('Testeingriff',action=req['action'],value=req['value']);return backup
 def execute(self,player,req):
  action=req.get('action');value=req.get('value')
  if action=='graphics_mask':
   from graphics_debug import request
   message=request(player,value);self.event('Grafikdiagnose',value=value);return message
  choices=self.choices(player)
  if action not in ('teleport','grant_item','grant_character'):raise ValueError('Unbekannte Testaktion.')
  allowed=choices['spots'] if action=='teleport' else choices['items' if action=='grant_item' else 'characters']
  valid={row['key'] for row in allowed}
  if value not in valid:raise ValueError('Unbekanntes oder nicht verfügbares Ziel.')
  if player.progress.data.get('pending'):raise ValueError('Ein Übergang läuft bereits; bitte dessen Ende abwarten.')
  if not player.can_transition():raise ValueError('Zuerst das Belohnungsfenster bestätigen.')
  snap=player.bridge.snapshot()
  if snap['scene']<=1 or snap['scene']==20 or snap['next'] or snap['frame_count']<2:raise ValueError('Das Spiel ist noch nicht spielbereit.')
  if req.get('frame')!=player.last['frame'] or snap['scene']+1!=req.get('frame'):raise ValueError('Der Raum hat gewechselt; bitte erneut auslösen.')
  from lab import ini_object_ids,ini_items
  ids=ini_object_ids(player.bridge);identity=ini_items(player.bridge,'randochecks',ids['Ini++'])
  if identity['sessionid']['value']!=player.m['run_id']:raise ValueError('Aktiver Lauf konnte nicht bestätigt werden.')
  backup=self.mark(player,req)
  try:
   if action=='teleport':
    from gastly_route_lab import read_state
    state=read_state(player.bridge,player.save_name)
    player.progress.request(state['collectables'],state['frame'],'Debug-Teleport',player.last.get('stats',{}),target=value)
    message='Teleport angefordert; die bestehende Übergangsprüfung bestätigt die Ankunft.'
   else:
    self.grant(player,value,action=='grant_character',ids)
    message=value+' wurde als Test vergeben.'
   write_json(backup/'result.json',{'ok':True,'message':message});return message
  except Exception as e:
   write_json(backup/'result.json',{'ok':False,'error':str(e)});raise
 def grant(self,player,name,is_character,ids):
  from lab import ini_items
  from mixed_rewards import action,string_param
  obj='Ini++ 3' if is_character else 'Ini++';group='Unlockables' if is_character else 'Collectables';snap=player.bridge.snapshot()
  plan=json.loads((self.store.base/'slot_reward_plan.json').read_text(encoding='utf-8'));loc=next((r for r in plan['locations'] if r['scene']==snap['scene']),None)
  ref=bytes.fromhex(loc['license_ref' if is_character else 'save_ref']) if loc else None
  if ref is None:
   bank=struct.unpack('<I',player.bridge.read(snap['run']+0x88,4))[0];off=0
   for _ in range(6000):
    h=player.bridge.read(bank+off,14);n=-struct.unpack_from('<h',h)[0]
    if not n:break
    if not 14<=n<32768:raise ValueError('Ereignisreferenz ist ungültig.')
    block=player.bridge.read(bank+off,n);needle=bytes.fromhex('210058000a00')+struct.pack('<H',ids[obj]);at=block.find(needle)
    if at>=0:ref=block[at+6:at+10];break
    off+=n
  if ref is None or struct.unpack_from('<H',ref)[0]!=ids[obj]:raise ValueError('Dieser Raum unterstützt die Testvergabe noch nicht.')
  template=struct.pack('<HhHHHBBBB',14,33,95,*struct.unpack('<HH',ref),0,0,3,0)
  setter=action(template,[string_param(group),string_param(name),string_param('1')],ref)
  if len(setter)>224:raise ValueError('Testvergabe ist zu groß.')
  address=player.metadata['menu']+1648;h=struct.unpack('<7I',player.bridge.read(address,28))
  if h[0]!=h[1]:raise ValueError('Eine native Aktion läuft bereits.')
  sequence=h[0]+1;payload=struct.pack('<7I',sequence,h[1],snap['scene'],ids['Ini++'],0,len(setter),len(setter))+setter.ljust(224,b'\0')*2+bytes(36)
  if not player.bridge.cmd(f"character {player.metadata['menu']:x} {payload.hex()}").get('written'):raise RuntimeError('Native Testvergabe abgewiesen.')
  end=time.monotonic()+3
  while time.monotonic()<end:
   ack=struct.unpack('<7I',player.bridge.read(address,28))
   if ack[1]==sequence:break
   time.sleep(.03)
  if ack[1]!=sequence or ack[4]!=1:raise RuntimeError('Native Testvergabe nicht bestätigt.')
  from native_models import ini
  path=self.store.base/'IWBTB'/('onlineLicense.ini' if is_character else player.save_name)
  end=time.monotonic()+3
  while time.monotonic()<end:
   live=ini_items(player.bridge,group.lower(),ids[obj]).get(name.lower(),{}).get('value')
   if live=='1' and ini(self.store,path).get(group.lower(),{}).get(name.lower())=='1':
    from native_profiles import snapshot
    snapshot(self.store,player.m);player.rewards.last=0;player.rewards.poll();return
   time.sleep(.05)
  raise RuntimeError('Testvergabe wurde nicht dauerhaft bestätigt. Sie wird nicht automatisch wiederholt.')
 def choices(self,player):
  from native_models import location
  from native_level_route import eligible
  from native_models import ini
  collect=ini(self.store,self.store.base/'IWBTB'/player.save_name).get('collectables',{})
  available=eligible(player.m['pool'],collect)
  if player.m['options'].get('mode')=='target' and player.progress.data.get('targets_obtained')!=player.progress.goals:available={k:v for k,v in available.items() if k!='boss_solgryn.ini'}
  plan=json.loads((self.store.base/'slot_reward_plan.json').read_text(encoding='utf-8'))
  return {'spots':[{'key':k,'label':p.get('label',location(p['frame']))+' · '+k} for k,p in available.items()],
          'items':[{'key':n,'label':n} for n in sorted({r['source'] for r in plan['locations'] if r['source_kind']=='item'}|{'Gastly'})],
          'characters':[{'key':n,'label':n} for n in sorted({r['source'] for r in plan['locations'] if r['source_kind']=='character'})]}
 def position(self,player,snap,retry=True):
  from lab import objects
  key=(player.m['run_id'],snap['run'],snap['scene'],snap['object_list'])
  reset=snap['frame_count']<getattr(self,'player_tick',0)
  self.player_tick=snap['frame_count']
  if key!=self.player_key or not self.player_ptr or reset:
   self.player_key=key;self.player_ptr=None
   for obj in objects(player.bridge):
    if obj['type']!=2:continue
    meta=struct.unpack_from('<I',bytes.fromhex(obj['raw']),28)[0]
    if player.bridge.read(meta+90,24).split(b'\0')[0]==b'Player':
     self.player_ptr=obj['ptr'];self.player_oi=obj['oi'];self.player_handle=obj['handle'];self.player_slot=obj['slot'];break
  if self.player_ptr:
   pointer=struct.unpack('<I',player.bridge.read(snap['object_list']+self.player_slot*8,4))[0]
   raw=player.bridge.read(self.player_ptr,100) if pointer==self.player_ptr else bytes(100)
   valid=pointer==self.player_ptr and struct.unpack_from('<H',raw,18)[0]==self.player_oi and struct.unpack_from('<h',raw,24)[0]==2 and struct.unpack_from('<h',raw,0)[0]==self.player_handle
   if valid:
    after=player.bridge.snapshot()
    if (after['scene'],after['run'],after['object_list'])!=(snap['scene'],snap['run'],snap['object_list']) or after['frame_count']<snap['frame_count']:raise RuntimeError('Scene changed during observation')
    return [struct.unpack_from('<i',raw,76)[0],struct.unpack_from('<i',raw,84)[0]]
   self.player_ptr=None
   if retry:return self.position(player,player.bridge.snapshot(),retry=False)

 def tick(self,phase,player=None,model=None,force=False):
  now=time.monotonic()
  if not force and now-self.last<.5:return
  self.last=now;self.sequence+=1;self.timings=None;self.spawn_bridge=None
  data=dict(schema=1,sequence=self.sequence,time=time.time(),host_pid=os.getpid(),phase=phase,game_root=str(self.store.base/'IWBTB'),game_exe=str(self.store.base/'IWBTB/I Wanna Be The Boshy.exe'),events=self.events,run_id=None,choices={})
  if model:data.update(menu_page=model.page,selected_slot=model.slot,message=model.message)
  if player and player.last:
   data.update(run_id=player.m['run_id'],binding=player.m['session_binding'],slot=player.m['slot'],seed=player.m['seed'],options=player.m['options'],last=player.last,progress=player.progress.data,observed=getattr(player,'debug_sample',{}),choices=self.choices(player),debug_modified=(player.folder/'debug-state.json').exists())
   from trigger_explanation import explain
   data['trigger_explanation']=explain(player)
   if getattr(player,'insights',None):data['run_highlights']=player.insights.highlights()
   data['graphics']=self.graphics_state(player)
   if getattr(player,'shots',None):data['shot_cycle']=dict(player.shots.data)
   from seed_share import encode_saved
   data['share_seed']=encode_saved(player.m['seed'],player.m['options'],getattr(getattr(player,'rules',None),'base',self.store.base),getattr(player,'rules',None))
   self.timings=getattr(player,'transition_timings',None)
   if self.timings:data['transition_timings']=self.timings.snapshot()
   self.spawn_bridge=player.bridge
   if getattr(player.bridge,'last_spawn_check',None):data['spawn_guard']=dict(player.bridge.last_spawn_check)
   # Keep position history available for the hidden-window problem marker.
   if not getattr(player,'ending_started',False):
    try:
     snap=player.bridge.snapshot();data['engine']={k:snap[k] for k in ('scene','next','frame_count','viewport')};data['player_position']=self.position(player,snap)
    except Exception as e:data['observation_error']=str(e)
  data['last_error_report']=self.last_error_report
  self.state=data;self.recorder.observe(json.loads(json.dumps(data)));write_json(self.folder/'state.json',data)
 def close(self):
  if self.closed:return
  self.closed=True
  data={**getattr(self,'state',{}),'events':self.events,'phase':'stopped','sequence':self.sequence+1,'time':time.time()};write_json(self.folder/'state.json',data)
