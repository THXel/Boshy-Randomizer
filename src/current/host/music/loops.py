"""Repeat background music in the engine; retain explicit stops and transitions.

The catalogue distinguishes music from speech, shots and short victory jingles.
Some jingles trigger the next scene when they finish and must remain one-shot.
"""

from music.runtime import NAMES, GROUP
from music.title import CUE, GROUP as TITLE_GROUP
from transition.events import action, commands, event, expression, integer
from transition.router import params

MUSIC = frozenset(NAMES) | {
    CUE,
    "Boshy Credits",
    "8bit Clouds",
    "smgalaxy-windgarden",
    "select",
    "smb2_character_select",
    "Rhythm Heaven Fever Music - Ringside",
    "Super Mario RPG - Victory!!",
    "hellokitty (2)",
    "loludied",
    "EpicSaxGuy",
    "FUCK IITTT",
    "George Michael - Careless Whisper Loop (2)",
    "MM2Wily-w-Lyrics (2)",
    "Put dat cookie down redux",
    "chocolate rain",
    "doabreelroll",
    "keyboard cat (2)",
    "lalalalalalala low q (2)",
    "omnomnom",
    "rickroll",
    "trololo",
}


def is_music(command):
    if command[0] or command[1] != -2:
        return False
    code, raw = command[2], command[-1]
    if code in (0, 4, 11, 12):
        ps = params(raw)
        return bool(
            ps
            and ps[0][0] == 6
            and ps[0][1][8:].split(b"\0", 1)[0].decode("latin1") in MUSIC
        )
    return code in (28, 29) and any(
        group.encode() + b"\0" in raw for group in (GROUP, TITLE_GROUP)
    )


def transform(frame, sections):
    result, changed = [], 0
    for rows in sections:
        output = []
        for row in rows:
            cs = commands(row)
            actions = []
            for c in cs:
                if c[0]:
                    continue
                raw = c[-1]
                if is_music(c):
                    ps = [p[1] for p in params(raw)]
                    code = {0: 4, 4: 4, 11: 12, 12: 12, 28: 29, 29: 29}[c[2]]
                    if c[2] in (4, 12, 29):
                        ps[-1] = expression(integer(0), 27)
                    else:
                        ps.append(expression(integer(0), 27))
                    raw = action(-2, code, c[3], ps)
                    changed += int(raw != c[-1])
                actions.append(raw)
            output.append(event(row, [c[-1] for c in cs if c[0]], actions))
        result.append(output)
    return result, [dict(frame=frame, music_loop_actions=changed)] if changed else []
