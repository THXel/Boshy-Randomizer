"""Capture real engine phase transitions after explicitly documented test fixtures."""
from pathlib import Path
import argparse,json,subprocess,time,os
from Xlib import X,display
from PIL import Image
from phase_state import State
p=argparse.ArgumentParser();p.add_argument('case');p.add_argument('--seconds',type=float,default=65);p.add_argument('--label',default='');a=p.parse_args()
ROOT=Path(__file__).resolve().parents[2];out=ROOT/'outputs/Fusion-Phases-20261023'/(a.case+a.label)
out.mkdir(parents=True,exist_ok=False)
rows=[r.split(None,4) for r in subprocess.check_output(['wmctrl','-lp'],text=True).splitlines() if r.endswith(' I Wanna Be The Boshy')];assert len(rows)==1
wid=rows[0][0];pid=rows[0][2];expected=Path('/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshySceneTests')/a.case
assert Path(os.readlink(f'/proc/{pid}/cwd'))==expected
subprocess.run(['wmctrl','-ia',wid],check=True);D=display.Display();w=D.create_resource_object('window',int(wid,16));g=w.get_geometry();root=D.screen().root.get_geometry();r=D.screen().root.translate_coords(w,0,0)
park=max([(5,5),(root.width-5,5),(5,root.height-5),(root.width-5,root.height-5)],key=lambda p:(p[0]-r.x-g.width/2)**2+(p[1]-r.y-g.height/2)**2)
subprocess.run(['xdotool','mousemove',*map(str,park)],check=True)
def key(k):
 subprocess.run(['xdotool','keydown',k],check=True);time.sleep(.2);subprocess.run(['xdotool','keyup',k],check=True)
def shot(name):
 im=w.get_image(0,0,g.width,g.height,X.ZPixmap,0xffffffff);Image.frombytes('RGB',(g.width,g.height),im.data,'raw','BGRX').save(out/name)
s=State(a.case);report={'case':a.case,'scope':'Temporary HP and player-position fixtures; Die calls disabled only in private process; sprite randomizer OFF','samples':[],'writes':s.writes,'run':s.run}
try:
 report['protection_before_restart']=s.protect();key('r');time.sleep(.6);report['protection_after_restart']=s.protect();time.sleep(.5)
 obs=s.objects();players=[o for o in obs if o['name']=='Player']
 if not players:
  key('r');time.sleep(.5);s.protect();obs=s.objects();players=[o for o in obs if o['name']=='Player']
 assert len(players)==1,('player absent',[(o['oi'],o['name']) for o in obs])
 bossname='randomness' if 'solgryn' in a.case else 'Active 4sonic';boss=next(o for o in obs if o['name']==bossname)
 report['difficulty']=0;report['hp_fixture']=0 if 'solgryn' in a.case else 35;report['boss_before']=s.values(boss);s.set_value(boss,3 if 'solgryn' in a.case else 1,0 if 'solgryn' in a.case else 35)
 if 'sonic' in a.case:s.position(players[0],320,400)
 start=time.monotonic();entered=False
 while time.monotonic()-start<a.seconds:
  obs=s.objects();boss=next((o for o in obs if o['name']==bossname),None);vals=s.values(boss) if boss else []
  player=next((o for o in obs if o['name']=='Player'),None)
  if 'solgryn' in a.case and vals and vals[0]==5999 and not entered:
   assert player;s.position(player,300,-8);entered=True;report['climb_entry']={'phase':5999,'x':300,'y':-8}
  name=f'frame-{len(report["samples"]):03}.png';shot(name)
  row={'seconds':round(time.monotonic()-start,3),'boss_values':vals,'player':player,'objects':[o for o in obs if ('sonic' in o['name'].lower() or ('solgryn' in a.case and o['name'] in ('Active 9','Active 10','Active 14','randomness')))],'image':name}
  report['samples'].append(row);(out/'result.json').write_text(json.dumps(report,indent=2))
  if len(report['samples'])%10==0:print(a.case,row['seconds'],vals,'player',bool(player),'entry',entered,flush=True)
  time.sleep(.3)
 report['complete']=True;report['climb_entered']=entered;(out/'result.json').write_text(json.dumps(report,indent=2));print('DONE',a.case,len(report['samples']),flush=True)
finally:
 (out/'result.json').write_text(json.dumps(report,indent=2));s.close();subprocess.run(['wmctrl','-ic',wid])
