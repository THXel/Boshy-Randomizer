"""Select custom blood at its native player-death creation, never by timing.

Animation 0 and enemy creation events stay original. Animation 15 is a private
pack slot. Alterable value G is an unused per-particle lifetime; zero denotes
ordinary blood. No sound action is added, removed, or moved.
"""

import copy
import struct
from transition.events import (
    action,
    commands,
    event,
    expression,
    integer,
    ini_value,
    parameter,
)
from transition.boss_exits import split
from transition.router import frame_metadata, params

GROUP = "FusionBloodV1"
BLOOD = {105: "Active 2", 1032: "blood"}
ANIMATION = 15
LIFE = 6


def compare_life(oi, value, comparison, identifier):
    fields = parameter(50, struct.pack("<IH", LIFE, 0)) + expression(
        integer(value), 23, comparison
    )
    return (
        struct.pack(
            "<HhhHHHBBH", 16 + len(fields), 2, -27, oi, 0, 0x20, 2, 0, identifier
        )
        + fields
    )


def set_life(oi, tokens, code=31):
    return action(
        2, code, oi, [parameter(50, struct.pack("<IH", LIFE, 0)), expression(tokens)]
    )


def extend_object(obj):
    if obj["handle"] not in BLOOD:
        return obj
    assert obj["name"] == BLOOD[obj["handle"]] and obj["type"] == 2
    assert len(obj["values"]) == 6
    assert [a["slot"] for a in obj["animations"]] == [0]
    out = copy.deepcopy(obj)
    out["values"].append(0)
    out["animations"].append(
        dict(
            slot=ANIMATION,
            name="Player blood",
            directions=[
                dict(
                    direction=0,
                    minSpeed=32,
                    maxSpeed=32,
                    repeat=0,
                    backTo=0,
                    frames=[7, 2] * 16,
                )
            ],
        )
    )
    return out


def player_spawn(row):
    cs = commands(row)
    expected = expression(integer(3))
    return any(c[0] and c[1:4] == (57, -81, 267) and c[-1][16:] == expected for c in cs)


def transform(frame, sections, objects, instances):
    spawn_rows = [
        (si, ri, row)
        for si, rows in enumerate(sections)
        for ri, row in enumerate(rows)
        if player_spawn(row)
    ]
    if not spawn_rows:
        return sections, []
    assert len(spawn_rows) == 1, frame
    si, ri, row = spawn_rows[0]
    cs = commands(row)
    selected = {c[3] for c in cs if not c[0] and c[1] == 2 and c[3] in BLOOD}
    assert len(selected) == 1, (frame, selected)
    oi = selected.pop()
    assert objects[oi]["name"] == BLOOD[oi]
    create = [c for c in cs if not c[0] and c[1:3] == (-5, 0)]
    assert len(create) == 1 and len(create[0][-1]) == 50
    assert struct.unpack_from("<H", create[0][-1], 42)[0] == oi
    # Fail closed if G is ever referenced by original direct blood events.
    for rows in sections:
        for old in rows:
            for c in commands(old):
                if c[1] == 2 and c[3] == oi:
                    for kind, p in params(c[-1], c[0]):
                        if kind == 50:
                            assert struct.unpack_from("<I", p, 4)[0] != LIFE
    ini, _, _ = frame_metadata(frame, sections, objects, instances)
    result = [list(rows) for rows in sections]
    conditions, actions = split(row)
    actions += [
        action(2, 17, oi, [expression(ini_value(GROUP, "Animation", 0, oi=ini))]),
        set_life(oi, ini_value(GROUP, "LifeTicks", 0, oi=ini)),
    ]
    result[si][ri] = event(row, conditions, actions)
    audit = [
        dict(frame=frame, section=si, row=ri, oi=oi, change="player_creation_only")
    ]
    identifier = 0xB500
    for sj, rows in enumerate(sections):
        for rj, old in enumerate(rows):
            cmds = commands(old)
            if not any(not c[0] and c[1:4] == (2, 80, oi) for c in cmds):
                continue
            conditions, actions = split(old)
            assert any(not c[0] and c[1:4] == (2, 24, oi) for c in cmds)
            conditions.append(compare_life(oi, 0, 0, identifier))
            identifier += 1
            result[sj][rj] = event(old, conditions, actions)
            audit.append(
                dict(
                    frame=frame,
                    section=sj,
                    row=rj,
                    oi=oi,
                    change="keep_floor_paste_for_vanilla_only",
                )
            )
    # Destroy before the counter can reach zero and become ordinary blood.
    template = struct.pack("<hBB", -14, 0, 0) + bytes(10)
    result.append(
        [
            event(
                template, [compare_life(oi, 1, 0, identifier)], [action(2, 24, oi, [])]
            ),
            event(
                template,
                [compare_life(oi, 1, 4, identifier + 1)],
                [set_life(oi, integer(1), 33)],
            ),
        ]
    )
    return result, audit
