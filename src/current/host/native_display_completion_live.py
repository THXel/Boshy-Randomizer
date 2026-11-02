"""Real native F4 and Ctrl+Alt+D checks on the isolated candidate process."""
import json,time,uuid,subprocess
from functools import partial
from pathlib import Path
from native_menu import builds
from menu_host.store import Store,digest,save
builds.DYNAMIC_BASE=builds.PREFIX/'drive_c/BoshyTransitions/Boshy-dynamic-v34.exe'
builds.DYNAMIC_SHA=digest(builds.DYNAMIC_BASE)
from export_native_run import export
from export_route_probe import ROOT
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu.display import Settings
from native_menu_probe import pump
from native_menu_lifecycle_probe import wait_for
from native_classic_live import enter_title, trigger, wait
from Xlib import display as xd
import god_mode_live as capture
out=ROOT/'outputs/Fusion-Completion-20261026';capture.OUT=out
report=dict(build=str(builds.DYNAMIC_BASE),sha256=builds.DYNAMIC_SHA,cases=[])
s=Store(out/('display-'+uuid.uuid4().hex[:8]),exporter=partial(export,dynamic=True))

def geometry(c):
 d=xd.Display()
 try:
  w=d.create_resource_object('window',int(c.window.window,16));g=w.get_geometry();p=d.screen().root.translate_coords(w,0,0)
  return [p.x,p.y,g.width,g.height]
 finally:d.close()

with s.lock():
 d=Draft();d.set_mode('normal');d.update(god_mode=True,no_mouse_ghost=True,characters=False);s.create(1,d)
 c=CombinedController(s,dynamic=True)
 try:
  c.open();enter_title(c);pump(c,9)
  if trigger(c)[1]!=-1:c.window.key('Return');wait(c,lambda:trigger(c)[1]==-1)
  seed=c.model.draft.shared();c.window.key('F4');pump(c,1)
  assert c.model.display.fullscreen,c.model.display
  g=geometry(c);assert abs(g[2]-g[3]*4/3)<2,g
  report['cases'].append(dict(aspect='4:3',geometry=g,state=c.display_state))
  capture.snap(c.window,'fullscreen-4-3')
  c.window.key('Down');pump(c,.2);c.window.key('Return');wait(c,lambda:c.window.reader.frame()=='Options');pump(c,.5)
  for _ in range(4):c.window.key('Down');pump(c,.25)
  c.window.key('Return');pump(c,.8)
  assert c.model.display.aspect=='16:9',c.model.display
  g=geometry(c);assert abs(g[2]-g[3]*16/9)<2,g
  assert c.window.presentation_backing.shown
  report['cases'].append(dict(aspect='16:9',geometry=g,state=c.display_state,native_options=True))
  capture.snap(c.window,'fullscreen-16-9')
  c.window.key('Escape');wait(c,lambda:c.window.reader.frame()=='Title Screen');pump(c,.4)
  c.window.key('ctrl+alt+d');pump(c,.7)
  assert c.diagnostics.root is not None
  diag=c.diagnostics.root
  diag.lift();diag.focus_force();pump(c,.5)
  assert not c.window.presentation_backing.shown
  report['diagnostics']=json.loads(c.diagnostics.text)
  subprocess.run(['import','-window',str(diag.winfo_id()),str(out/'diagnostics.png')],check=True)
  c.diagnostics.close();c.window.key('F4');pump(c,.7)
  assert not c.model.display.fullscreen
  assert getattr(c.window,'presentation_backing',None) is None
  assert c.model.draft.shared()==seed
  c.enter();c.model.slot=1;c.model.load_slot();c.begin();wait_for(c,lambda:c.phase=='playing',seconds=25)
  c.window.key('F4');pump(c,.7);assert c.model.display.fullscreen
  before=geometry(c);c.window.key('q');pump(c,.4);c.window.key('r');pump(c,.6)
  assert geometry(c)==before,(geometry(c),before)
  c.window.key('F2');wait_for(c,lambda:c.phase=='menu',seconds=10)
  assert geometry(c)==before
  c.window.key('F4');pump(c,.5);assert not c.model.display.fullscreen
  report['passed']=True
 except BaseException as error:
  report['error']=repr(error);raise
 finally:
  try:c.close()
  finally:(out/'display-v34-live.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS display and diagnostics',flush=True)
