"""Complete Mario through ordinary input and native God Mode/autofire only."""
import json,time,uuid,subprocess
from functools import partial
from native_menu import builds
from menu_host.store import Store,save,digest
from export_route_probe import ROOT
OUT=ROOT/'outputs/Fusion-BackgroundGroups-20261026'
builds.DYNAMIC_BASE=builds.PREFIX/'drive_c/BoshyTransitions/Boshy-dynamic-v39.exe'
builds.DYNAMIC_SHA=digest(builds.DYNAMIC_BASE)
from export_native_run import export
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu_probe import pump
from native_classic_live import wait
from native_menu.observe import objects
from god_mode_boss_probe import values
from transition.router import GROUP
import god_mode_live as capture
capture.OUT=OUT
report=dict(scope=__doc__,build=str(builds.DYNAMIC_BASE),sha256=builds.DYNAMIC_SHA,memory_writes=0,samples=[])
s=Store(OUT/('mario-'+uuid.uuid4().hex[:8]),exporter=partial(export,dynamic=True))
with s.lock():
 d=Draft();d.set_mode('boss_rush');d.update(boss_pool=['mario'],route_boss_count=1,level_pool=[],level_count=0,no_mouse_ghost=True,god_mode=True,autofire=True,characters=False,sprite_scenery=True,sprite_backgrounds=True,sprite_decor=True,sprite_tiles=True,sprite_actors=True)
 d.seed='MARIO-NATURAL-V39';s.create(1,d);c=CombinedController(s,dynamic=True)
 try:
  c.open();c.enter();c.model.slot=1;c.model.load_slot();c.begin();wait(c,lambda:c.phase=='playing');pump(c,.5)
  subprocess.run(['wmctrl','-ia',c.window.window],check=True)
  subprocess.run(['xdotool','keydown','Left'],check=True)
  try:pump(c,3)
  finally:subprocess.run(['xdotool','keyup','Left'],check=True)
  c.window.key('Right');subprocess.run(['xdotool','keydown','x'],check=True)
  start=time.monotonic();last=-1
  while time.monotonic()-start<300:
   pump(c,.3);obs=objects(c.window.reader);elapsed=round(time.monotonic()-start,1)
   if int(elapsed)//10!=last:
    last=int(elapsed)//10;sample=dict(seconds=elapsed,objects=[dict(name=o['name'],x=o['x'],y=o['y'],values=values(c.window.reader,o,8)) for o in obs if o['name'] in ['Player','Classic Mario','Classic Mario 2','Classic Mario 3','Active 27']]);report['samples'].append(sample);print(json.dumps(sample),flush=True);capture.snap(c.window,'mario-fight-'+str(last))
   pipe=next((o for o in obs if o['name']=='Active 27'),None)
   if pipe and pipe['x']<=604:report['pipe_revealed']=True;break
   assert any(o['name']=='Player' for o in obs),'Player disappeared'
  subprocess.run(['xdotool','keyup','x'],check=True)
  capture.snap(c.window,'mario-pipe');assert report.get('pipe_revealed'),'Natural Mario fight did not reveal exit within 5 minutes'
  subprocess.run(['xdotool','keydown','Right'],check=True)
  try:
   end=time.monotonic()+10
   while time.monotonic()<end:
    pump(c,.15);cfg=save(c.folder/'SaveFile1.ini')
    if cfg.getint(GROUP,'Done17',fallback=0):break
  finally:subprocess.run(['xdotool','keyup','Right'],check=True)
  report['arrival']=dict(cfg[GROUP]);report['frame']=c.window.reader.frame();assert cfg.getint(GROUP,'Done17')==1
  assert cfg.getint(GROUP,'CurrentStage')==23
  capture.snap(c.window,'mario-arrival');c.window.key('q');pump(c,.6);assert not any(o['name']=='Player' for o in objects(c.window.reader));c.window.key('r');pump(c,.8);assert any(o['name']=='Player' for o in objects(c.window.reader));report['death_retry_after_exit']=True;report['passed']=True
 finally:
  subprocess.run(['xdotool','keyup','x','Left','Right'],check=True);c.close();(OUT/'mario-complete-live.json').write_text(json.dumps(report,indent=2)+'\n')
