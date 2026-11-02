"""One isolated native spider/controller per playable scene; original artwork."""

import copy
import struct
from gameplay.normal_plan import FRAMES

OBJECT = 4100
NAME = "Randomizer Spider"
IMAGE = 2287


def convert_frame(number, frame, objects):
    if number not in FRAMES:
        return frame, objects
    result = copy.deepcopy(frame)
    objs = dict(objects) if isinstance(objects, dict) else dict(enumerate(objects))
    assert OBJECT not in objs
    obj = copy.deepcopy(objs[41])
    obj.update(handle=OBJECT, name=NAME, values=[0] * 12, qualifiers=[])
    props = bytearray(obj["properties"])
    # Controller stays awake and survives outside the room between attacks.
    struct.pack_into("<I", props, 16, struct.unpack_from("<I", props, 16)[0] | 0x6000)
    obj["properties"] = bytes(props)
    obj["animations"][0]["directions"][0]["frames"] = [IMAGE]
    objs[OBJECT] = obj
    player_layers = {
        i["layer"]
        for i in frame["instances"]
        if objs[i["objectInfo"]]["name"] == "Player"
    }
    assert len(player_layers) == 1
    result["instances"].append(
        dict(
            handle=54100,
            objectInfo=OBJECT,
            x=-200,
            y=-200,
            layer=player_layers.pop(),
            parentType=0,
            parentObjectInfo=0,
            tail="00 " * 8,
        )
    )
    return result, objs
