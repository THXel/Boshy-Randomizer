"""Serialize a checkpoint/route once after its synchronous native actions.

Only the gameplay save object is batched. The original action order, fastloops,
checkpoint sounds and collisions remain intact. Fastloop handlers inherit their
caller's transaction; existing explicit batches and file loads are left alone.
Every transaction commits before a frame change, never on a host timer.
"""
import struct
from transition.events import commands, event, action, expression, integer
from gameplay.native_events import Events
from transition.router import frame_metadata, STAGES
from gameplay.profile_batch import begin, finish

FRAMES = {n for s in STAGES.values() for n in s['frames']} | {9}


def transform(frame, sections, objects, instances):
    if frame not in FRAMES:
        return sections, []
    ini, _, _ = frame_metadata(frame, sections, objects, instances)
    output, changed, timers = [], 0, 0
    e = Events(sections, low=0xDC00, high=0xDD00)
    for rows in sections:
        result = []
        for row in rows:
            cs = commands(row)
            conditions = [c[-1] for c in cs if c[0]]
            actions = [c for c in cs if not c[0]]
            # The original clock edits the same encrypted document once per second.
            # Keep its value in memory; checkpoints, deaths and frame exit persist it.
            # This leaves the original clock and Timer item expressions intact.
            if (len(actions) == 1 and actions[0][1:4] == (33, 94, ini)
                    and b'Stats\0' in actions[0][-1] and b'TimeSeconds\0' in actions[0][-1]
                    and any(c[0] and c[1:3] == (-4, -4) for c in cs)):
                result.append(event(row, conditions, [begin(ini), actions[0][-1],
                    action(33, 132, ini, [expression(integer(0))])]))
                timers += 1
                continue
            # Do not nest transactions or change load/reload semantics.
            if any(c[0] and c[1:3] == (-1, -16) for c in cs) or any(
                c[1] == 33 and c[3] == ini and c[2] in (123, 124, 125, 132)
                for c in actions
            ):
                result.append(row)
                continue
            writes = [i for i,c in enumerate(actions) if c[1] == 33 and c[3] == ini and c[2] in (94,95)]
            loops = [i for i,c in enumerate(actions) if c[1:3] == (-1,14) and any(
                text in c[-1] for text in (b'save\0', b'Fusion Target next\0'))]
            if len(writes) < 2 and not loops:
                result.append(row)
                continue
            first = min(writes + loops)
            end = next((i for i,c in enumerate(actions[first:],first) if c[1] == -3 and c[2] in (0,1,2,4,5,6)),len(actions))
            # All writes must finish before the transfer; never move actions.
            if any(i >= end for i in writes+loops):
                raise ValueError('Save action after frame transfer')
            raw = [c[-1] for c in actions]
            raw = raw[:first] + [begin(ini)] + raw[first:end] + finish(ini) + raw[end:]
            result.append(event(row,conditions,raw)); changed += 1
        output.append(result)
    if timers:
        # Native End of Frame also runs on R/F2 and normal application close.
        # Commit before a later frame loads the document again.
        end = struct.pack('<HhhHHHBBH', 16, -3, -2, 0, 0, 0, 0, 0, e.ident())
        output.append([e.row([end], [action(33, 124, ini, [])])])
    return output, [dict(frame=frame, save_transactions=changed, buffered_clocks=timers)] if changed or timers else []
