"""Native route dispatch with save-local station identity and one transition per frame.

Original actions retain their ordering. Only a confirmed outgoing event may
commit its seed successor. Restart/menu/debug events are not rewritten.
"""

import json, struct, hashlib, sys
from pathlib import Path
from .events import (
    action,
    parameter,
    expression,
    integer,
    string,
    ini_value,
    set_ini,
    compare_ini,
    event,
    commands,
)
from .boss_exits import split, xy

GROUP = "FusionRouteV4"
from app_paths import REPO
sys.path.insert(0, str(REPO / "src/python/rules"))
from position_names import legacy_catalogue

NAMED_STAGES = json.loads(Path(__file__).with_name("stages.json").read_text())
# Only the wire/compiled interface retains historical identities.
STAGES = legacy_catalogue(NAMED_STAGES)
CATALOGUE_HASH = hashlib.sha256(
    json.dumps(STAGES, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
REGIONS = {
    "before_kracko": (3200, 0, 3840, 480),
    "before_gravitron": (2560, 1440, 3200, 1920),
    "before_ninja_ryu": (4480, 0, 5120, 480),
    "before_kid_icarus": (640, 6240, 1280, 6624),
    "before_kappa": (1920, 1440, 2560, 1920),
}


def params(raw, condition=False):
    offset = 16 if condition else 14
    result = []
    for _ in range(raw[12]):
        size, kind = struct.unpack_from("<HH", raw, offset)
        assert size >= 4 and offset + size <= len(raw)
        result.append((kind, raw[offset : offset + size]))
        offset += size
    assert offset == len(raw)
    return result


def value_parameter(p):
    assert p[0] in [22, 23, 45]
    return p[1][6:-4]


def global_expression(index, tokens):
    return action(
        -1, 3, 0, [parameter(49, struct.pack("<IH", index, 0)), expression(tokens)]
    )


def ini_expression(group, key, tokens, oi):
    return action(
        33,
        94,
        oi,
        [
            expression(string(group), 45),
            expression(string(key), 45),
            expression(integer(0)),
            expression(tokens),
        ],
    )


def compare(tokens, value, comparison=0, identifier=0x9700):
    ps = expression(tokens) + expression(integer(value), 23, comparison)
    return (
        struct.pack("<HhhHHHBBH", 16 + len(ps), -1, -3, 0, 0, 0x20, 2, 0, identifier)
        + ps
    )


def count(oi, value, comparison=0, identifier=0x9700):
    ps = expression(integer(value), 23, comparison)
    return (
        struct.pack("<HhhHHHBBH", 16 + len(ps), 2, -32, oi, 0, 0x20, 1, 0, identifier)
        + ps
    )


def inside(oi, rect, identifier):
    x, y, right, bottom = rect
    return [
        xy(oi, "x", 4, x, identifier),
        xy(oi, "x", 3, right, identifier + 1),
        xy(oi, "y", 4, y, identifier + 2),
        xy(oi, "y", 3, bottom, identifier + 3),
    ]


def native_destination(command, preceding, frame, table):
    _, kind, code, oi, raw = command
    assert kind == -3
    if code == 0:
        return frame + 1, None
    if code != 2:
        return None, None
    ps = params(raw)
    if len(ps) != 1:
        return None, None
    if ps[0][0] == 26:
        return table[struct.unpack_from("<I", ps[0][1], 4)[0]] + 1, None
    if ps[0][0] != 22:
        return None, None
    tokens = value_parameter(ps[0])
    global_i = struct.pack("<hhHHHH", -1, 24, 12, 0, 0, 8)
    if tokens == global_i:
        for c in reversed(preceding):
            if c[0] or c[1:3] != (-1, 3):
                continue
            cp = params(c[-1])
            if (
                len(cp) == 2
                and cp[0][0] == 49
                and struct.unpack_from("<I", cp[0][1], 4)[0] == 8
            ):
                tokens = value_parameter(cp[1])
                break
    if tokens[:6] == struct.pack("<hhH", -1, 0, 10) and len(tokens) == 10:
        return struct.unpack_from("<i", tokens, 6)[0], None
    return None, tokens


def frame_metadata(frame, sections, objects, instances):
    inis = set()
    saves = []
    for section in sections:
        for row in section:
            for c in commands(row):
                if not c[0] and c[1] == 33 and c[2] == 94 and b"Positions\0" in c[-1]:
                    inis.add(c[3])
                if not c[0] and c[1:3] == (-1, 14) and b"save\0" in c[-1]:
                    saves.append(c[-1])
    players = {
        i["objectInfo"]
        for i in instances
        if objects[i["objectInfo"]].get("name") == "Player"
    }
    assert len(inis) == 1, (frame, "active INI", inis)
    assert len(players) == 1, (frame, "player", players)
    assert saves, (frame, "save fastloop")
    return inis.pop(), players.pop(), saves[0]


def guarded(conditions, guards):
    """Apply guards to EVERY branch of an original Fusion OR expression."""
    result = []
    for condition in conditions:
        kind, code = struct.unpack_from("<hh", condition, 2)
        if (kind, code) in [(-1, -24), (-1, -25)]:
            result.extend(guards)
        result.append(condition)
    return result + guards


def transform(frame, sections, table, objects, instances):
    selected = {k: s for k, s in STAGES.items() if frame in s["frames"]}
    if not selected:
        return sections, {"frame": frame, "edges": []}
    ini, player, save = frame_metadata(frame, sections, objects, instances)
    template = struct.pack("<hBB", -14, 0, 0) + bytes(10)
    next_identifier = 0xA000

    def ev(template, conditions, actions):
        nonlocal next_identifier
        unique = []
        for c in conditions:
            next_identifier += 1
            raw = bytearray(c)
            struct.pack_into("<H", raw, 14, next_identifier)
            unique.append(bytes(raw))
        return event(template, unique, actions)

    def check(key, value, comparison=0):
        nonlocal next_identifier
        next_identifier += 1
        return compare_ini(GROUP, key, value, comparison, next_identifier, oi=ini)

    def enabled(stage):
        return [
            check("Schema", 4),
            check("CurrentStage", stage["id"]),
            check("Handled", 0),
            check("NextId" + str(stage["id"]), 1, 4),
            check("NextId" + str(stage["id"]), len(STAGES), 2),
            check("NextFrame" + str(stage["id"]), 3, 4),
            check("NextFrame" + str(stage["id"]), 60, 2),
        ]

    def dispatch(stage):
        sid = str(stage["id"])
        get = lambda key: ini_value(GROUP, key + sid, oi=ini)
        result = [
            global_expression(1, get("NextX")),
            global_expression(2, get("NextY")),
            global_expression(8, get("NextFrame")),
        ]
        result += [
            ini_expression("Positions", key, get(field), ini)
            for key, field in [
                ("xPos", "NextX"),
                ("yPos", "NextY"),
                ("frame", "NextFrame"),
            ]
        ]
        result += [
            set_ini(GROUP, "Done" + sid, 1, oi=ini),
            ini_expression(GROUP, "CurrentStage", get("NextId"), ini),
            set_ini(GROUP, "Handled", 1, oi=ini),
            save,
        ]
        result.append(
            action(-3, 2, 0, [expression(struct.pack("<hhHHHH", -1, 24, 12, 0, 0, 8))])
        )
        return result

    start = struct.pack("<HhhHHHBBH", 16, -3, -1, 0, 0, 0, 0, 0, 0x9F00)
    prelude = [
        ev(
            template,
            [start],
            [
                set_ini(GROUP, key, 0, oi=ini)
                for key in ["Handled", "Armed", "KrackoVictory", "KidSeen"]
            ],
        )
    ]
    extras = []
    audit = []
    result = []
    for si, section in enumerate(sections):
        rows = []
        for ri, row in enumerate(section):
            cs = commands(row)
            conds, acts = split(row)
            routes = []
            if si > 1:
                jumps = [
                    (i, c)
                    for i, c in enumerate(cs)
                    if not c[0] and c[1] == -3 and c[2] in [0, 2]
                ]
                if len(jumps) == 1:
                    ci, jump = jumps[0]
                    dest, tokens = native_destination(jump, cs[:ci], frame, table)
                    for spot, stage in selected.items():
                        if spot == "boss_solgryn.ini":
                            continue
                        for target in stage["native_exit_frames"]:
                            if dest is not None and dest != target:
                                continue
                            if dest is None and tokens is None:
                                continue
                            gate = (
                                []
                                if dest is not None
                                else [compare(tokens, target, identifier=0x9F10)]
                            )
                            # Cheetah's exit exists invisibly before its victory animation.
                            if spot == "boss21.ini" and (si, ri) == (101, 0):
                                gate += split(sections[91][152])[0][:1]
                            kept = [
                                c[-1] for i, c in enumerate(cs) if not c[0] and i != ci
                            ]
                            routes.append(
                                ev(
                                    row,
                                    guarded(conds, enabled(stage) + gate),
                                    kept + dispatch(stage),
                                )
                            )
                            audit.append(
                                {
                                    "spot": spot,
                                    "section": si,
                                    "row": ri,
                                    "native_destination": target,
                                    "kind": "frame_exit",
                                }
                            )
                if frame == 46 and (si, ri) == (18, 200):
                    final = STAGES["boss_solgryn.ini"]
                    assert any(c[1:3] == (-3, 0) for c in cs if not c[0])
                    routes.append(
                        ev(
                            row,
                            conds
                            + [
                                check("Schema", 4),
                                check("CurrentStage", final["id"]),
                                check("Handled", 0),
                            ],
                            [
                                set_ini(GROUP, "Completed", 1, oi=ini),
                                set_ini(GROUP, "Handled", 1, oi=ini),
                                save,
                            ]
                            + acts,
                        )
                    )
                    audit.append(
                        {
                            "spot": "boss_solgryn.ini",
                            "section": si,
                            "row": ri,
                            "kind": "native_finale",
                        }
                    )
                # The beta bosses deliberately have no native next-frame action.
                if frame in [44, 45] and (si, ri) == (18, 4):
                    stage = STAGES["boss19.ini" if frame == 44 else "boss20.ini"]
                    assert b"Randomness\0" in row and len(conds) == 3 and len(acts) == 1
                    routes.append(
                        ev(row, guarded(conds, enabled(stage)), acts + dispatch(stage))
                    )
                    audit.append(
                        {
                            "spot": "boss19.ini" if frame == 44 else "boss20.ini",
                            "section": si,
                            "row": ri,
                            "kind": "native_beta_death",
                        }
                    )
            if routes:
                rows.extend(routes)
                rows.append(ev(row, guarded(conds, [check("Handled", 0)]), acts))
            else:
                rows.append(row)
            if frame == 5 and (si, ri) == (88, 35):
                assert any(c[1:4] == (2, 24, 464) for c in cs)
                rows[-1] = ev(
                    row, conds, acts + [set_ini(GROUP, "KrackoVictory", 1, oi=ini)]
                )
        result.append(rows)
    for spot, stage in selected.items():
        segment = stage.get("segment")
        if segment in REGIONS:
            rect = REGIONS[segment]
            x, y, right, bottom = rect
            for axis, op, value in [
                ("x", 3, x),
                ("x", 4, right),
                ("y", 3, y),
                ("y", 4, bottom),
            ]:
                extras.append(
                    ev(
                        template,
                        [
                            check("Schema", 4),
                            check("CurrentStage", stage["id"]),
                            check("Armed", 0),
                            xy(player, axis, op, value, 0x9F20),
                        ],
                        [set_ini(GROUP, "Armed", 1, oi=ini)],
                    )
                )
            extras.append(
                ev(
                    template,
                    enabled(stage) + [check("Armed", 1)] + inside(player, rect, 0x9F30),
                    dispatch(stage),
                )
            )
            audit.append({"spot": spot, "kind": "miniboss_entry", "rectangle": rect})
        elif segment == "kracko":
            rect = (3840, 0, 4480, 480)
            extras.append(
                ev(
                    template,
                    enabled(stage)
                    + [check("KrackoVictory", 1)]
                    + inside(player, rect, 0x9F40),
                    dispatch(stage),
                )
            )
            audit.append(
                {
                    "spot": spot,
                    "kind": "kracko_victory_then_next_screen",
                    "rectangle": rect,
                }
            )
        elif segment == "ninja_ryu":
            extras.append(
                ev(
                    template,
                    [check("Schema", 4), check("CurrentStage", stage["id"]), check("Armed", 0)]
                    + inside(player, (4480, 0, 5120, 480), 0x9F50),
                    [set_ini(GROUP, "Armed", 1, oi=ini)],
                )
            )
            extras.append(
                ev(
                    template,
                    enabled(stage)
                    + [check("Armed", 1)]
                    + inside(player, (5120, 0, 5760, 480), 0x9F60),
                    dispatch(stage),
                )
            )
            audit.append({"spot": spot, "kind": "ninja_ryu_next_screen"})
        elif segment == "kid_icarus":
            extras.append(
                ev(
                    template,
                    [
                        check("Schema", 4),
                        check("CurrentStage", stage["id"]),
                        check("KidSeen", 0),
                        count(1758, 1, 4),
                        count(1764, 1, 4),
                    ],
                    [set_ini(GROUP, "KidSeen", 1, oi=ini)],
                )
            )
            extras.append(
                ev(
                    template,
                    enabled(stage)
                    + [
                        check("KidSeen", 1),
                        count(1758, 0),
                        count(1759, 0),
                        count(1764, 0),
                    ]
                    + inside(player, (640, 6240, 1920, 6720), 0x9F70),
                    dispatch(stage),
                )
            )
            audit.append(
                {"spot": spot, "kind": "kid_icarus_defeated_and_exit_unblocked"}
            )
    # Run after the original Start-of-Frame file load, before region gates.
    result[-1] += prelude + extras
    assert next_identifier < 0xFFFF
    return result, {"frame": frame, "ini": ini, "player": player, "edges": audit}
