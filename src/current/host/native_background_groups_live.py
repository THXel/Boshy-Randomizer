"""Exercise all nine complete background sets in nine native worlds, one game at a time."""
import json,time,uuid
from functools import partial
from native_menu import builds
from menu_host.store import Store,digest
from pathlib import Path
from visuals import background_groups as bg
from export_route_probe import ROOT
OUT=ROOT/'outputs/Fusion-BackgroundGroups-20261026'
builds.DYNAMIC_BASE=builds.PREFIX/'drive_c/BoshyTransitions/Boshy-dynamic-v39.exe'
builds.DYNAMIC_SHA=digest(builds.DYNAMIC_BASE)
from export_native_run import export
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu.observe import objects
from visuals.scenery_pack import App
NAMES=App(builds.DYNAMIC_BASE).payload(0x2254).decode("utf-16le").split("\0")
IDS={n:i for i,n in enumerate(NAMES) if n.startswith(bg.PREFIX)}
from native_menu_probe import pump
from native_classic_live import wait
import god_mode_live as capture
capture.OUT=OUT
STAGES=['save1.ini','save2.ini','save3.ini','save6.ini','save9.ini','save10.ini','save12.ini','save13.ini','save15.ini']
SOURCES=[8,0,5,1,3,4,7,2,6]
report=dict(build=str(builds.DYNAMIC_BASE),sha256=builds.DYNAMIC_SHA,cases=[],memory_writes=0)
def helpers(c):return [o for o in objects(c.window.reader,types=(2,48)) if o['oi'] in IDS.values()]
try:
 for batch in range(3):
  store=Store(OUT/('groups-'+uuid.uuid4().hex[:8]),exporter=partial(export,dynamic=True))
  with store.lock():
   for slot in (1,2,3):
    target=batch*3+slot-1;source=SOURCES[target]
    seed=next('BGROUP'+str(i) for i in range(2000) if bg.mapping('BGROUP'+str(i),True)[target]==source)
    d=Draft();d.set_mode('level_rush');d.update(level_pool=[STAGES[target]],level_count=1,boss_pool=[],route_boss_count=0,
        no_mouse_ghost=True,god_mode=True,characters=False,sprite_scenery=True,sprite_backgrounds=True,
        sprite_decor=True,sprite_tiles=True,sprite_actors=True,sprite_dim=20)
    d.seed=seed;store.create(slot,d)
   c=CombinedController(store,dynamic=True)
   try:
    c.open();c.enter();pump(c,1);capture.snap(c.window,'v39-title-batch'+str(batch))
    for slot in (1,2,3):
     target=batch*3+slot-1;source=SOURCES[target]
     c.model.slot=slot;c.model.load_slot();c.mail.publish();c.begin();wait(c,lambda:c.phase=='playing',seconds=30);pump(c,1)
     expected={IDS[bg.PREFIX+str(i['object'])] for i in bg.catalogue()['sets'][source]['instances']}
     actual=helpers(c)
     if {o['oi'] for o in actual}!=expected:
      capture.snap(c.window,'group-failure')
      (OUT/'group-failure.json').write_text(json.dumps(dict(frame=c.window.reader.frame(),objects=objects(c.window.reader,types=(2,48))),indent=2))
     assert {o['oi'] for o in actual}==expected,(target,source,expected,actual)
     first=[(o['name'],o['x'],o['y']) for o in actual]
     capture.snap(c.window,'group-'+str(target)+'-source-'+str(source))
     c.window.key('Right');pump(c,1)
     later=[(o['name'],o['x'],o['y']) for o in helpers(c)]
     clouds=any(bg.catalogue()['objects'][i['object']]['cloud'] for i in bg.catalogue()['sets'][source]['instances'])
     if clouds and first==later:
      print('FOREGROUND',[(o['name'],o['x'],o['y']) for o in objects(c.window.reader) if o['name']=='Player'],flush=True)
      capture.snap(c.window,'cloud-stall')
      (OUT/'cloud-stall.json').write_text(json.dumps(dict(first=first,later=later,objects=helpers(c)),indent=2))
     if clouds:assert first!=later,('Foreign clouds are frozen',first,later)
     assert any(o['name']=='Player' for o in objects(c.window.reader))
     c.window.key('q');pump(c,.7);assert not any(o['name']=='Player' for o in objects(c.window.reader))
     c.window.key('r');pump(c,1)
     assert {o['oi'] for o in helpers(c)}==expected
     assert any(o['name']=='Player' for o in objects(c.window.reader))
     c.window.key('F2');wait(c,lambda:c.phase=='menu');c.enter()
     report['cases'].append(dict(target=target,source=source,frame=bg.catalogue()['sets'][target]['scene']+1,
        objects=sorted(expected),clouds_moving=clouds,death_retry=True,f2=True))
     (OUT/'groups-v39-live.json').write_text(json.dumps(report,indent=2)+'\n')
     print('PASS whole background',target,'from',source,flush=True)
   finally:c.close()
 report['passed']=True
finally:(OUT/'groups-v39-live.json').write_text(json.dumps(report,indent=2)+'\n')
