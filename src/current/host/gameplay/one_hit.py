"""Phase-local damage on real native hits; no HP initialization or victory edits.

Sonic keeps the original HP threshold that starts the shrinking platform/fire
phase. Solgryn's refill and all phase timers stay untouched. Normal mobs and
Gradius enemies are excluded from the explicit health-object catalogue.
"""
import json, struct
from pathlib import Path
from transition.events import commands, event, expression, integer, ini_value
from transition.router import params
from gameplay.god_mode import GROUP

HEALTH = {int(f): {int(oi): idx for oi,idx in targets.items()}
          for f,targets in json.loads(Path(__file__).with_name("boss_health.json").read_text()).items()}


def token(kind, code):
    return struct.pack("<hhH",kind,code,6)


def binary(a, operator, b):
    # Native arithmetic operators: + 2, - 4, * 6. Parentheses keep blend order.
    return token(-1,-1) + a + token(0,operator) + b + token(-1,-2)


def minimum(a,b):
    return token(-1,40) + a + token(-1,-3) + b + token(-1,-2)


def maximum(a,b):
    return token(-1,41) + a + token(-1,-3) + b + token(-1,-2)


def damage_tokens(frame, oi, index, original, ini):
    hp=struct.pack("<hhHHHH",2,16,12,oi,0,index)
    damage=maximum(integer(0),hp)
    if frame in (14,60):
        floor=ini_value(GROUP,"OneHitSonicFloor",90,oi=ini)
        first=maximum(integer(0),minimum(integer(1),binary(hp,4,floor)))
        damage=maximum(integer(0),binary(hp,4,binary(floor,6,first)))
    enabled=ini_value(GROUP,"OneHit",0,oi=ini)
    return binary(integer(original),2,binary(enabled,6,binary(damage,4,integer(original))))


def transform(frame, sections, objects, instances):
    targets=HEALTH.get(frame)
    if not targets:return sections,[]
    inis={c[3] for ss in sections for row in ss for c in commands(row)
          if not c[0] and c[1:3]==(33,94) and b"Positions\0" in c[-1]}
    assert len(inis)==1,(frame,inis)
    ini=inis.pop();out=[list(ss) for ss in sections];audit=[]
    for si,ss in enumerate(sections):
        for ri,row in enumerate(ss):
            cs=commands(row);changed=[];edits=[]
            for ci,c in enumerate(cs):
                raw=c[-1]
                if not c[0] and c[1:3]==(2,33) and c[3] in targets:
                    ps=params(raw)
                    index=struct.unpack_from("<H",ps[0][1],4)[0]
                    if index==targets[c[3]]:
                        # A health catalogue entry alone is insufficient: motion
                        # counters can also use subtraction. Require a native hit.
                        assert any(k[0] and k[1] == 2 and k[2] in (-4, -14)
                                   for k in cs), (frame, si, ri, "Not a collision damage event")
                        assert len(ps)==2 and len(ps[1][1])==20
                        original=struct.unpack_from("<i",ps[1][1],12)[0]
                        assert 1<=original<=15 and ps[1][1]==expression(integer(original))
                        raw=raw[:14]+ps[0][1]+expression(damage_tokens(frame,c[3],index,original,ini))
                        raw=struct.pack("<H",len(raw))+raw[2:]
                        edits.append(dict(frame=frame,section=si,row=ri,command=ci,oi=c[3],
                                          name=objects[c[3]]["name"],index=index,damage=original))
                changed.append(raw)
            if edits:
                out[si][ri]=event(row,changed[:row[2]],changed[row[2]:]);audit.extend(edits)
    assert {a['oi'] for a in audit}==set(targets),(frame,"Uncovered health object")
    return out,audit
