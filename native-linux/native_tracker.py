"""Read-only run presentation, published atomically for desktop and stream trackers."""
import json,os,time
from pathlib import Path
from native_session import write_json
from native_models import ini,location
from beta_catalogue import goals,BOSSES,stage_achievements
from seed_share import encode_saved
from tracker_awards import Awards

class Publisher:
 def __init__(self,store):
  self.store=store;self.path=store.base/'INI/native-live.json';self.last=0;self.identity=None;self.clock=0.;self.anchor=None;self.clock_path=None;self.awards=Awards();self.catalogue_cache=None;self.share_cache=None;self.music_reader=None;self.music_player=None;self.music_bridge=None
 def pause(self):
  if self.anchor is not None:
   self.clock+=max(0,time.monotonic()-self.anchor);self.anchor=None
   if self.clock_path:write_json(self.clock_path,dict(version=1,elapsed=self.clock))
 def emit(self,data,force=False):
  now=time.time()
  if not force and now-self.last<.5:return
  self.last=now;write_json(self.path,dict(schema=1,updated_at=now,host_pid=os.getpid(),root=str(self.store.base),**data))
 def menu(self,loading=False):
  self.music_reader=None;self.music_player=None;self.music_bridge=None
  self.pause();self.emit(dict(mode='menu',game_running=True,phase='loading' if loading else 'menu',elapsed=0,timer_running=False,items=[],characters=[],bosses=[],goals=[],seed='',slot=0,character='',location='Spielstand wählen'),force=loading)
 def stopped(self):
  self.pause();self.emit(dict(mode='stopped',game_running=False),True)
 def run(self,player,result):
  if time.time()-self.last<.5:return
  m=player.m;folder=self.store.root/m['run_id'];d=ini(self.store,self.store.base/'IWBTB'/f"SaveFile{m['slot']}.ini");lic=ini(self.store,folder/'profile.ini');stats=result.get('stats',{}) or d.get('stats',{});progress=player.progress.data
  if self.identity!=m['run_id']:
   self.pause();self.identity=m['run_id'];self.clock_path=folder/'tracker-clock.json'
   base=getattr(getattr(player,'rules',None),'base',self.store.base)
   self.catalogue_cache=json.loads((base/'slot_reward_plan.json').read_text(encoding='utf-8'));self.share_cache=encode_saved(m['seed'],m['options'],base,getattr(player,'rules',None))
   self.music_reader=None
   try:self.clock=max(0,float(json.loads(self.clock_path.read_text(encoding='utf-8'))['elapsed']))
   except (OSError,ValueError,KeyError):self.clock=max(0,float(stats.get('timeseconds',0)))
  # Run identity survives reloads; the process connection and native addresses do not.
  if self.music_reader is None or self.music_player is not player or self.music_bridge is not player.bridge:
   from native_telemetry import MusicReader
   self.music_reader=MusicReader(player);self.music_player=player;self.music_bridge=player.bridge
  finished=bool(result.get('completed'));now=time.monotonic()
  if finished:self.pause()
  elif self.anchor is None:self.anchor=now
  elapsed=self.clock+(max(0,now-self.anchor) if self.anchor is not None else 0)
  write_json(self.clock_path,dict(version=1,elapsed=elapsed))
  if finished:
   summary_path=folder/'summary.json'
   if summary_path.exists():
    summary=json.loads(summary_path.read_text(encoding='utf-8'))
    if 'tracker_seconds' not in summary:
     summary.update(game_seconds=summary.get('seconds',0),seconds=int(elapsed),tracker_seconds=elapsed)
     write_json(summary_path,summary)
    elapsed=float(summary['tracker_seconds'])
  plan=self.catalogue_cache;owned=d.get('collectables',{});chars=lic.get('unlockables',{});ach=d.get('achievements',{});g=player.progress.goals;got=progress.get('targets_obtained',dict(items=[],bosses=[]))
  items=[dict(name=n,kind='item',done=owned.get(n.lower())=='1') for n in sorted({r['source'] for r in plan['locations'] if r['source_kind']=='item'}|{'Gastly'})]
  characters=[dict(name=n,kind='character',done=chars.get(n.lower())=='1') for n in sorted({r['source'] for r in plan['locations'] if r['source_kind']=='character'})]
  catalogue_module=player.rules.module('beta_catalogue') if getattr(player,'rules',None) else __import__('beta_catalogue')
  ach=catalogue_module.stage_achievements(m['options'],progress,ach)
  bosses=[dict(name=v[0],key=k,kind='boss',done=(k in progress.get('beta_bosses',{}) if k in ('questionmark','ridley') else int(ach.get(k,0))>=2)) for k,v in catalogue_module.catalogue(m['options']).items()]
  if m['options'].get('mode')=='normal':
   from native_targets import BOSSES as original_bosses
   bosses=[r for r in bosses if r['key'] in original_bosses]
  bosses.append(dict(name='Solgryn',key='solgryn',kind='boss',done=finished or int(ach.get('solgryn',0))>=2))
  goal_rows=[dict(name=n,kind='item',done=n in got['items']) for n in g['items']]+[dict(name=BOSSES[k][0],key=k,kind='boss',done=k in got['bosses']) for k in g['bosses']]
  self.awards.update(m['run_id'],items+characters+bosses)
  from run_extras import presentation
  extras=presentation(m['options'],player.shots.data if getattr(player,'shots',None) else None)
  from tracker_presenter import route_entries
  self.emit(dict(route_stages=route_entries(player,finished),play_mode=m['options'].get('mode','randomizer'),active_extras=extras,share_seed=self.share_cache,music=self.music_reader.read(),reward_events=self.awards.events,mode='target' if m['options'].get('mode')=='target' else 'randomizer',phase='finished' if finished else 'running',game_running=True,game_pid=player.metadata.get('pid',0),run_id=m['run_id'],slot=m['slot'],seed=m['seed'],options=m['options'],character=lic.get('license',{}).get('charactername','Dark Boshy'),difficulty=int(stats.get('difficulty',m['options']['difficulty'])),location=location(result['frame']),frame=result['frame'],elapsed=elapsed,timer_running=not finished,deaths=int(stats.get('deaths',0)),items=items,characters=characters,bosses=bosses,goals=goal_rows,route_index=progress['index'],route_limit=None if g['items'] or m['options'].get('mode')=='normal' else progress['limit'],route=progress.get('history',[])[-5:],checks_done=sum(d.get('randochecks',{}).get(r['key'].lower())=='1' for r in plan['locations']),checks_total=len(plan['locations']),solgryn_unlocked=bool(goal_rows and all(r['done'] for r in goal_rows)) if g['items'] else progress['spot']=='boss_solgryn.ini'))
