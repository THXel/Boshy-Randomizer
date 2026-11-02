"""Exercise the ORIGINAL, unrouted Mario pipe completion as a bounded fixture."""
import argparse,json,subprocess,time,runpy
from pathlib import Path
from Xlib import display,X
from PIL import Image
from phase_state import State
p=argparse.ArgumentParser();p.add_argument('case');p.add_argument('label');a=p.parse_args()
R=Path(__file__).resolve().parents[2];out=R/'outputs/Fusion-FrameLinks-20261023'/a.label;out.mkdir()
rows=[r.split(None,4) for r in subprocess.check_output(['wmctrl','-lp'],text=True).splitlines() if r.endswith(' I Wanna Be The Boshy')];assert len(rows)==1
wid=rows[0][0];subprocess.run(['wmctrl','-ia',wid]);subprocess.run(['xdotool','mousemove','5','5'])
s=State(a.case);report={'case':a.case,'writes':s.writes}
rc=runpy.run_path(str(R/'work/Boshy-Randomizer/src/shared/PY/rc4_utils.py'))['rc4_crypt'];save=Path('/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshySceneTests')/a.case/'SaveFile1.ini'
def read():return rc(b'BLOB',save.read_bytes()).decode('latin1')
try:
 assert 'MarioRoute' not in read()
 s.protect();subprocess.run(['xdotool','keydown','r']);time.sleep(.2);subprocess.run(['xdotool','keyup','r']);time.sleep(.4);s.protect()
 pipe=next(o for o in s.objects() if o['name']=='Active 27');report['before']=read();s.set_value(pipe,0,50);time.sleep(1.2)
 report['after']=read();report['objects']=[dict(o,values=s.values(o,3)) for o in s.objects()]
 w=display.Display().create_resource_object('window',int(wid,16));g=w.get_geometry();im=w.get_image(0,0,g.width,g.height,X.ZPixmap,0xffffffff);Image.frombytes('RGB',(g.width,g.height),im.data,'raw','BGRX').save(out/'arrival.png')
 print(report['after'])
finally:
 (out/'result.json').write_text(json.dumps(report,indent=2));s.close();subprocess.run(['wmctrl','-ic',wid])
