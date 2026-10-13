"""User-confirmed native exits, scoped to the stage actually entered.

Save flags and checkpoint changes never finish a stage by themselves. Beta bosses
and Gastly retain their separate native completion protocols.
"""
import time
from native_targets import BOSSES
# Kept for diagnostics and historical callers; these flags are NOT exit triggers.
WORLDS={'save1.ini':1,'save2.ini':2,'save3.ini':3,'save4.ini':4,'save5.ini':4,
        'save6.ini':5,'save7.ini':6,'save9.ini':7,'save10.ini':7,'save11.ini':8,
        'save8.ini':9,'save12.ini':9,'save13.ini':10,'save22.ini':10,'save15.ini':11}
EXITS={36:(3,),3:(4,33),5:(6,),8:(10,37),11:(12,),13:(14,),
       15:(17,39,50),52:(17,39,50),22:(24,53),23:(24,53),25:(26,),
       27:(59,),31:(32,),35:(51,38),33:(29,),37:(29,),50:(15,52),
       53:(54,),38:(46,),51:(35,)}
BOSS_EXITS={4:(5,),6:(7,),7:(8,),10:(11,),12:(13,),14:(15,),
            17:(22,),24:(25,),26:(27,),59:(31,),32:(35,),60:(15,),54:(29,),39:(17,),28:(31,)}
BOSS_KEYS={v[2]:k for k,v in BOSSES.items()}
BOSS_KEYS.update({'boss23.ini':'sonic','boss21.ini':'cheetahmen','boss10.ini':'gradius'})
RULE_VERSION=3

def stage_frames(spot,point):
    frame=point['frame']
    if spot=='boss10.ini':return (15,39)  # Legacy Gradius approach inside Castlevania.
    if point['category']=='rooms' and frame in (22,23):return (22,23)
    if point['category']=='rooms' and frame in (15,52):return (15,52)
    return (frame,)

def exits_for(spot,point):
    if point.get('segment') in ('before_kracko','before_ninja_ryu','kracko','ninja_ryu'):return ()
    if spot=='boss7.ini':return (12,)
    if spot=='boss10.ini':return (17,)
    return (BOSS_EXITS if point['category']=='bosses' else EXITS).get(point['frame'],())

class CompletionGate:
    def __init__(self):self.reset()
    def reset(self):
        self.identity=None;self.seen_origin=False;self.previous=None;self.candidate=None;self.candidate_frame=None;self.since=0;self.last_frame=None;self.last_tick=None;self.deaths=None;self.won=False
    def snapshot(self):
        return dict(rule_version=RULE_VERSION,identity=list(self.identity) if self.identity else None,
                    seen_origin=self.seen_origin,previous=self.previous,candidate=self.candidate,
                    candidate_frame=self.candidate_frame,deaths=self.deaths,won=self.won)
    def restore(self,data):
        self.reset()
        # Older generic flag/room candidates do not prove one of the specified exits.
        if not data or data.get('rule_version')!=RULE_VERSION:return
        self.identity=tuple(data['identity']) if data.get('identity') else None
        for name in ('seen_origin','previous','candidate','candidate_frame','deaths','won'):
            if name in data:setattr(self,name,data[name])
        self.since=time.monotonic()
    def pause(self):
        self.last_frame=None;self.last_tick=None
        if self.candidate:self.since=time.monotonic()
    def observe(self,spot,point,frame,ach,disk,stats,tick=None,restart_pressed=False,position=None):
        identity=(spot,point['frame'])
        if self.identity!=identity:self.reset();self.identity=identity
        origins=stage_frames(spot,point);exits=exits_for(spot,point)
        deaths=int(stats.get('deaths',0))
        restarted=(self.deaths is not None and deaths!=self.deaths) or (frame==self.last_frame and tick is not None and self.last_tick is not None and tick<self.last_tick)
        self.deaths=deaths;self.last_tick=tick
        key=BOSS_KEYS.get(spot);current={key:min(int(ach.get(key,0)),int(disk.get(key,0)))} if key else {}
        self.won=bool(current and any(v>=2 for v in current.values()))
        if self.previous is None or restarted:
            self.previous=current;self.candidate=None;self.candidate_frame=None;self.seen_origin=frame in origins;self.last_frame=frame;return None
        exact_exit=(point['frame']!=51 or (position is not None and tuple(position)==(7871,553)))
        if self.candidate and (frame!=self.candidate_frame or frame not in exits or not exact_exit):
            self.candidate=None;self.candidate_frame=None
        if self.seen_origin and self.last_frame in origins and frame in exits and exact_exit and not self.candidate:
            self.candidate='Boss-Ausgang' if point['category']=='bosses' else 'Level-Ausgang'
            self.candidate_frame=frame;self.since=time.monotonic()
        if frame in origins:self.seen_origin=True
        elif frame not in exits:self.seen_origin=False
        self.previous=current;self.last_frame=frame
        if self.candidate and time.monotonic()-self.since>=2:return self.candidate
        return None
