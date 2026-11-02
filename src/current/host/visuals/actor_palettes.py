"""Save-local actor colour variation without replacing any shared image handles.

Fusion action 66 changes an instance's RGB coefficient only. Applying it each
frame also covers late enemy spawns. Animation, alpha, hotspots, collisions,
original ink modes, fire, blood and all unlisted objects retain their rules.
"""

import hashlib
import struct
from transition.events import action, expression, ini_value, compare_ini, event
from transition.router import frame_metadata

GROUP = "FusionActorsV1"
PALETTES = (
    "ef95ba",
    "8fdaf2",
    "e9c26c",
    "b0ed8b",
    "c7a0f0",
    "f0a36b",
    "83e6d3",
    "e0e1ec",
)
ACTORS = {
    153: "Active 37",
    165: "Active 4",
    318: "hellokitty",
    553: "Active 15",
    561: "Active 27",
    1088: "EnemyWidgetTurn 2",
    1089: "EnemyWidgetTurn 3",
    2048: "Goomba",
    2084: "Goomba 2",
}


def colours(seed):
    """Keep the existing per-actor seed choice; COLORREF is little-endian RGB."""
    result = {}
    for oi in ACTORS:
        colour = min(
            PALETTES,
            key=lambda v: hashlib.sha256(
                f"boshy-graphics-v2\0{seed}\08\0{oi}\0#{v}".encode()
            ).digest(),
        )
        result[str(oi)] = int.from_bytes(bytes.fromhex(colour), "little")
    return result


def settings(seed, enabled):
    if type(enabled) is not bool:
        raise ValueError("Actor setting must be boolean")
    return {
        "Schema": 1,
        "Enabled": int(enabled),
        **{"RGB" + k: v for k, v in colours(seed).items()},
    }


def transform(frame, sections, objects, instances):
    present = {i["objectInfo"] for i in instances}
    selected = sorted(present & ACTORS.keys())
    if not selected:
        return sections, []
    for oi in selected:
        obj = objects[oi]
        assert obj["name"] == ACTORS[oi] and obj["type"] == 2, (frame, oi)
        assert not obj.get("shader"), ("Unreviewed actor shader", oi)
    ini, _, _ = frame_metadata(frame, sections, objects, instances)
    template = struct.pack("<hBB", -14, 0, 0) + bytes(10)
    extra, audit = [], []
    for index, oi in enumerate(selected):
        key = "RGB" + str(oi)
        guards = [
            compare_ini(GROUP, k, value, cmp, 0xB000 + index * 4 + n, oi=ini)
            for n, (k, value, cmp) in enumerate(
                [("Schema", 1, 0), ("Enabled", 1, 0), (key, 0, 4), (key, 0xFFFFFF, 2)]
            )
        ]
        tint = action(2, 66, oi, [expression(ini_value(GROUP, key, 0xFFFFFF, oi=ini))])
        extra.append(event(template, guards, [tint]))
        audit.append(
            {
                "frame": frame,
                "oi": oi,
                "name": ACTORS[oi],
                "action": "native_rgb_coefficient",
                "image_bank_changes": 0,
            }
        )
    return [*sections, extra], audit
