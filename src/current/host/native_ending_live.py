"""Observe the original ending timer and credits, using only an isolated completed save."""
import io,json,time,uuid,subprocess
from functools import partial
from native_menu import builds
from menu_host.store import Store,save,digest,RC4
builds.DYNAMIC_BASE=builds.PREFIX/'drive_c/BoshyTransitions/Boshy-dynamic-v34.exe'
builds.DYNAMIC_SHA=digest(builds.DYNAMIC_BASE)
from export_native_run import export
from export_route_probe import ROOT
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu.results import CLOSE_BOUNDS
from native_menu.transport import read
from native_menu.observe import objects
from native_menu_probe import pump
from native_menu_lifecycle_probe import wait_for
from god_mode_boss_probe import values
from transition.router import GROUP
from Xlib import display as xd
import god_mode_live as capture
out=ROOT/'outputs/Fusion-Completion-20261026';capture.OUT=out
report=dict(build=str(builds.DYNAMIC_BASE),sha256=builds.DYNAMIC_SHA,
            fixture='isolated completed save entering original ending frame 47',memory_writes=0)
s=Store(out/('ending-'+uuid.uuid4().hex[:8]),exporter=partial(export,dynamic=True))
with s.lock():
 d=Draft();d.set_mode('normal');d.update(god_mode=True,no_mouse_ghost=True,characters=False);s.create(1,d)
 path=s.folder(1)/'SaveFile1.ini';cfg=save(path);cfg['Positions'].update(frame='47',xpos='320',ypos='240');cfg[GROUP]['Completed']='1';stream=io.StringIO();cfg.write(stream);path.write_bytes(RC4(b'BLOB',stream.getvalue().encode('latin1')))
 c=CombinedController(s,dynamic=True)
 try:
  c.open();c.enter();c.model.slot=1;c.model.load_slot();c.begin();wait_for(c,lambda:c.phase=='playing',seconds=25)
  assert c.window.reader.frame()=='Frame 49';pump(c,1)
  assert c.completion.data is not None and not c.completion.visible
  capture.snap(c.window,'ending-early-no-result')
  started=time.monotonic();first=None
  while time.monotonic()-started<24:
   c.tick()
   try:frame=c.window.reader.frame()
   except RuntimeError:
    time.sleep(.04);continue
   if frame!='Frame 49':break
   try:
    timer=next(o for o in objects(c.window.reader) if o['name']=='randomness')
    value=values(c.window.reader,timer,1)[0]
   except (RuntimeError,StopIteration):
    time.sleep(.04);continue
   if value<745:assert not c.completion.visible,value
   if c.completion.visible and first is None:
    first=value;pump(c,.3);capture.snap(c.window,'ending-rainbow-result');report['reveal_counter']=value
   time.sleep(.04)
  assert first is not None and first>=750,first
  wait_for(c,lambda:c.window.reader.frame()=='Credits',seconds=10);pump(c,.8)
  assert c.completion.visible;capture.snap(c.window,'credits-result')
  panel=next(o for o in objects(c.window.reader) if o['name']=='Run Result Panel')
  report['credits_panel']={**panel,'values':values(c.window.reader,panel,4)}
  from PIL import Image
  im=Image.open(out/'credits-result.png').convert('RGB')
  assert any(im.getpixel((x,186))[1] > 100 for x in range(190,620)), 'Result border not visible in credits'
  c.window.key('F6');pump(c,.4);assert c.completion.copy_sequence==1
  # Actual close button at scaled window coordinates.
  dx=xd.Display();g=dx.create_resource_object('window',int(c.window.window,16)).get_geometry();dx.close()
  x=(CLOSE_BOUNDS[0]+CLOSE_BOUNDS[2])*g.width//1280
  y=(CLOSE_BOUNDS[1]+CLOSE_BOUNDS[3])*g.height//960
  subprocess.run(['wmctrl','-ia',c.window.window],check=True);time.sleep(.2)
  subprocess.run(['xdotool','mousemove','--window',c.window.window,str(x),str(y),'click','1'],check=True)
  pump(c,.6);assert c.completion.dismissed
  assert read(c.folder/'results-view.ini')['ready']==0
  capture.snap(c.window,'credits-result-closed')
  assert c.window.reader.frame()=='Credits'
  player=next(o for o in objects(c.window.reader) if o['name']=='Player');before=player['x']
  c.window.key('Right');pump(c,.2)
  after=next(o for o in objects(c.window.reader) if o['name']=='Player')['x']
  assert after!=before,(before,after)
  report['playable_after_close']=dict(before=before,after=after)
  c.window.key('F2');wait_for(c,lambda:c.phase=='menu',seconds=10)
  assert not c.completion.visible and not c.completion.dismissed
  report['f2_reset']=True;report['passed']=True
 except BaseException as error:report['error']=repr(error);raise
 finally:
  try:c.close()
  finally:(out/'ending-v34-live.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS rainbow, credits, close and F2',flush=True)
