"""Native mixed reward events: separate chest receipts and dynamic Ini++ grants.

Only the 36 reviewed chest behaviours change. Boss gates, pickups, timing,
movement and all unrelated actions remain native. No runtime hooks are used.
"""

import struct
from gameplay.reward_plan import LOCATIONS, GROUP, CHECKS
from transition.events import (
    commands,
    event,
    expression,
    string,
    integer,
    action,
    compare_ini,
    set_ini,
)
from transition.router import params, guarded


def ini_string(group, key, default, oi):
    sep = struct.pack("<hhH", -1, -3, 6)
    return (
        struct.pack("<hhHHH", 33, 89, 10, oi, 0)
        + string(group)
        + sep
        + string(key)
        + sep
        + string(default)
        + struct.pack("<hhH", -1, -2, 6)
    )


def rewrite(raw, condition, ps):
    head = 16 if condition else 14
    result = raw[:head] + b"".join(ps)
    return struct.pack("<H", len(result)) + result[2:]


def transform(frame, sections):
    locations = [l for l in LOCATIONS if l["scene"] + 1 == frame]
    if not locations:
        return sections, []
    used = {
        struct.unpack_from("<H", c[-1], 14)[0]
        for rows in sections
        for row in rows
        for c in commands(row)
        if c[0]
    }

    def ident():
        n = next(n for n in range(0xCB00, 0xCE00) if n not in used)
        used.add(n)
        return n

    def fresh(raw):
        return raw[:14] + struct.pack("<H", ident()) + raw[16:]

    out = [list(rows) for rows in sections]
    audit = []
    for loc in locations:
        oi = loc["object"]
        key = loc["key"]
        save = int.from_bytes(bytes.fromhex(loc["save_ref"])[:2], "little")
        license = int.from_bytes(bytes.fromhex(loc["license_ref"])[:2], "little")
        getter = struct.pack("<hhHHHH", 2, 19, 12, oi, 0, 0)
        name = ini_string(GROUP, "Name" + key, loc["source"], save)
        matches = []
        for si, rows in enumerate(out):
            if any(
                not c[0]
                and c[1:3] == (33, 94)
                and params(c[-1], False)[1][1] == expression(getter, 45)
                for row in rows
                for c in commands(row)
            ):
                matches.append(si)
        assert len(matches) == 1, (frame, key, matches)
        si = matches[0]
        result = []
        counts = dict(grants=0, checks=0, displays=0)
        for row in out[si]:
            cs = commands(row)
            conditions = [c[-1] for c in cs if c[0]]
            actions = [c[-1] for c in cs if not c[0]]
            grants = [
                i
                for i, c in enumerate(cs[row[2] :])
                if c[1:3] == (33, 94)
                and params(c[-1], False)[1][1] == expression(getter, 45)
            ]
            consumed = [
                i
                for i, c in enumerate(cs[: row[2]])
                if c[1:3] == (-1, -3)
                and getter in c[-1]
                and (b"Unlockables\0" in c[-1] or b"Collectables\0" in c[-1])
            ]
            for i in consumed:
                assert len(conditions) == 1 and any(
                    c[1:4] == (2, 24, oi) for c in cs if not c[0]
                )
                conditions[i] = compare_ini(CHECKS, key, 1, 0, ident(), oi=save)
                counts["checks"] += 1
            captions = []
            for i, c in enumerate(cs[row[2] :]):
                if c[1:3] in ((-1, 19), (32, 49)) and getter in c[-1]:
                    ps = [p for _, p in params(c[-1], False)]
                    if c[1:3] == (32, 49):
                        captions.append(i)
                        ps[-1] = expression(name, 45)
                    else:
                        ps[-1] = expression(name, 45)
                    actions[i] = rewrite(c[-1], False, ps)
                    counts["displays"] += 1
                if c[1:3] == (37, 82):
                    ps = [p for _, p in params(c[-1], False)]
                    # Keep original item help when mixing is off; use the actual
                    # reward name when on, instead of instructions for a wrong item.
                    for j in range(2):
                        raw = ps[j][12:-4].split(b"\0", 1)[0].decode("ascii")
                        ps[j] = expression(
                            ini_string(
                                GROUP, ("Text" if j == 0 else "Title") + key, raw, save
                            ),
                            45,
                        )
                    actions[i] = rewrite(c[-1], False, ps)
            def kind_guard(kind):
                from transition.events import ini_value

                gate = compare_ini(GROUP, "Kind" + key, kind, 0, ident(), oi=save)
                if loc["source_kind"] == "character":
                    gate = gate.replace(
                        ini_value(GROUP, "Kind" + key, 0, oi=save),
                        ini_value(GROUP, "Kind" + key, 1, oi=save),
                    )
                return gate

            def captioned(aa, kind):
                aa = list(aa)
                heading = "\r\nCharacter unlocked!!\r\n" if kind else "\r\nSECRET ITEM!\r\n"
                tokens = string(heading) + struct.pack("<hhH", 0, 2, 6) + name
                for index in captions:
                    ps = [p for _, p in params(aa[index], False)]
                    ps[-1] = expression(tokens, 45)
                    aa[index] = rewrite(aa[index], False, ps)
                return aa

            if grants:
                assert len(grants) == 1
                # The touched chest follows Boshy during its animation; the chest
                # flag is stable even when the original collision no longer is.
                collision = [i for i, c in enumerate(cs[: row[2]]) if c[1:3] == (2, -4)]
                assert len(collision) == 1, (frame, key)
                flag = expression(integer(0))
                conditions[collision[0]] = (
                    struct.pack(
                        "<HhhHHHBBH", 16 + len(flag), 2, -25, oi, 0, 0x20, 1, 0, ident()
                    )
                    + flag
                )
                conditions.append(compare_ini(CHECKS, key, 0, 0, ident(), oi=save))
                for kind, target, group in [
                    (0, save, "Collectables"),
                    (1, license, "Unlockables"),
                ]:
                    branch = [fresh(c) for c in conditions]
                    branch.append(kind_guard(kind))
                    grant = action(
                        33,
                        94,
                        target,
                        [
                            expression(string(group), 45),
                            expression(name, 45),
                            expression(integer(0)),
                            expression(integer(1)),
                        ],
                    )
                    aa = captioned(actions, kind)
                    aa[grants[0] : grants[0] + 1] = [
                        grant,
                        set_ini(CHECKS, key, 1, oi=save),
                    ]
                    result.append(event(row, branch, aa))
                counts["grants"] += 1
            elif captions:
                # One message per pickup, labelled by the actual randomized kind.
                # Retain every original trigger, including any OR branches.
                for kind in (0, 1):
                    branch = [fresh(c) for c in guarded(conditions, [kind_guard(kind)])]
                    result.append(event(row, branch, captioned(actions, kind)))
            else:
                result.append(event(row, conditions, actions))
        assert (
            counts["checks"] == 1
            and counts["grants"] in (1, 2)
            and counts["displays"] in (1, 2)
        ), (key, counts)
        out[si] = result
        audit.append(dict(frame=frame, key=key, section=si, **counts))
    return out, audit
