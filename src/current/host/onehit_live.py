"""Native boss-hit probes: real shots, documented projectile-position fixtures.

No boss HP, event code, invulnerability state or victory flags are written.
The Solgryn case enters its native checkpoint via the private test save.
"""
import io,json,time,struct,sys
from pathlib import Path
from menu_host.store import Store,save,RC4
from menu_host.draft import Draft
from menu_host.runtime import Runtime
from transition.router import STAGES,GROUP
from god_mode_live import objects
from god_mode_boss_probe import values,cas,position
import god_mode_live as capture
from export_route_probe import ROOT
OUT=ROOT/'outputs/Fusion-OneHit-20261024'
capture.OUT=OUT

def shot(r,boss_name,index,case):
    obs=objects(r.reader);boss=next(o for o in obs if o['name']==boss_name)
    before=values(r.reader,boss,max(5,index+1))[index]
    r.key('x')
    obs=objects(r.reader);boss=next((o for o in obs if o['name']==boss_name),None)
    after=values(r.reader,boss,max(5,index+1))[index] if boss else 0
    if after!=before:return dict(before=before,after=after,fixture=False)
    bullets=[o for o in obs if o['name']=='Bullet 2']
    if not bullets or not boss:return dict(before=before,after=after,miss=True)
    bullet=bullets[0]
    for offset,key in ((84,'y'),(76,'x')):
        for attempt in range(8):
            assert r.reader.u32(bullet['ptr']+18)&65535==bullet['oi']
            if cas(r,bullet['ptr']+offset,boss[key],'projectile contact fixture',case['writes']):break
        else:raise RuntimeError('Moving projectile fixture')
    time.sleep(.25)
    obs=objects(r.reader);boss=next((o for o in obs if o['name']==boss_name),None)
    after=values(r.reader,boss,max(5,index+1))[index] if boss else 0
    return dict(before=before,after=after,fixture=True)

def hit(r,boss_name,index,target,case):
    for attempt in range(300):
        obs=objects(r.reader);boss=next(o for o in obs if o["name"]==boss_name)
        if not (0 <= boss["x"] <= 640 and 0 <= boss["y"] <= 480):
            time.sleep(.4);continue
        result=shot(r,boss_name,index,case);case['shots'].append(result)
        print('SHOT',case['name'],result,flush=True)
        if result['after']!=result['before']:
            assert result['after']==target,(result,target)
            return result
        time.sleep(.3)
    raise AssertionError('No vulnerable hit reached')

def main():
    report=json.loads((OUT/'live-results.json').read_text()) if len(sys.argv)>1 and (OUT/'live-results.json').exists() else dict(scope=__doc__,cases=[])
    report['cases']=[c for c in report['cases'] if c.get('passed') and c['name'] not in sys.argv[1:]]
    cases=[('kitty-off','hellokitty','hellokitty',1,False),('kitty-on','hellokitty','hellokitty',1,True),
           ('sonic','sonic','Active 4sonic',1,True),('oldsonic','oldsonic','Active 4sonic',1,True),
           ('solgryn',None,'randomness',3,True),('mario','mario','Classic Mario',3,True)]
    for name,key,boss_name,index,enabled in cases:
        if len(sys.argv)>1 and name not in sys.argv[1:]:continue
        s=Store(OUT/(name+'-profile'))
        with s.lock():
            if not s.current(1):
                d=Draft();d.update(level_pool=[],level_count=0,boss_pool=[key or 'hellokitty'],route_boss_count=1,
                                  difficulty=1,god_mode=True,no_mouse_ghost=True,one_hp=enabled,
                                  sprite_scenery=True,sprite_actors=True,sprite_tiles=True,music=True)
                d.select_pack('music_pack','kamilia3');d.select_pack('blood_pack','wannafest22');s.create(1,d)
                if key is None:
                    path=s.folder(1)/'SaveFile1.ini';c=save(path);stage=STAGES['boss_solgryn.ini']
                    c[GROUP]['CurrentStage']=str(stage['id'])
                    for a,b in [('frame','frame'),('xpos','x'),('ypos','y')]:c['Positions'][a]=str(stage[b])
                    buf=io.StringIO();c.write(buf);path.write_bytes(RC4(b'BLOB',buf.getvalue().encode('latin1')))
            r=Runtime(s);case=dict(name=name,enabled=enabled,writes=[],shots=[],samples=[]);report['cases'].append(case)
            try:
                print('START',name,flush=True);case['frame']=r.start(1);time.sleep(1)
                r.key('s');time.sleep(.5)
                obs=objects(r.reader);boss=next(o for o in obs if o['name']==boss_name)
                initial=values(r.reader,boss)[index];case['initial_hp']=initial
                target=90 if name in ('sonic','oldsonic') else 0 if enabled else initial-1
                hit(r,boss_name,index,target,case)
                capture.snap(r,name+'-first-hit')
                if name in ('sonic','oldsonic'):
                    obs=objects(r.reader)
                    position(r,next(o for o in obs if o['name']=='Player'),320,400,case['writes'])
                    widths=[];start=time.monotonic()
                    while time.monotonic()-start<7:
                        obs=objects(r.reader);widths += [o['w'] for o in obs if o['name']=='Active 23sonic']
                        boss=next(o for o in obs if o['name']==boss_name)
                        case['samples'].append(dict(seconds=time.monotonic()-start,values=values(r.reader,boss),widths=widths[-1:]))
                        time.sleep(.3)
                    assert min(widths)==168,widths
                    capture.snap(r,name+'-platform-fire')
                    hit(r,boss_name,index,0,case)
                elif name=='solgryn':
                    entered=False;start=time.monotonic()
                    while time.monotonic()-start<65:
                        obs=objects(r.reader);boss=next(o for o in obs if o['name']==boss_name);v=values(r.reader,boss)
                        if v[0]==5999 and not entered:
                            position(r,next(o for o in obs if o['name']=='Player'),300,-8,case['writes']);entered=True
                        case['samples'].append(dict(seconds=time.monotonic()-start,values=v,names=[o['name'] for o in obs if o['name'] in ('Active 9','Active 10')]))
                        if entered and v[0]>6200 and v[3]==60:break
                        time.sleep(.4)
                    assert entered and any(v['names'] for v in case['samples'])
                    assert values(r.reader,boss)[3]==60
                    capture.snap(r,'solgryn-climb-fire')
                time.sleep(.7);r.key('q');time.sleep(.5)
                assert not any(o['name']=='Player' for o in objects(r.reader))
                r.key('r');time.sleep(1);assert any(o['name']=='Player' for o in objects(r.reader))
                r.close('one-hit-probe');s.resume(1);case['passed']=True;print('PASS',name,flush=True)
            except BaseException as e:
                case['error']=repr(e)
                try:capture.snap(r,name+'-failure')
                except Exception:pass
                raise
            finally:
                if s.active:r.close('one-hit-probe-cleanup')
                (OUT/'live-results.json').write_text(json.dumps(report,indent=2)+'\n')
    report['passed']=True;(OUT/'live-results.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':main()
