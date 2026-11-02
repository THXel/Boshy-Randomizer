"""Select the original shooting sound that belongs to the current shot artwork.

Only character selection and its license guard in 'shooot' handlers change.
Jump, movement, death, enemy sounds, music and all original sound actions remain
byte-identical. The game's 'Special Shooting Sounds' preference is respected.
"""

import struct
from gameplay.native_events import Events
from gameplay.native_extras import group, operator
from gameplay.normal_plan import FRAMES
from gameplay.shot_plan import GROUP, STATE
from gameplay.shot_gates import effective_license
from transition.events import commands, event, expression, integer, ini_value, parameter
from transition.router import frame_metadata, params


def transform(frame, sections, objects, instances):
    if frame not in FRAMES:
        return sections, []
    save, _, _ = frame_metadata(frame, sections, objects, instances)
    license = Events.profile(sections)
    enabled = ini_value(GROUP, "Enabled", oi=save)
    shot_id = group(
        ini_value(STATE, "Frame", oi=license)
        + operator(6)
        + integer(4)
        + operator(2)
        + integer(12)
    )
    original_id = struct.pack("<hhHHHH", -1, 24, 12, 0, 0, 5)
    selected_id = (
        original_id
        + operator(6)
        + group(integer(1) + operator(4) + enabled)
        + operator(2)
        + shot_id
        + operator(6)
        + enabled
    )
    result = [list(s) for s in sections]
    changed = []
    for si, rows in enumerate(sections):
        for ri, row in enumerate(rows):
            cs = commands(row)
            if not any(
                c[0] and c[1:3] == (-1, -16) and b"shooot\0" in c[-1] for c in cs
            ):
                continue
            edited = []
            for cond, kind, code, oi, raw in cs:
                if cond:
                    raw = effective_license(raw, save)
                if cond and (kind, code) == (-1, -8):
                    ps = params(raw, True)
                    assert ps[0][1] == parameter(49, struct.pack("<IH", 5, 0))
                    assert (
                        ps[1][0] == 23 and struct.unpack_from("<H", ps[1][1], 4)[0] == 0
                    )
                    cid = struct.unpack_from("<i", ps[1][1], 12)[0]
                    assert 12 <= cid <= 156 and cid % 4 == 0
                    body = expression(selected_id) + ps[1][1]
                    head = bytearray(raw[:16])
                    struct.pack_into("<H", head, 0, 16 + len(body))
                    struct.pack_into("<h", head, 4, -3)
                    raw = bytes(head) + body
                    changed.append(
                        dict(
                            section=si,
                            row=ri,
                            character=cid,
                            shot_frame=(cid - 12) // 4,
                        )
                    )
                edited.append(raw)
            result[si][ri] = event(row, edited[: row[2]], edited[row[2] :])
    assert len(changed) == 37 and {c["shot_frame"] for c in changed} == set(
        range(37)
    ), frame
    return result, [dict(frame=frame, shot_sounds=changed)]
