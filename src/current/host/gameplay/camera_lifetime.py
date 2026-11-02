"""Keep the rendering viewport alive during extreme native player knockback.

Sonic's falling platforms can send an invulnerable player thousands of pixels
above the room. The viewport follows that position and Fusion otherwise destroys
it as too far from the playfield. Keep this camera helper, never gameplay actors.
Explicit original Destroy actions (including DeleteView) still work.

Flag source: reference-clickteam-sdk/Inc/Cncf.h, OEFLAG_NEVERKILL.
"""

import struct

NEVER_DESTROY_FAR = 0x2000
FLAGS_OFFSET = 0x10


def properties(raw):
    if len(raw) < FLAGS_OFFSET + 4:
        raise ValueError("Truncated viewport properties")
    patched = bytearray(raw)
    flags = struct.unpack_from("<I", raw, FLAGS_OFFSET)[0]
    struct.pack_into("<I", patched, FLAGS_OFFSET, flags | NEVER_DESTROY_FAR)
    return bytes(patched)


def protect(objects):
    source = objects if isinstance(objects, dict) else dict(enumerate(objects))
    result = {
        oi: dict(obj, properties=properties(obj["properties"]))
        if obj.get("type") == 34 and obj.get("name") == "Viewport 2"
        else obj
        for oi, obj in source.items()
    }
    return result if isinstance(objects, dict) else list(result.values())
