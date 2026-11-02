import io,json,uuid
from functools import partial
from native_menu import builds
from menu_host.store import Store,save,digest,RC4
builds.DYNAMIC_BASE=builds.PREFIX/'drive_c/BoshyTransitions/Boshy-dynamic-v28.exe'
builds.DYNAMIC_SHA=digest(builds.DYNAMIC_BASE)
from export_native_run import export
from export_route_probe import ROOT
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu.observe import objects
from native_menu_probe import pump
from native_menu_lifecycle_probe import wait_for
from god_mode_boss_probe import values
from transition.router import GROUP
import god_mode_live as capture
out=ROOT/'outputs/Fusion-Completion-20261026';capture.OUT=out
s=Store(out/('result-'+uuid.uuid4().hex[:8]),exporter=partial(export,dynamic=True))
with s.lock():
 d=Draft();d.set_mode('normal');d.update(god_mode=True,no_mouse_ghost=True,characters=False);s.create(1,d)
 p=s.folder(1)/'SaveFile1.ini';cfg=save(p);cfg['Positions'].update(frame='49',xpos='320',ypos='240');cfg[GROUP]['Completed']='1';b=io.StringIO();cfg.write(b);p.write_bytes(RC4(b'BLOB',b.getvalue().encode('latin1')))
 c=CombinedController(s,dynamic=True)
 try:
  c.open();c.enter();c.model.slot=1;c.model.load_slot();c.begin();wait_for(c,lambda:c.phase=='playing',seconds=25);pump(c,1)
  print(c.window.reader.frame(),c.completion.data,c.completion.last_error,flush=True)
  obs=objects(c.window.reader,types=(2,33))
  selected=[]
  for o in obs:
   if o['name'].startswith('Run Result'):
    if 'Panel' in o['name']:o['values']=values(c.window.reader,o,4)
    selected.append(o)
  print(selected,flush=True);capture.snap(c.window,'result-debug')
  (out/'result-debug-objects.json').write_text(json.dumps(selected,indent=2))
  c.window.key('F2');pump(c,1)
 finally:c.close()
