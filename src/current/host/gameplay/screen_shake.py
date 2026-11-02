"""Suppress only the original viewport's shake offsets, per save.

The original shaker, random draws, durations and boss triggers still run. Only
its two contributions to the camera source rectangle are multiplied by zero
when explicitly enabled. Missing settings retain the original camera behavior.
"""

import struct
from gameplay.native_extras import group, operator
from transition.events import commands, event, ini_value, integer, parameter
from transition.router import frame_metadata, params

GROUP = "FusionScreenShakeV1"
KEY = "Disabled"
OPTION = "no_screen_shaking"


def settings(extras):
    enabled = extras.get(OPTION, False)
    if type(enabled) is not bool:
        raise ValueError("Invalid screen shake option")
    return dict(Schema=1, Disabled=int(enabled))


def validate(plan, config):
    expected = settings(plan["options"]["extras"])
    schema = plan.get("screen_shake_schema")
    if schema is None:
        if expected[KEY]:
            raise ValueError("No Screen Shaking requires a newer native build")
        return
    if (
        schema != 1
        or not config.has_section(GROUP)
        or dict(config[GROUP]) != {k.lower(): str(v) for k, v in expected.items()}
    ):
        raise ValueError("Changed screen shake settings")


def tokens(data):
    """Walk validated Fusion expression tokens, including their object lists."""
    offset = 0
    while offset < len(data):
        assert offset + 6 <= len(data), "Truncated expression"
        kind, code, size = struct.unpack_from("<hhH", data, offset)
        assert size >= 6 and offset + size <= len(data), "Invalid expression token"
        raw = data[offset : offset + size]
        yield kind, code, raw
        offset += size


def offset_token(kind, code, raw, shakers):
    return (
        (kind, code) == (2, 16)
        and len(raw) == 12
        and struct.unpack_from("<H", raw, 6)[0] in shakers
        and struct.unpack_from("<H", raw, 10)[0] in (1, 2)
    )


def gated_offset(raw, ini):
    # Fusion operators: 4 = subtract; 6 = multiply. Explicit parentheses keep
    # the surrounding original camera expression's precedence unchanged.
    return group(
        raw
        + operator(6)
        + group(integer(1) + operator(4) + ini_value(GROUP, KEY, oi=ini))
    )


def transform(frame, sections, objects, instances):
    shakers = {oi for oi, obj in objects.items() if obj["name"] == "Screen Shaker"}
    result, audit = [], []
    ini = None
    for si, rows in enumerate(sections):
        out = []
        result.append(out)
        for ri, row in enumerate(rows):
            rewritten = []
            changed = 0
            for condition, kind, code, oi, raw in commands(row):
                # Only viewport source-rectangle actions consume shake offsets.
                if condition or (kind, code) != (34, 83):
                    rewritten.append((condition, raw))
                    continue
                new_params = []
                for pk, p in params(raw):
                    if pk not in (22, 23, 45):
                        new_params.append(p)
                        continue
                    parts = []
                    for tk, tc, token in tokens(p[6:-4]):
                        if offset_token(tk, tc, token, shakers):
                            if ini is None:
                                ini, _, _ = frame_metadata(
                                    frame, sections, objects, instances
                                )
                            token = gated_offset(token, ini)
                            changed += 1
                        parts.append(token)
                    new_params.append(parameter(pk, p[4:6] + b"".join(parts) + p[-4:]))
                body = b"".join(new_params)
                header = bytearray(raw[:14])
                struct.pack_into("<H", header, 0, 14 + len(body))
                rewritten.append((condition, bytes(header) + body))
            if changed:
                row = event(
                    row,
                    [r for c, r in rewritten if c],
                    [r for c, r in rewritten if not c],
                )
                audit.append(
                    dict(frame=frame, section=si, row=ri, offsets=changed, ini=ini)
                )
            out.append(row)
    return result, audit
