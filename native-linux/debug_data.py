"""Bounded diagnostic recordings; no save-file writes or global key logging."""
from pathlib import Path
from collections import deque
import json,time,uuid,zipfile,hashlib
from copy import deepcopy
from ui_i18n import tr

MAX_JSON=2*1024*1024

def read_json(path,default=None):
 try:
  p=Path(path)
  if p.stat().st_size>MAX_JSON:return default
  return json.loads(p.read_text(encoding='utf-8'))
 except (OSError,ValueError):return default

def write_json(path,data):
 from native_session import write_json as atomic_json
 atomic_json(Path(path),data)

def report_text(state,note=''):
 return json.dumps({'beschreibung':note[:12000],'diagnose':state},indent=2,ensure_ascii=False)

class Recorder:
 def __init__(self,base,max_bytes=50*1024*1024):
  self.base=Path(base);self.folder=self.base/'debug-reports';self.ring=deque(maxlen=240);self.last=None;self.active=None;self.stream=None;self.bytes=0;self.max_bytes=max_bytes;self.last_export=None;self.notice='';self.note=''
 def observe(self,state):
  stamp=state.get('sequence')
  if stamp is None or stamp==self.last:return
  self.last=stamp;state=deepcopy(state);self.ring.append(state)
  cutoff=state.get('time',time.time())-120
  while self.ring and self.ring[0].get('time',cutoff)<cutoff:self.ring.popleft()
  if self.stream:
   self.append(state)
   if self.bytes>=self.max_bytes:self.finish(self.note+'\nAutomatisch gespeichert: Größenlimit erreicht.');self.notice='Aufzeichnung wegen Größenlimit gespeichert.'
 def marker_snapshot(self,state,note=''):
  """Freeze on the UI thread; exporting this copy cannot stop a recording."""
  frozen=Recorder(self.base,self.max_bytes);frozen.ring=deepcopy(self.ring);frozen.last=self.last
  marked=deepcopy(state);now=time.time()
  marked['problem_marker']={'time':now,'observation_age_seconds':max(0,now-marked['time']) if marked.get('time') else None}
  cutoff=now-120
  while frozen.ring and frozen.ring[0].get('time',0)<cutoff:frozen.ring.popleft()
  return frozen,marked,note
 def export_marker(self,state,note=''):
  path=self.finish(note,state)
  write_json(self.folder/'latest-marker.json',{'path':str(path),'time':time.time(),'run_id':state.get('run_id')})
  return path
 def append(self,state):
  raw=json.dumps(state,ensure_ascii=False,separators=(',',':'))+'\n';self.stream.write(raw);self.stream.flush();self.bytes+=len(raw.encode())
 def start(self):
  if self.stream:return
  self.folder.mkdir(exist_ok=True);name=time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8];self.active=self.folder/(name+'.jsonl');self.stream=self.active.open('x');self.bytes=0
  for row in self.ring:self.append(row)
 def finish(self,note='',state=None):
  self.folder.mkdir(exist_ok=True)
  if state is not None:self.observe(state)
  if self.stream:self.stream.close();self.stream=None
  name=self.active.stem if self.active else time.strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
  path=self.folder/(name+'.zip');last=state or (self.ring[-1] if self.ring else {})
  versions={}
  for n in ('graphics_debug.py','graphics_debug.c','background_sets.py','sprite_chaos.py','hub_guard.py','fast_exit.py','spawn_guard.py','transition_timing.py','debug_data.py','transition_guard.py','native_menu_polished.dll','old_sonic.py','trigger_audit.py','native_player.py','native_progress.py','native_triggers.py','beta_bosses.py','minibosses.py','intro_guard.py','native_intro_guard.dll','beta_catalogue.py','run_settings.py','slot_reward_hook.bin','native_menu.dll','debug_runtime.py','debug_window.py','run_extras.py','shot_cycle.py','runtime_versions.py','run_insights.py','trigger_explanation.py','bridge.exe'):
   p=self.base/n
   if p.is_file():versions[n]=hashlib.sha256(p.read_bytes()).hexdigest()
  metadata={'schema':1,'created_at':time.time(),'description':note[:12000],'versions':versions,'last_state':last,'sample_period_seconds':.5,'prehistory_limit_samples':240,'recording_file':self.active.name if self.active else None}
  from graphics_debug import capture_game
  screenshot,capture=capture_game(self.base)
  metadata['screenshot']={**capture,'observation_time':last.get('time')}
  with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
   if screenshot:z.writestr('game.png',screenshot)
   z.writestr('graphics.json',json.dumps(last.get('graphics',{}),ensure_ascii=False,indent=2))
   z.writestr('bericht.json',json.dumps(metadata,ensure_ascii=False,indent=2))
   z.writestr('LESEN.txt','Boshy Randomizer – Debug-Aufzeichnung\n\n'+note[:12000]+'\n\nzeitverlauf.jsonl enthält beobachtete Zustände; Testaktionen sind als solche markiert. Fehlende Beobachtungen beweisen keinen fehlenden Trigger. game.png zeigt ausschließlich das Spielfenster, falls verfügbar. graphics.json enthält den aktiven Hintergrund und die letzten Grafikwechsel. Der Aufnahmezeitpunkt steht in bericht.json. Originale Spielstände und das Charakterprofil sind nicht Teil dieses Exports.\n')
   explanation=last.get('trigger_explanation',{})
   z.writestr('trigger.txt','Erwartet: '+explanation.get('expected','Keine aktive Route')+'\nStatus: '+explanation.get('reason','Keine Beobachtung')+'\nRegelsatz: '+explanation.get('rules_version','–')+'\n\nLetzte Übergänge:\n'+'\n'.join(json.dumps(r,ensure_ascii=False) for r in last.get('progress',{}).get('transition_trace',[])))
   z.writestr('trigger-evidence.json',json.dumps(explanation,ensure_ascii=False,indent=2))
   z.writestr('transition-timings.json',json.dumps(last.get('transition_timings',[]),ensure_ascii=False,indent=2))
   if self.active:z.write(self.active,'zeitverlauf.jsonl')
   else:z.writestr('zeitverlauf.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in self.ring))
  self.active=None;self.last_export=path;return path

class Chord:
 """One toggle per press, with focus gating; unrelated key contents are discarded."""
 def __init__(self):self.down=False
 def update(self,down,eligible):
  fired=down and not self.down and eligible;self.down=down;return fired
