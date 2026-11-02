"""Advance Mario's final native outro; let it reveal the pipe itself."""
from pathlib import Path
import sys,time,json,subprocess
from Xlib import display,X
from PIL import Image
from phase_state import State
out=Path(__file__).resolve().parents[2]/'outputs/Fusion-BossExits-20261023/mario-outro';out.mkdir(exist_ok=False)
s=State('rebuilt-mario-exit');report={'writes':s.writes,'samples':[]}
rows=[r.split(None,4) for r in subprocess.check_output(['wmctrl','-lp'],text=True).splitlines() if r.endswith(' I Wanna Be The Boshy')];assert len(rows)==1
wid=rows[0][0];subprocess.run(['wmctrl','-ia',wid]);subprocess.run(['xdotool','mousemove','5','5'])
D=display.Display();w=D.create_resource_object('window',int(wid,16));g=w.get_geometry()
def shot(name):
 i=w.get_image(0,0,g.width,g.height,X.ZPixmap,0xffffffff);Image.frombytes('RGB',(g.width,g.height),i.data,'raw','BGRX').save(out/(name+'.png'))
try:
 s.protect();obs=s.objects();boss=next(o for o in obs if o['name']=='Classic Mario 3')
 flags=boss['ptr']+boss['rel']+104;old=s.b.u32(flags);s.cas(flags,old,old|1,'activate final Mario timer for outro fixture')
 s.set_value(boss,0,949)
 for tick in range(85):
  time.sleep(.5);obs=s.objects();boss=next((o for o in obs if o['name']=='Classic Mario 3'),None);pipe=next((o for o in obs if o['name']=='Active 27'),None)
  row={'seconds':tick*.5,'boss':s.values(boss,3) if boss else None,'pipe':pipe};report['samples'].append(row)
  if tick%10==0:shot('outro-'+str(tick));print(row['seconds'],row['boss'],pipe['x'] if pipe else None,flush=True)
  if not boss and pipe and pipe['x']<=600:
   shot('revealed');player=next(o for o in obs if o['name']=='Player');s.position(player,pipe['x']+16,431)
   for i in range(20):
    time.sleep(.15);ps=[o for o in s.objects() if o['name']=='Active 27'];report.setdefault('pipe_timer',[]).append(s.values(ps[0],1)[0] if ps else None)
    if not ps:break
   shot('after-entry');report['native_pipe_revealed']=True;break
 print('RESULT',report.get('native_pipe_revealed'),report.get('pipe_timer'),flush=True)
finally:
 (out/'result.json').write_text(json.dumps(report,indent=2));s.close()
