"""Touch a real portal from a staged closed save; no live memory writes."""
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
from native_rewards_live import write_save
from native_menu.observe import objects
from transition.router import GROUP
import god_mode_live as capture
capture.OUT=OUT
s=Store(OUT/('portal-'+uuid.uuid4().hex[:8]),exporter=partial(export,dynamic=True))
report=dict(build=str(builds.DYNAMIC_BASE),sha256=builds.DYNAMIC_SHA,scope=__doc__,memory_writes=0)
with s.lock():
 d=Draft();d.set_mode('level_rush');d.update(level_pool=['save1.ini'],level_count=1,boss_pool=[],route_boss_count=0,no_mouse_ghost=True,god_mode=True,characters=False)
 d.seed='PORTAL-CHECKPOINT';s.create(1,d)
 p=s.folder(1)/'SaveFile1.ini';cfg=save(p);cfg['Positions']['xPos']='3352';cfg['Positions']['yPos']='1170';write_save(p,cfg)
 report['before']=dict(cfg[GROUP]);report['checkpoint']=dict(cfg['Positions'])
 c=CombinedController(s,dynamic=True)
 try:
  c.open();c.enter();c.model.slot=1;c.model.load_slot();c.begin();wait(c,lambda:c.phase=='playing');pump(c,.4)
  capture.snap(c.window,'portal-before')
  end=time.monotonic()+12
  while time.monotonic()<end:
   pump(c,.15);cfg=save(c.folder/'SaveFile1.ini')
   if cfg.getint(GROUP,'BlockedPortal',fallback=0)==29:break
  report['after']=dict(cfg[GROUP]);report['positions']=dict(cfg['Positions']);report['frame']=c.window.reader.frame();report['player']=[o for o in objects(c.window.reader) if o['name']=='Player']
  capture.snap(c.window,'portal-after')
  assert cfg.getint(GROUP,'BlockedPortal',fallback=0)==29,report
  assert report['after']['currentstage']==report['before']['currentstage']
  assert {k:v for k,v in report['after'].items() if k.startswith('done')}=={k:v for k,v in report['before'].items() if k.startswith('done')}
  assert cfg.getint('Positions','frame')==3
  assert report['frame']=='First World - Prehistorik'
  assert report['positions']['xpos']=='3352' and report['positions']['ypos']=='1170'
  report['passed']=True;print('PASS portal returns to checkpoint, no route progress',flush=True)
 finally:
  c.close();(OUT/'portal-guard-live.json').write_text(json.dumps(report,indent=2)+'\n')
