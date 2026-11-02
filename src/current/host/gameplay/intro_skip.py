"""Use each boss's original S-skip actions and phase guards, selected per save.

The manual and automatic branches are exclusive. Non-boss S bindings (Ninja
Gaiden's special event and the level editor) are deliberately not automated.
"""

import struct
from transition.events import commands, compare_ini, event, parameter
from transition.router import params
from gameplay.god_mode import GROUP

# Original source frame identities, independently checked against the old skip table.
FRAMES = frozenset((4, 7, 10, 12, 24, 26, 32, 44, 45, 46, 59))


def is_skip(command):
    return (
        command[0]
        and command[1:3] == (-6, -1)
        and params(command[-1], True) == [(14, parameter(14, struct.pack("<I", 83)))]
    )


def transform(frame, sections):
    if frame not in FRAMES:
        return sections, []
    saves = {
        c[3]
        for rows in sections
        for row in rows
        for c in commands(row)
        if not c[0] and c[1:3] == (33, 94) and b"Positions\0" in c[-1]
    }
    assert len(saves) == 1, (frame, saves)
    ini = saves.pop()
    used = {
        struct.unpack_from("<H", c[-1], 14)[0]
        for rows in sections
        for row in rows
        for c in commands(row)
        if c[0]
    }

    def identifier():
        n = next(n for n in range(0xCB00, 0xCF00) if n not in used)
        used.add(n)
        return n

    out, audit = [], []
    for si, rows in enumerate(sections):
        result = []
        for ri, row in enumerate(rows):
            cs = commands(row)
            keys = [i for i, c in enumerate(cs) if is_skip(c)]
            if not keys:
                result.append(row)
                continue
            assert len(keys) == 1 and row[2] >= 2, (frame, si, ri)
            actions = [c[-1] for c in cs if not c[0]]
            conditions = [c[-1] for c in cs if c[0]]
            manual = event(
                row,
                conditions
                + [compare_ini(GROUP, "SkipIntro", 0, 0, identifier(), oi=ini)],
                actions,
            )
            automatic = []
            for ci, raw in enumerate(conditions):
                if ci == keys[0]:
                    raw = compare_ini(GROUP, "SkipIntro", 1, 0, identifier(), oi=ini)
                else:
                    raw = raw[:14] + struct.pack("<H", identifier()) + raw[16:]
                automatic.append(raw)
            index = len(result)
            result.extend((manual, event(row, automatic, actions)))
            audit.append(
                dict(
                    frame=frame,
                    section=si,
                    source_row=ri,
                    output_row=index,
                    ini=ini,
                    key_condition=keys[0],
                    actions=len(actions),
                )
            )
        out.append(result)
    assert audit, frame
    return out, audit
