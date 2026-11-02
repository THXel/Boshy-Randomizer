"""Real keyboard-held firing and cursor contact, without game memory writes."""
import json,time,subprocess
from pathlib import Path
from menu_host.store import Store
from menu_host.draft import Draft
from menu_host.runtime import Runtime, windows
from menu_host.processes import games
from god_mode_live import objects, point
import god_mode_live as capture
from god_mode_boss_probe import values
from export_route_probe import ROOT

OUT=ROOT/'outputs/Fusion-Controls-20261024'
capture.OUT=OUT

def firing(r, name, expected):
    subprocess.run(['wmctrl','-ia',r.window],check=True)
    subprocess.run(['xdotool','mousemove','1910','1040'],check=True)
    subprocess.run(['xdotool','keydown','x'],check=True)
    samples=[]
    start=time.monotonic()
    try:
        for i in range(16):
            time.sleep(.2)
            obs=objects(r.reader)
            bullets=[o for o in obs if o['name']=='Bullet 2']
            assert any(o['name']=='Player' for o in obs)
            samples.append(dict(time=time.monotonic()-start,bullets=len(bullets)))
        capture.snap(r,name+'-held')
    finally:
        subprocess.run(['xdotool','keyup','x'],check=True)
    time.sleep(1.2)
    after=[o for o in objects(r.reader) if o['name']=='Bullet 2']
    late=[s['bullets'] for s in samples if s['time']>1.5]
    assert late and (sum(n>0 for n in late)>=len(late)//2 if expected else not any(late)),samples
    assert not after,after
    return dict(samples=samples,after_release=len(after))

def main():
    report=dict(scope=__doc__,memory_writes=0,cases=[])
    # Separate three-slot profiles keep every test artifact reviewable.
    cases=[('normal-off',1,False,False),('normal-on',1,True,True),
           ('ez-off',0,False,True),('hardon-on',3,True,True)]
    for name,difficulty,autofire,disabled in cases:
        s=Store(OUT/(name+'-profile'))
        with s.lock():
            if not s.current(1):
                d=Draft();d.update(level_pool=['save1.ini'],level_count=1,boss_pool=['hellokitty'],route_boss_count=1,
                                  difficulty=difficulty,autofire=autofire,no_mouse_ghost=disabled)
                s.create(1,d)
            r=Runtime(s);case=dict(name=name,difficulty=difficulty,autofire=autofire,no_mouse_ghost=disabled)
            report['cases'].append(case)
            try:
                print('START',name,flush=True);r.start(1);time.sleep(1)
                case['fire']=firing(r,name,autofire or difficulty==0)
                obs=objects(r.reader);p=next(o for o in obs if o['name']=='Player')
                point(r,p['x'],p['y'])
                samples=[]
                for i in range(10):
                    time.sleep(.4);obs=objects(r.reader)
                    mouse=next((o for o in obs if o['name']=='mouse kill'),None)
                    samples.append(dict(alive=any(o['name']=='Player' for o in obs),charge=values(r.reader,mouse,1)[0] if mouse else None))
                assert samples[-1]['alive']==disabled,samples
                if disabled:assert all(v['charge'] is None for v in samples),samples
                capture.snap(r,name+'-mouse');case['mouse']=samples
                if disabled:
                    r.key('q');time.sleep(.6)
                    assert not any(o['name']=='Player' for o in objects(r.reader))
                r.key('r');time.sleep(1)
                assert any(o['name']=='Player' for o in objects(r.reader))
                case['restart']=True;r.key('F2')
                end=time.monotonic()+15
                while time.monotonic()<end and r.poll()!='menu':time.sleep(.2)
                assert s.active is None and not windows() and not games()
                s.resume(1);case['passed']=True;print('PASS',name,flush=True)
            except BaseException as error:
                case['error']=repr(error)
                if r.window:
                    try:capture.snap(r,name+'-failure')
                    except Exception:pass
                raise
            finally:
                if s.active:r.close('controls-probe-cleanup')
                (OUT/'live-results.json').write_text(json.dumps(report,indent=2)+'\n')
    report['passed']=True;(OUT/'live-results.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
