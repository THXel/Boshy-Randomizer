"""Explicitly load the run-local character profile before native character readers.

The recovered Ini++ object does not reliably auto-load its saved filename under
Fusion 2.5. Use the same Apppath + load action as the tested native menu mailbox.
"""

import struct
from gameplay.native_events import Events
from gameplay.characters import ROSTER
from transition.events import (
    commands,
    event,
    action,
    expression,
    integer,
    string,
    compare_ini,
    set_ini,
)


def transform(frame, sections, objects):
    reads = [
        c
        for rows in sections
        for row in rows
        for c in commands(row)
        if b"License\0" in c[-1] and b"Character\0" in c[-1]
    ]
    if not reads:
        return sections, []
    candidates = {
        o["handle"]
        for o in objects.values()
        if o["type"] == 33 and b"onlineLicense.ini\0" in o["properties"]
    }
    candidates = {
        oi
        for oi in candidates
        if any(struct.pack("<hhHH", 33, 88, 10, oi) in c[-1] for c in reads)
    }
    assert len(candidates) == 1, (frame, candidates)
    oi = candidates.pop()
    identifiers = {
        struct.unpack_from("<H", c[-1], 14)[0]
        for rows in sections
        for row in rows
        for c in commands(row)
        if c[0]
    }
    ident = next(
        i for i in range(0xCF00, 0xD000) if not set(range(i, i + 3)) & identifiers
    )
    start = struct.pack("<HhhHHHBBH", 16, -3, -1, 0, 0, 0x20, 0, 0, ident)
    path = expression(
        struct.pack("<hhH", -1, 8, 6)
        + struct.pack("<hhH", 0, 2, 6)
        + string("onlineLicense.ini"),
        45,
    )
    row = event(
        struct.pack("<hBB", -14, 0, 0) + bytes(10),
        [start],
        [
            action(33, 123, oi, [path, expression(integer(0))]),
            # Ini++ 1.5 action 129: Auto Save first, Auto Load second.
            action(33, 129, oi, [expression(integer(1)), expression(integer(0))]),
        ],
    )
    result = [list(rows) for rows in sections]
    enabled = event(
        struct.pack("<hBB", -14, 0, 0) + bytes(10),
        [
            start[:14] + struct.pack("<H", ident + 2),
            compare_ini("License", "RandomizerStartCharacter", 1, 0, ident + 1, oi=oi),
        ],
        [set_ini("Options", "OnlineLicenseCharacter", 1, oi=4)],
    )
    result[0][0:0] = [row, enabled]
    # Auto runs can have no license file at all. Native character behaviors read
    # Character with default 0, which is not a character ID. Initialize only that
    # absent/zero state; saved selections and character cycling remain untouched.
    e = Events(result, low=0x1000, high=0xFFFE)
    fallback = e.row(
        [e.start(), e.eq(oi, "License", "Character", 0)],
        [
            set_ini("License", "Character", ROSTER["Boshy"], oi=oi),
            e.text(oi, "License", "CharacterName", string("Boshy")),
        ],
    )
    from gameplay.rewards import ini_string

    # Auto-created local profiles need the same local identity as explicitly
    # chosen starts. Otherwise the original F3 room opens its obsolete online
    # registration dialog before accepting any unlocked character.
    local_identity = e.row(
        [e.start(), e.cmp(ini_string("License", "Name", "", oi), string(""))],
        [
            e.text(oi, "License", "Name", string("Randomizer")),
            set_ini("License", "NeverDoneItBefore", 1, oi=oi),
            set_ini("License", "RandomizerStartCharacter", 1, oi=oi),
        ],
    )
    result[0].insert(1, local_identity)
    result[0].insert(3, fallback)
    return result, [
        dict(
            frame=frame,
            ini=oi,
            before_original_readers=True,
            writable_profile=True,
            missing_local_identity=True,
            native_character_option=True,
            missing_character_default="Boshy",
        )
    ]
