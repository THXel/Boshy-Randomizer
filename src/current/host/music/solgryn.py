"""Keep replacement music alive across Solgryn's scripted phases.

Megalith is a long, single-play track with hard-coded seeks. Replacement tracks
have unrelated lengths and arrangements: loop them and retain pause/resume,
without applying Megalith's 29.2/141.5-second offsets. Original phase timing is unchanged.
"""

import struct
from gameplay.native_events import Events
from transition.events import action, commands, event, expression, integer
from transition.router import frame_metadata, guarded, params
from music.runtime import GROUP, NAMES

FRAME = 46
CUE = "Ace Combat  Megalith"
OFFSETS = (29200, 141500)


def original_seek(command):
    return (
        not command[0]
        and command[1:3] == (-2, 16)
        and params(command[-1])
        in [
            [(22, expression(integer(2))), (22, expression(integer(offset)))]
            for offset in OFFSETS
        ]
    )


def transform(frame, sections, objects, instances):
    if frame != FRAME:
        return sections, []
    ini, _, _ = frame_metadata(frame, sections, objects, instances)
    e = Events(sections, low=0x1000, high=0xFFFE)
    marker = f"Cue{NAMES.index(CUE):02d}".encode() + b"\0"
    changed, seeks, plays = [], 0, 0

    def branch(row, conditions, actions, enabled):
        conditions = guarded(
            conditions, [e.eq(ini, GROUP, "Enabled", 1, 0 if enabled else 1)]
        )
        conditions = [
            raw[:14] + struct.pack("<H", e.ident()) + raw[16:] for raw in conditions
        ]
        return event(row, conditions, actions)

    for rows in sections:
        out = []
        for row in rows:
            cs = commands(row)
            conditions = [c[-1] for c in cs if c[0]]
            actions = []
            for c in cs:
                if c[0]:
                    continue
                raw = c[-1]
                if c[1:3] == (-2, 28) and marker in raw:
                    # Already guarded by FusionMusicV1.Enabled in runtime.transform.
                    raw = action(
                        -2,
                        29,
                        c[3],
                        [p[1] for p in params(raw)] + [expression(integer(0), 27)],
                    )
                    plays += 1
                actions.append(raw)
            if any(original_seek(c) for c in cs):
                seeks += 1
                out.append(branch(row, conditions, actions, False))
                replacement = [c[-1] for c in cs if not c[0] and not original_seek(c)]
                if replacement:
                    out.append(branch(row, conditions, replacement, True))
            else:
                out.append(event(row, conditions, actions))
        changed.append(out)
    if plays != 1 or seeks not in (3, 4):
        raise ValueError(
            f"Unexpected Solgryn music events: {plays} playback, {seeks} seeks"
        )
    return changed, [
        dict(
            frame=frame, solgryn_replacement_loop=plays, original_only_music_seeks=seeks
        )
    ]
