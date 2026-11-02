"""Exercise the native Cheetah exit; fixtures only advance victory and position Player."""
from pathlib import Path
import sys,time,json,subprocess,runpy,argparse,os
from Xlib import display,X
from PIL import Image
from phase_state import State
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--label',default='route1');p.add_argument('--case',choices=['rebuilt-cheetah','rebuilt-cheetah-seed','rebuilt-cheetah-exit','rebuilt-cheetah-links'],default='rebuilt-cheetah');p.add_argument('--output-group',default='Fusion-Transition-20261023');a=p.parse_args()
assert '/' not in a.output_group and '..' not in a.output_group
out=ROOT/'outputs'/a.output_group/a.label;out.mkdir(exist_ok=False)
rows=[l.split(None,4) for l in subprocess.check_output(['wmctrl','-lp'],text=True).splitlines() if l.endswith(' I Wanna Be The Boshy')];assert len(rows)==1
expected=Path('/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshySceneTests')/a.case
assert Path(os.readlink('/proc/'+rows[0][2]+'/cwd'))==expected
wid=rows[0][0];D=display.Display();w=D.create_resource_object('window',int(wid,16));g=w.get_geometry()
subprocess.run(['wmctrl','-ia',wid]);subprocess.run(['xdotool','mousemove','5','5'])
def key(k):
 subprocess.run(['wmctrl','-ia',wid]);time.sleep(.1)
 subprocess.run(['xdotool','keydown',k]);time.sleep(.2);subprocess.run(['xdotool','keyup',k])
def shot(name):
 i=w.get_image(0,0,g.width,g.height,X.ZPixmap,0xffffffff);Image.frombytes('RGB',(g.width,g.height),i.data,'raw','BGRX').save(out/(name+'.png'))
rc=runpy.run_path(str(ROOT/'work/Boshy-Randomizer/src/shared/PY/rc4_utils.py'))['rc4_crypt']
save=expected/'SaveFile1.ini'
def readsave():return rc(b'BLOB',save.read_bytes()).decode('latin1')
s=State(a.case);report={'window':wid,'pid':rows[0][2],'save_before':readsave(),'writes':s.writes,'samples':[]}
try:
 key('r');time.sleep(.5);key('q');time.sleep(.5)
 report['death_before_exit']={'player_present':any(o['name']=='Player' for o in s.objects()),'save':readsave()};shot('death-before-exit')
 s.protect();key('r');time.sleep(.6);s.protect()
 obs=s.objects();player=next(o for o in obs if o['name']=='Player');boss=next(o for o in obs if o['name']=='BossActions')
 if any(f'CheetahRoute={v}\r' in readsave() for v in (1,2)):
  hidden_exit=next(o for o in obs if o['name']=='Active 42')
  s.position(player,hidden_exit['x'],hidden_exit['y']);time.sleep(.3)
  report['hidden_exit_contact']={'boss_present':any(o['name']=='BossActions' for o in s.objects()),'save':readsave()}
  assert report['hidden_exit_contact']['boss_present'], 'Premature route before victory'
 s.position(player,511,376);time.sleep(.3)
 report['pre_victory']={'boss_present':any(o['name']=='BossActions' for o in s.objects()),'save':readsave()};shot('before-victory')
 s.set_value(boss,0,6499)
 for i in range(24):
  time.sleep(.5);obs=s.objects();b=next((o for o in obs if o['name']=='BossActions'),None)
  report['samples'].append({'t':(i+1)*.5,'boss':s.values(b,3) if b else None,'exit':[o for o in obs if o['name']=='Active 42'],'player':[o for o in obs if o['name']=='Player']})
  if i%4==0:shot(f'victory-{i:02}')
  if not b:break
 obs=s.objects();player=next((o for o in obs if o['name']=='Player'),None)
 if any(o['name']=='BossActions' for o in obs) and player:
  exitobj=next(o for o in obs if o['name']=='Active 42');s.position(player,exitobj['x'],exitobj['y']);time.sleep(1)
 shot('arrival');report['save_arrival']=readsave();report['arrival_objects']=[o['name'] for o in s.objects()]
 # A fresh scene must have unmodified Die calls. Q invokes the original death action.
 key('q');time.sleep(.8);shot('death');report['player_after_death']=any(o['name']=='Player' for o in s.objects())
 key('r');time.sleep(.7);shot('restart');report['save_restart']=readsave();report['restart_objects']=[o['name'] for o in s.objects()]
 report['same_process_at_end']=s.b.cmd('read '+format(s.b.ready['base'],'x')+' 2')['hex']=='4d5a'
 print(json.dumps({k:v for k,v in report.items() if k not in ('samples','writes','arrival_objects','restart_objects')}),flush=True)
finally:
 (out/'result.json').write_text(json.dumps(report,indent=2));s.close()
