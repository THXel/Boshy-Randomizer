"""Change all three global packages on one immutable run; verify real audio/death/retry."""
import json,uuid
from functools import partial
from pathlib import Path
from native_menu import builds
from menu_host.store import Store,digest
builds.DYNAMIC_BASE=builds.PREFIX/'drive_c/BoshyTransitions/Boshy-dynamic-v34.exe'
builds.DYNAMIC_SHA=digest(builds.DYNAMIC_BASE)
from export_native_run import export
from export_route_probe import ROOT
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu_probe import pump
from native_classic_live import enter_title,trigger,wait
from native_menu.observe import objects
from god_mode_boss_probe import values
from music import runtime
import native_runtime_music_live as audio
import god_mode_live as capture
OUT=ROOT/'outputs/Fusion-Completion-20261026';audio.OUT=OUT;capture.OUT=OUT
report=dict(build=str(builds.DYNAMIC_BASE),sha256=builds.DYNAMIC_SHA,cases=[],memory_writes=0)
s=Store(OUT/('pack-preferences-'+uuid.uuid4().hex[:8]),exporter=partial(export,dynamic=True))
with s.lock():
 d=Draft();d.set_mode('normal');d.update(god_mode=True,no_mouse_ghost=True,characters=False);s.create(1,d)
 immutable=(s.folder(1)/'plan.json').read_bytes();seed=d.shared()
 c=CombinedController(s,dynamic=True)
 try:
  c.open();identity=c.window.pid
  for pack in ('kamilia3','wannafest22','original'):
   enter_title(c);pump(c,9)
   if trigger(c)[1]!=-1:c.window.key('Return');wait(c,lambda:trigger(c)[1]==-1)
   c.window.key('Down');pump(c,.2);c.window.key('Return');wait(c,lambda:c.window.reader.frame()=='Options');pump(c,.3)
   for _ in range(3):c.window.key('Down');pump(c,.25)
   c.window.key('Right');pump(c,.5);assert c.presentation.pack==pack
   c.window.key('Escape');wait(c,lambda:c.window.reader.frame()=='Title Screen');c.enter()
   c.model.slot=1;c.model.load_slot();c.begin();wait(c,lambda:c.phase=='playing');pump(c,2)
   cue='Prehistorik2Boss (2)'
   if pack=='original':expected=runtime.original_audio()[cue]
   else:
    path=c.presentation.music['Cue'+str(runtime.NAMES.index(cue)).zfill(2)]
    expected=(c.folder/Path(path.replace('\\','/'))).read_bytes()
   result=audio.audio_check(c,'global-'+pack,expected)
   c.window.key('q');pump(c,.7)
   panel=next(o for o in objects(c.window.reader) if o['name']=='Randomizer Death Screen')
   assert values(c.window.reader,panel,1)[0]==int(pack!='original')
   capture.snap(c.window,'global-'+pack+'-death')
   c.window.key('r');pump(c,.7)
   assert sum(o['name']=='Player' for o in objects(c.window.reader))==1
   c.window.key('F2');wait(c,lambda:c.phase=='menu')
   assert (s.folder(1)/'plan.json').read_bytes()==immutable and c.model.draft.shared()==seed
   assert c.window.pid==identity
   report['cases'].append(dict(pack=pack,audio=result,death_and_retry=True,seed_and_plan_unchanged=True))
   print('PASS',pack,flush=True)
  report['passed']=True
 except BaseException as error:report['error']=repr(error);raise
 finally:
  try:c.close()
  finally:(OUT/'pack-preferences-v34-live.json').write_text(json.dumps(report,indent=2)+'\n')
