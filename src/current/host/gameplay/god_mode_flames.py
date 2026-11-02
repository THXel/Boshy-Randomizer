"""Reuse the native harmless fire particles as a persistent God Mode indicator.

Original character effects are retained. The additional emitter is enabled only
by an explicit per-save God Mode value and a live Player, and avoids doubling
the original fire character's emitter. It changes no collisions or death rules.
"""

import struct
from gameplay.native_events import Events
from gameplay.god_mode import GROUP, KEY
from transition.events import commands, event, action, parameter, ini_value, integer
from transition.router import params


def transform(frame, sections, objects):
    if frame in (19, 58):
        return sections, []
    inis = {
        c[3]
        for ss in sections
        for row in ss
        for c in commands(row)
        if not c[0] and c[1:3] == (33, 94) and b"Positions\0" in c[-1]
    }
    if not inis:
        return sections, []
    assert len(inis) == 1, (frame, inis)
    ini = inis.pop()
    e = Events(sections, low=0x1000, high=0xFFFE)
    result, audit = [], []
    for si, rows in enumerate(sections):
        out = []
        result.append(out)
        for ri, row in enumerate(rows):
            out.append(row)
            cs = commands(row)
            emitters = [
                c
                for c in cs
                if not c[0]
                and c[1:3] == (2, 59)
                and objects[c[3]]["name"] == "OPE_fireParticle"
            ]
            if not emitters:
                continue
            conditions = [c for c in cs if c[0]]
            assert len(conditions) == 2 and conditions[0][1:3] == (-1, -8)
            assert conditions[1][1:3] == (2, -32)
            player = conditions[1][3]
            assert objects[player]["name"] == "Player"
            original_character, living = [bytearray(c[-1]) for c in conditions]
            # Native comparison 1 means not equal: don't duplicate ONOpe's fire.
            ps = params(original_character, True)
            assert len(ps) == 2 and ps[1][0] == 23
            assert struct.unpack_from("<H", ps[1][1], 4)[0] == 0
            struct.pack_into("<H", original_character, 16 + len(ps[0][1]) + 4, 1)
            struct.pack_into("<H", original_character, 14, e.ident())
            struct.pack_into("<H", living, 14, e.ident())
            acts = [c[-1] for c in cs if not c[0]]
            behind = action(
                2,
                59,
                emitters[0][3],
                [parameter(1, struct.pack("<HHHH", 0, player, 2, 0))],
            )
            acts = [behind if a == emitters[0][-1] else a for a in acts]
            guard = e.cmp(ini_value(GROUP, KEY, 1, oi=ini), integer(0))
            out.append(
                event(row, [guard, bytes(original_character), bytes(living)], acts)
            )
            audit.append(
                dict(
                    frame=frame,
                    section=si,
                    source_row=ri,
                    rule="god_mode_flames",
                    ini=ini,
                    player=player,
                )
            )
    return result, audit
