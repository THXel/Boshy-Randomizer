"""Native checkpoint return for portals outside the current route point's exits."""
import struct
from gameplay.native_events import Events
from transition.events import commands,event,action,expression,integer,ini_value,set_ini
from transition.router import STAGES,GROUP,frame_metadata,native_destination,global_expression,guarded
from transition.boss_exits import split


def transform(frame,sections,table,objects,instances):
    protected=[s for s in STAGES.values() if frame in s['frames'] and 29 not in s['native_exit_frames']]
    if not protected:return sections,[]
    ini,_,_=frame_metadata(frame,sections,objects,instances)
    e=Events(sections,low=0x1000,high=0xfffe)
    result=[];audit=[]
    for si,section in enumerate(sections):
        rows=[];result.append(rows)
        for ri,row in enumerate(section):
            cs=commands(row);conds,acts=split(row)
            jumps=[(i,c) for i,c in enumerate(cs) if not c[0] and c[1]==-3 and c[2] in (0,2)]
            if si<2 or len(jumps)!=1 or any(b'Done' in c[-1] and b'FusionRouteV4\0' in c[-1] for c in cs if not c[0]):
                rows.append(row);continue
            ci,jump=jumps[0];dest,tokens=native_destination(jump,cs[:ci],frame,table)
            if dest!=29 and (dest is not None or tokens is None):rows.append(row);continue
            for stage in protected:
                guards=[e.eq(ini,GROUP,'Schema',4),e.eq(ini,GROUP,'LevelsEnabled',1),
                        e.eq(ini,GROUP,'CurrentStage',stage['id']),e.eq(ini,GROUP,'Handled',0)]
                if tokens is not None:guards.append(e.cmp(tokens,integer(29)))
                # Read the most recent native checkpoint before the original
                # portal action can replace Positions with the hub destination.
                restore=[global_expression(g,ini_value('Positions',key,oi=ini)) for g,key in [(1,'xPos'),(2,'yPos'),(8,'frame')]]
                restore += [set_ini(GROUP,'Handled',1,oi=ini),set_ini(GROUP,'BlockedPortal',29,oi=ini),
                            action(-3,2,0,[expression(ini_value('Positions','frame',oi=ini))])]
                fresh=[]
                for c in guarded(conds,guards):
                    c=bytearray(c);struct.pack_into("<H",c,14,e.ident());fresh.append(bytes(c))
                rows.append(e.row(fresh,restore))
                audit.append(dict(frame=frame,section=si,row=ri,stage=stage['id'],rule='unlisted_hub_checkpoint_return'))
            rows.append(event(row,guarded(conds,[e.eq(ini,GROUP,'Handled',0)]),acts))
    return result,audit
