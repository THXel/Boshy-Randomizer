"""Compile local blood packs once; select an animation per save at native death.

Only the two existing blood objects gain animations. Vanilla animation zero,
enemy creation, player death conditions and all audio remain untouched.
"""

import copy
import struct
from functools import lru_cache
from pathlib import Path
from visuals.blood_pack import load_pack
from visuals.player_blood import BLOOD

from app_paths import SOUNDPACKS as PACK_ROOT
from music.packs import ANIMATIONS as PACKS
FIRST_IMAGE = 20000


@lru_cache(maxsize=1)
def assets():
    result = {}
    handle = FIRST_IMAGE
    for name, animation in PACKS.items():
        images, origin, fps = load_pack(PACK_ROOT / name)
        handles = list(range(handle, handle + len(images)))
        result[name] = dict(
            animation=animation, images=images, origin=origin, fps=fps, handles=handles
        )
        handle += len(images)
    return result


def settings(pack):
    if pack == "original":
        return dict(Schema=1, Animation=0, LifeTicks=0)
    images, origin, fps = load_pack(PACK_ROOT / pack)
    return dict(
        Schema=1,
        Animation=PACKS[pack],
        LifeTicks=(len(images) * 50 + fps - 1) // fps + 1,
    )


def extend_object(obj):
    if obj["handle"] not in BLOOD:
        return obj
    assert [a["slot"] for a in obj["animations"]] == [0, 15]
    result = copy.deepcopy(obj)
    for name, data in assets().items():
        result["animations"].append(
            dict(
                slot=data["animation"],
                name="Player blood " + name,
                directions=[
                    dict(
                        direction=0,
                        minSpeed=2 * data["fps"],
                        maxSpeed=2 * data["fps"],
                        repeat=0,
                        backTo=0,
                        frames=data["handles"],
                    )
                ],
            )
        )
    return result


def raw_image(image, origin):
    w, h = image.size
    rgb = image.convert("RGB").tobytes("raw", "BGR")
    alpha = image.getchannel("A").tobytes()
    color_stride = (w + 1) // 2 * 2 * 3
    alpha_stride = (w + 3) // 4 * 4
    body = b"".join(
        rgb[y * w * 3 : (y + 1) * w * 3] + bytes(color_stride - w * 3) for y in range(h)
    )
    body += b"".join(
        alpha[y * w : (y + 1) * w] + bytes(alpha_stride - w) for y in range(h)
    )
    head = bytearray(32)
    struct.pack_into(
        "<IIIHHBBHhhhhI",
        head,
        0,
        0xFFFFFFFF,
        0,
        len(body),
        w,
        h,
        4,
        0x10,
        0,
        *origin,
        0,
        0,
        0
    )
    return bytes(head) + body


def image_loader(original):
    def load(app):
        images = dict(original(app))
        for data in assets().values():
            for handle, image in zip(data["handles"], data["images"]):
                if handle in images:
                    raise ValueError("Embedded blood image handle collision")
                images[handle] = raw_image(image, data["origin"])
        return images

    return load


def install(writer, blood):
    """Attach at the source writer boundary, after existing blood placeholders."""
    previous = blood.extend_object
    blood.extend_object = lambda obj: extend_object(previous(obj))
    writer.inflated_images = image_loader(writer.inflated_images)
