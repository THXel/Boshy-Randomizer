"""Use native Options keys, restart and one unchanged run to verify global presentation."""
import json,time,uuid
from functools import partial
from native_menu import builds
from menu_host.store import Store,digest
from native_menu.preferences import read_native_settings as save
builds.DYNAMIC_BASE=builds.PREFIX/'drive_c/BoshyTransitions/Boshy-dynamic-v34.exe'
builds.DYNAMIC_SHA=digest(builds.DYNAMIC_BASE)
from export_native_run import export
from export_route_probe import ROOT
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu.presentation import PACKS
from native_menu.preferences import LANGUAGES
from native_menu.observe import objects
from native_menu_probe import pump
from native_classic_live import enter_title,trigger,wait
import god_mode_live as capture
OUT=ROOT/'outputs/Fusion-Completion-20261026';capture.OUT=OUT
report=dict(build=str(builds.DYNAMIC_BASE),sha256=builds.DYNAMIC_SHA,cases=[],memory_writes=0)
s=Store(OUT/('presentation-'+uuid.uuid4().hex[:8]),exporter=partial(export,dynamic=True))

def original_menu(c):
 enter_title(c);pump(c,9)
 if trigger(c)[1]!=-1:c.window.key('Return');wait(c,lambda:trigger(c)[1]==-1)

def open_options(c):
 c.window.key('Down');pump(c,.3);c.window.key('Return');wait(c,lambda:c.window.reader.frame()=='Options');pump(c,.5)

with s.lock():
 d=Draft();d.set_mode('normal');d.update(no_mouse_ghost=True,characters=False);s.create(1,d)
 immutable=(s.folder(1)/'plan.json').read_bytes(); seed=d.shared()
 c=CombinedController(s,dynamic=True)
 try:
  c.open();original_menu(c)
  initial=save(c.folder/'options.ini').getint('Options','IntroVariant');report['intro_initial']=initial
  capture.snap(c.window,'presentation-title')
  open_options(c)
  capture.snap(c.window,'presentation-options-initial')
  lang=LANGUAGES[(LANGUAGES.index(c.model.language)+1)%len(LANGUAGES)]
  c.window.key('Right');pump(c,.8)
  assert c.model.language==lang,(c.model.language,lang)
  assert json.loads(c.tracker.path.read_text())["language"]==lang
  capture.snap(c.window,'presentation-options-language')
  for _ in range(3):c.window.key('Down');pump(c,.25)
  c.window.key('Right');pump(c,.8)
  assert c.presentation.pack=='kamilia3',c.presentation.pack
  capture.snap(c.window,'presentation-options-kamilia')
  # Original sliders remain functional in their new positions.
  c.window.key('Up');pump(c,.2);c.window.key('Up');pump(c,.2)
  c.window.key('Left');pump(c,.4)
  volume=save(c.folder/'options.ini').getint('Options','MusicVolume');assert volume<100
  c.window.key('Escape');wait(c,lambda:c.window.reader.frame()=='Title Screen');pump(c,.4)
  assert save(c.folder/'options.ini').getint('Options','IntroVariant')==initial
  c.enter();pump(c,.4);capture.snap(c.window,'presentation-save-digits')
  c.model.go('cosmetics');c.mail.publish();pump(c,.4)
  art=(c.renderer.theme,c.renderer.cast,c.renderer.art_generation)
  for _ in range(3):
   c.model.draft.consume_seed();c.mail.publish();pump(c,.2)
   assert art==(c.renderer.theme,c.renderer.cast,c.renderer.art_generation)
  c.model.go('home');c.model.slot=1;c.model.load_slot();c.mail.publish();c.begin()
  wait(c,lambda:c.phase=='playing',seconds=25);pump(c,1)
  assert c.presentation.music['Enabled']==1
  assert c.model.draft.shared()==seed
  c.window.key('q');pump(c,.6)
  panel=next(o for o in objects(c.window.reader) if o['name']=='Randomizer Death Screen')
  capture.snap(c.window,'presentation-kamilia-death')
  report['death_object']=panel
  c.window.key('r');pump(c,.5);c.window.key('F2');wait(c,lambda:c.phase=='menu');original_menu(c)
  changed=save(c.folder/'options.ini').getint('Options','IntroVariant')
  assert changed==(initial+1)%12,(initial,changed)
  assert (s.folder(1)/'plan.json').read_bytes()==immutable
  report.update(language=lang,pack=c.presentation.pack,volume=volume,intro_after_f2=changed,seed_unchanged=True)
  capture.snap(c.window,'presentation-title-restart')
 finally:
  try:c.close()
  finally:(OUT/'presentation-v34-live.json').write_text(json.dumps(report,indent=2)+'\n')
 # New host/process uses the user's durable choices.
 c=CombinedController(s,dynamic=True)
 try:
  assert c.model.language==lang and c.presentation.pack=='kamilia3'
  c.open();original_menu(c);open_options(c);pump(c,.3)
  capture.snap(c.window,'presentation-options-after-relaunch')
  report['relaunch_persisted']=True;report['passed']=True
 finally:
  try:c.close()
  finally:(OUT/'presentation-v34-live.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS presentation options, seed, death, intro and relaunch',flush=True)
