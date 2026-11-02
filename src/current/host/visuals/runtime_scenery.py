"""Native save-local scenery, preserving original backdrop masks and placements.

One temporary Active per backdrop type/layer loads its image once. Start events
recreate those backdrops in original placement order through Fusion's own Add
Backdrop action, including obstacle/platform type, then hide the helpers to retain their loaded images.
Original active scenery keeps all its animation and event logic.
"""

import copy
import json
import struct
from functools import lru_cache
from gameplay.native_events import Events
from native_menu.classic_events import load
from transition.events import action, expression, integer, parameter
from transition.router import frame_metadata, params
from gameplay.rewards import ini_string
from visuals.scenery_pack import PROTECTED, REPO
from visuals.scenery_cache import previous_frame

GROUP = "FusionSceneryV1"
DIRECTORY = "native-scenery"
PREFIX = "Randomizer Scenery "
# Moving these behind retained Quick Backdrops/other effects would change the
# original draw order. This conservative set is verified against every placement.
ORDER_PROTECTED = frozenset(
    (
        115,
        116,
        140,
        185,
        186,
        201,
        202,
        373,
        374,
        375,
        376,
        396,
        505,
        512,
        537,
        617,
        898,
        1246,
        1508,
        1509,
        1611,
        1620,
        1638,
        1650,
        1662,
        1709,
        1905,
        1912,
        2042,
        2060,
        2067,
        2116,
        2789,
        2792,
        2793,
        2890,
        2899,
        2902,
        2911,
    )
)


@lru_cache(maxsize=1)
def records():
    rows = json.loads(
        (REPO / "assets/catalogues/sprite_chaos_catalogue.json").read_text()
    )["records"]
    return tuple(
        r
        for r in rows
        if r["category"] in (1, 2, 4)
        and r["oi"] not in PROTECTED
        and r["oi"] not in ORDER_PROTECTED
    )


def helper(oi, layer):
    assert 0 <= layer < 8
    ident = 6000 + oi * 8 + layer
    assert ident < 32768
    return ident


def frame_records(frame):
    return [(i, r) for i, r in enumerate(records()) if frame in r["frames"]]


def placements(frame, instances):
    backdrops = {r["oi"]: (i, r) for i, r in frame_records(frame) if r["type"] == 1}
    return [
        (inst, *backdrops[inst["objectInfo"]])
        for inst in instances
        if inst["objectInfo"] in backdrops
    ]


def convert_frame(frame_number, frame, objects):
    """Never mutate recovered source objects/instances used by other transforms."""
    placed = placements(frame_number, frame["instances"])
    if not placed:
        return frame, objects
    result = copy.deepcopy(frame)
    objs = dict(enumerate(objects)) if not isinstance(objects, dict) else dict(objects)
    removed = {r["oi"] for _, _, r in placed}
    result["instances"] = [
        i for i in result["instances"] if i["objectInfo"] not in removed
    ]
    added = set()
    for inst, _, row in placed:
        key = helper(row["oi"], inst["layer"])
        if key in added:
            continue
        added.add(key)
        obj = copy.deepcopy(objs[41])
        obj.update(
            handle=key,
            name=PREFIX + str(row["oi"]) + "/" + str(inst["layer"]),
            values=[],
            qualifiers=[],
        )
        obj["animations"] = [
            dict(
                slot=0,
                name="Stopped",
                directions=[
                    dict(
                        direction=0,
                        minSpeed=0,
                        maxSpeed=0,
                        repeat=1,
                        backTo=0,
                        frames=[row["image"]],
                    )
                ],
            )
        ]
        # Keep the loaded animation referenced while this room is active.
        # Destroying the last helper also frees its replacement image.
        props = bytearray(obj["properties"])
        struct.pack_into(
            "<I", props, 16, struct.unpack_from("<I", props, 16)[0] | 0x2000
        )
        obj["properties"] = bytes(props)
        objs[key] = obj
        result["instances"].append(
            dict(
                handle=50000 + len(added),
                objectInfo=key,
                x=0,
                y=0,
                layer=inst["layer"],
                parentType=0,
                parentObjectInfo=0,
                tail="00 " * 8,
            )
        )
    return result, objs


def image_action(oi, row, index, ini):
    original = load(
        oi,
        "unused.png",
        animation=row["anim"],
        direction=row["direction"],
        frame=row["frame"],
        hx=row["hx"],
        hy=row["hy"],
    )
    ps = [p for _, p in params(original)]
    ps[0] = expression(ini_string(GROUP, "Image" + str(index), "", ini), 45)
    ps[6:8] = [expression(integer(row[k])) for k in ("ax", "ay")]
    return action(2, 89, oi, ps)


def transform(frame, sections, objects, instances):
    selected = frame_records(frame)
    if not selected:
        return sections, []
    ini, _, _ = frame_metadata(frame, sections, objects, instances)
    e = Events(sections, low=0x1000, high=0xFFFE)
    rows = [e.row([e.start()], [e.load(ini, "SaveFile1.ini")])]
    placed = placements(frame, instances)
    helpers = {}
    for inst, index, row in placed:
        helpers[helper(row["oi"], inst["layer"])] = (index, row)
    active = [(r["oi"], i, r) for i, r in selected if r["type"] == 2]
    for oi, index, row in [*((o, i, r) for o, (i, r) in helpers.items()), *active]:
        rows.append(
            e.row(
                [
                    e.start(),
                    e.eq(ini, GROUP, "Schema", 1),
                    e.eq(ini, GROUP, "EmbeddedOnly", 0),
                    e.cmp(previous_frame(), integer(frame), 1),
                ],
                [image_action(oi, row, index, ini)],
            )
        )
    # Keep every placement's original ordering, layer, hotspot and obstacle type.
    acts = []
    for inst, _, row in placed:
        oi = helper(row["oi"], inst["layer"])
        acts += [
            action(2, 2, oi, [expression(integer(inst["x"] + row["hx"]))]),
            action(2, 3, oi, [expression(integer(inst["y"] + row["hy"]))]),
            action(2, 83, oi, [parameter(43, struct.pack("<IH", row["obstacle"], 0))]),
        ]
    acts += [action(2, 26, oi, []) for oi in helpers]
    for offset in range(0, len(acts), 90):
        rows.append(e.row([e.start()], acts[offset : offset + 90]))
    result = [list(s) for s in sections]
    result[0][0:0] = rows
    return result, [
        dict(
            frame=frame,
            rule="runtime_scenery",
            helpers=len(helpers),
            placements=len(placed),
            active_images=len(active),
            original_order=True,
        )
    ]
