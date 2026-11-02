"""Suppress hazard death calls, preserving explicit Q deaths and all other actions.

The per-save INI value is the native death fastloop repeat count: 1 normally,
0 in God Mode. Missing settings retain the original one-iteration behavior.
No live memory patch, collision changes, global destroy filter or audio hook.
"""

import struct
from transition.events import commands, event, expression, integer, ini_value, string
from transition.router import params, STAGES

GROUP = "FusionGameplayV1"
KEY = "HazardDeathLoops"
DEATH_NAMES = {
    expression(string(name), 45): name for name in ("Die", "Die2", "die", "die2")
}


def settings(enabled):
    if type(enabled) is not bool:
        raise ValueError("God Mode must be boolean")
    return dict(Schema=1, HazardDeathLoops=0 if enabled else 1)


def death_call(command):
    condition, kind, code, oi, raw = command
    if condition or (kind, code) != (-1, 14):
        return None
    ps = params(raw)
    if ps and ps[0][1] in DEATH_NAMES:
        assert len(ps) == 2 and ps[1][1] == expression(
            integer(1)
        ), "Unknown death repeat expression"
        return DEATH_NAMES[ps[0][1]]
    return None


def manual_death(cs):
    return any(
        c[0]
        and c[1:3] == (-6, -1)
        and any(
            kind == 14 and p[4:] == struct.pack("<I", 0x51)
            for kind, p in params(c[-1], True)
        )
        for c in cs
    )


def transform(frame, sections, objects, instances):
    rows = [
        (si, ri, commands(row))
        for si, ss in enumerate(sections)
        for ri, row in enumerate(ss)
        if any(death_call(c) for c in commands(row))
    ]
    if not rows:
        return sections, []
    # Online lobby and unused prototype frame are not part of native routes.
    if frame in (19, 58):
        assert all(
            frame not in stage["frames"] and frame not in stage["native_exit_frames"]
            for stage in STAGES.values()
        )
        return sections, [
            dict(
                frame=frame,
                section=si,
                row=ri,
                loop=death_call(c),
                mode="outside_native_run",
            )
            for si, ri, cs in rows
            for c in cs
            if death_call(c)
        ]
    inis = {
        c[3]
        for ss in sections
        for row in ss
        for c in commands(row)
        if not c[0] and c[1:3] == (33, 94) and b"Positions\0" in c[-1]
    }
    assert len(inis) == 1, (frame, "active save INI", inis)
    ini = inis.pop()
    out = [list(ss) for ss in sections]
    audit = []
    for si, ri, cs in rows:
        manual = manual_death(cs)
        if manual:
            assert not any(
                c[0] and c[1:3] in ((-1, -24), (-1, -25)) for c in cs
            ), "Ambiguous Q branch"
        changed = []
        for c in cs:
            name = death_call(c)
            raw = c[-1]
            if name:
                audit.append(
                    dict(
                        frame=frame,
                        section=si,
                        row=ri,
                        loop=name,
                        mode="manual_q_unchanged" if manual else "hazard_guard",
                        ini=ini,
                    )
                )
                if not manual:
                    raw = (
                        raw[:14]
                        + params(raw)[0][1]
                        + expression(ini_value(GROUP, KEY, 1, oi=ini))
                    )
                    raw = struct.pack("<H", len(raw)) + raw[2:]
            changed.append(raw)
        if not manual:
            n = sections[si][ri][2]
            out[si][ri] = event(sections[si][ri], changed[:n], changed[n:])
    return out, audit
