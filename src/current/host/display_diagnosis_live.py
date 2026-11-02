import json,uuid,time
from native_menu import builds
from menu_host.store import Store,digest
builds.DYNAMIC_BASE=builds.PREFIX/'drive_c/BoshyTransitions/Boshy-dynamic-v34.exe';builds.DYNAMIC_SHA=digest(builds.DYNAMIC_BASE)
from native_menu.combined import CombinedController
from native_menu.display import Settings,from_options
from native_menu_probe import pump
from native_menu.preferences import read_native_settings
from export_route_probe import ROOT
from Xlib import display
out=ROOT/'outputs/Fusion-Completion-20261026'
s=Store(out/('display-diagnosis-'+uuid.uuid4().hex[:6]));report=[]
def geo(c):
 d=display.Display();w=d.create_resource_object('window',int(c.window.window,16));g=w.get_geometry();d.close();return [g.width,g.height]
with s.lock():
 c=CombinedController(s,dynamic=True)
 try:
  c.open();c.enter()
  for aspect in ('4:3','16:9'):
   c.model.display=Settings(aspect,480,True);c.action('display')
   report.append(dict(step=aspect,now=geo(c),display=str(c.model.display),options=dict(read_native_settings(c.folder/'options.ini')['Options']),applied=c.display_state))
   for i in range(5):
    pump(c,.2);report.append(dict(step=i,now=geo(c),display=str(c.model.display),options=dict(read_native_settings(c.folder/'options.ini')['Options'])))
 finally:
  c.close();(out/'display-diagnosis.json').write_text(json.dumps(report,indent=2))
