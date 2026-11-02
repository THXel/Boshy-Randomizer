"""Import locally supplied blood PNGs into dedicated native animation 15.

This exporter never replaces vanilla images or the death screen. The source
MFA must contain the player-owned creation/lifetime events and 32 placeholders.
"""

import hashlib
import json
import struct
from pathlib import Path
from PIL import Image
from visuals.scenery_pack import App, object_mapping, ORIGINAL_SHA
from visuals.fusion25 import (
    StoredImage,
    lz4_encode,
    image_bank,
    property_bank,
    animation_slot,
    write_images,
    write_properties,
    rebuild,
)
from visuals.player_blood import BLOOD, ANIMATION


def load_pack(root):
    root = Path(root).resolve()
    data = json.loads((root / "pack.json").read_text())
    visual = data.get("death_visuals", {})
    if visual.get("version") != 1:
        raise ValueError("Unsupported death visual manifest")
    blood = visual["blood"]
    frames, fps, size, origin = (blood[k] for k in ("frames", "fps", "size", "origin"))
    if not isinstance(frames, list) or not 1 <= len(frames) <= 32:
        raise ValueError("Blood frame count")
    if type(fps) is not int or not 1 <= fps <= 50 or 100 * fps % 50:
        raise ValueError("Blood frame rate")
    if (
        len(size) != 2
        or len(origin) != 2
        or any(type(v) is not int for v in [*size, *origin])
    ):
        raise ValueError("Blood geometry")
    if not all(1 <= v <= 64 for v in size) or not all(
        0 <= v < s for v, s in zip(origin, size)
    ):
        raise ValueError("Blood geometry")
    images = []
    for row in frames:
        rel = Path(row["file"])
        path = root / rel
        if (
            rel.is_absolute()
            or ".." in rel.parts
            or path.is_symlink()
            or not path.resolve().is_relative_to(root)
        ):
            raise ValueError("Blood image path")
        raw = path.read_bytes()
        if len(raw) > 2_000_000 or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError("Blood image checksum")
        with Image.open(path) as im:
            if im.format != "PNG" or im.size != tuple(size):
                raise ValueError("Blood image dimensions")
            images.append(im.convert("RGBA"))
    return images, origin, fps


def encode_image(template, handle, image, origin):
    alpha = image.getchannel("A").tobytes()
    stride = (image.width + 3) // 4 * 4
    plane = b"".join(
        alpha[y * image.width : (y + 1) * image.width] + bytes(stride - image.width)
        for y in range(image.height)
    )
    pixels = image.tobytes("raw", "BGRA") + plane
    packed = lz4_encode(pixels)
    head = bytearray(template.header)
    struct.pack_into("<III", head, 0, handle + 1, 0xFFFFFFFF, 2)
    struct.pack_into("<IHH", head, 16, len(packed) + 4, *image.size)
    head[24:26] = bytes((8, 24))
    struct.pack_into("<4h", head, 28, *origin, 0, 0)
    struct.pack_into("<I", head, 40, len(pixels))
    result = StoredImage(handle, bytes(head), packed)
    assert result.rgba().tobytes() == image.tobytes()
    return result


def prepare(base, original, pack, expected_sha):
    app = App(base)
    if hashlib.sha256(app.data).hexdigest() != expected_sha:
        raise ValueError("Unsupported player-blood build")
    source = App(original)
    if hashlib.sha256(source.data).hexdigest() != ORIGINAL_SHA:
        raise ValueError("Unsupported source game")
    frames, origin, fps = load_pack(pack)
    mapping = object_mapping(app, source.objects()[0], active_only=True)
    images, size = image_bank(app.payload(0x6666), app.payload(0x5555))
    props = property_bank(app.payload(0x2256), app.payload(0x2257))
    original_count = len(images)
    template = images[
        struct.unpack_from(
            "<H", props[mapping[105]], animation_slot(props[mapping[105]], 15, 0, 0)
        )[0]
    ]
    handles = []
    for im in frames:
        if size >= 32768:
            raise ValueError("Image capacity")
        images[size] = encode_image(template, size, im, origin)
        handles.append(size)
        size += 1
    changes = []
    for oi in BLOOD:
        compiled = mapping[oi]
        body = bytearray(props[compiled])
        positions = []
        for index in range(32):
            at = animation_slot(body, ANIMATION, 0, index)
            positions.append(at)
            struct.pack_into("<H", body, at, handles[min(index, len(handles) - 1)])
        direction = positions[0] - 8
        body[direction : direction + 2] = bytes((2 * fps, 2 * fps))
        props[compiled] = bytes(body)
        changes.append(
            dict(
                source_oi=oi,
                compiled_oi=compiled,
                image_offsets=positions,
                speed_offset=direction,
            )
        )
    ib, ix = write_images(images, size)
    pb, px = write_properties(props)
    output = rebuild(app, {0x6666: ib, 0x5555: ix, 0x2256: pb, 0x2257: px})
    return output, dict(
        schema=1,
        pack=Path(pack).name,
        frames=len(frames),
        fps=fps,
        origin=origin,
        base_sha256=expected_sha,
        sha256=hashlib.sha256(output).hexdigest(),
        settings=dict(
            Schema=1, Animation=15, LifeTicks=(len(frames) * 50 + fps - 1) // fps + 1
        ),
        original_images_preserved=original_count,
        handles=handles,
        changed=changes,
        scope="native player blood; vanilla enemy blood and game audio untouched",
    )
