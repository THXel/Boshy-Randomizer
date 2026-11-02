"""Persist native key bindings only when their value actually changes.

The original per-frame synchronization still observes current controls (including
mirror mode). Ini++ setters are gated by their current in-memory value, avoiding
repeated encrypted file saves for identical bindings. All original OR branches
keep their conditions; unrelated actions retain their original event.
"""
import re
import struct
from gameplay.native_events import Events
from gameplay.rewards import ini_string
from transition.events import commands, event
from transition.router import params, value_parameter, guarded

CONTROL = re.compile(rb'Control(?:UP|DOWN|LEFT|RIGHT|JUMP|SHOOT|RESTART)\x00')


def transform(frame, sections):
    e = Events(sections, low=0x1000, high=0xFFFE)
    output, changed = [], 0
    for rows in sections:
        result = []
        for row in rows:
            cs = commands(row)
            conditions = [c[-1] for c in cs if c[0]]
            actions = [c for c in cs if not c[0]]
            selected = [c for c in actions if c[1:3] == (33, 95)
                        and b'Options\0' in c[-1] and CONTROL.search(c[-1])]
            if not selected:
                result.append(row)
                continue
            others = [c[-1] for c in actions if c not in selected]
            if others:
                result.append(event(row, conditions, others))
            for c in selected:
                ps = params(c[-1])
                key = CONTROL.search(ps[1][1])[0][:-1].decode('ascii')
                gate = e.cmp(ini_string('Options', key, '', c[3]), value_parameter(ps[2]), 1)
                protected = guarded(conditions, [gate])
                fresh = []
                for raw in protected:
                    fresh.append(raw[:14] + struct.pack('<H', e.ident()) + raw[16:])
                result.append(event(row, fresh, [c[-1]]))
                changed += 1
        output.append(result)
    return output, [dict(frame=frame, changed_binding_guards=changed)] if changed else []
