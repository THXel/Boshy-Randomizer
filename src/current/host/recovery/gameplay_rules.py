"""Validated game rules already present in the original Randomizer's native patch."""

import struct
from transition.events import commands, event
from transition.boss_exits import split
from transition.router import params

BETA_BOSSES = {44: 2372, 45: 2380}


def beta_damage_guards(frame, sections):
    """Allow damage from phase 780, including the original S intro skip."""
    if frame not in BETA_BOSSES:
        return sections, []
    oi = BETA_BOSSES[frame]
    result = [list(rows) for rows in sections]
    changed = []
    for si, rows in enumerate(sections):
        for ri, row in enumerate(rows):
            cs = commands(row)
            damage = [c for c in cs if not c[0] and c[1:4] == (2, 33, oi)]
            if not damage:
                continue
            assert len(damage) == 1
            fields = params(damage[0][-1])
            assert (
                fields[0][0] == 50 and struct.unpack_from("<I", fields[0][1], 4)[0] == 3
            )
            assert fields[1][1] == bytes.fromhex(
                "140016000000ffff00000a000100000000000000"
            )
            conditions, actions = split(row)
            matches = [
                i
                for i, c in enumerate(conditions)
                if struct.unpack_from("<hhH", c, 2) == (2, -27, oi)
            ]
            assert len(matches) == 1
            index = matches[0]
            old = conditions[index]
            assert len(old) == 46 and old[16:38] == bytes.fromhex(
                "0a003200000000000000140017000500ffff00000a00"
            )
            assert struct.unpack_from("<I", old, 38)[0] == 400
            new = bytearray(old)
            struct.pack_into("<I", new, 38, 779)
            conditions[index] = bytes(new)
            result[si][ri] = event(row, conditions, actions)
            changed.append(
                {
                    "frame": frame,
                    "section": si,
                    "row": ri,
                    "boss_oi": oi,
                    "old_exclusive_phase": 400,
                    "new_exclusive_phase": 779,
                }
            )
    assert len(changed) == 2, (frame, changed)
    return result, changed
