"""Enable existing Ez shooting and remove the mouse ghost via per-save INI.

Only the difficulty gate of the two held-fire events changes. Their timer,
projectile cap, control mapping and actions stay native. Mouse-ghost source events remain intact; a disabled ghost is removed natively.
"""
import struct
from transition.events import commands, event, expression, integer, ini_value, parameter, compare_ini, action
from transition.router import params
from gameplay.god_mode import GROUP


def transform(frame, sections, objects, instances):
    out = [list(rows) for rows in sections]
    audit = []
    ghosts = []
    ini = None
    def save_ini():
        nonlocal ini
        if ini is None:
            found = {c[3] for rows in sections for row in rows for c in commands(row)
                     if not c[0] and c[1:3] == (33, 94) and b"Positions\0" in c[-1]}
            assert len(found) == 1, (frame, "active save INI", found)
            ini = found.pop()
        return ini
    for si, rows in enumerate(sections):
        for ri, row in enumerate(rows):
            cs = commands(row)
            held_shot = (any(c[0] and c[1:3] == (-7, -6) for c in cs)
                         and any(not c[0] and c[1:3] == (2, 29)
                                 and objects[c[3]]["name"] == "Player" for c in cs))
            changed = []
            edits = []
            for ci, c in enumerate(cs):
                raw = c[-1]
                ps = params(raw, c[0])
                if (held_shot and c[0] and c[1:3] == (-1, -8)
                    and ps[0][1] == parameter(49, bytes(6))):
                    assert ps[1][1] == expression(integer(0), 23)
                    # difficulty <= 0 retains Ez-only; <= 3 enables all four modes.
                    raw = raw[:16] + ps[0][1] + expression(
                        ini_value(GROUP, "AutoFireMaxDifficulty", 0, oi=save_ini()), 23, 2)
                    edits.append((ci, "autofire"))
                elif (not c[0] and c[1:3] == (2, 32)
                      and objects[c[3]]["name"] == "mouse kill"):
                    assert ps == [(50, parameter(50, bytes(6))), (22, expression(integer(1)))]
                    ghosts.append((si, ri, c[3], row))
                if raw != c[-1]:
                    raw = struct.pack("<H", len(raw)) + raw[2:]
                changed.append(raw)
            if edits:
                out[si][ri] = event(row, changed[:row[2]], changed[row[2]:])
                audit.extend(dict(frame=frame, section=si, row=ri, command=ci,
                                  rule=rule, ini=ini) for ci, rule in edits)
    identifiers = {struct.unpack_from("<H",c[-1],14)[0]
                   for ss in sections for row in ss for c in commands(row) if c[0]}
    for si, ri, oi, template in ghosts:
        identifier = next(n for n in range(0xD000, 0xFFFE) if n not in identifiers)
        identifiers.add(identifier)
        # Remove the actual collision object, not only its cursor-following charge.
        condition = compare_ini(GROUP,"MouseGhostDisabled",1,0,identifier,oi=save_ini())
        added = event(template,[condition],[action(2,24,oi,[])])
        out[si].append(added)
        audit.append(dict(frame=frame,section=si,row=len(out[si])-1,command=1,
                          rule="no_mouse_ghost",ini=ini,oi=oi,source_row=ri,added=True))
    return out, audit
