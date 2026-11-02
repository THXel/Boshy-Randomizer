"""Rebuild optimized image records from the user's original pixels.

Only changed/new artwork needs a literal payload. Original artwork is referenced
by handle, transformed into the target pixel layout and deterministically
compressed. Every record is checked against the compiled target's hash.
"""

import base64
import ctypes
import struct
from distribution.source_audio import digest
from visuals.fusion25 import _LZ4, image_bank, write_images, lz4_decode
from visuals.scenery_pack import image, ORIGINAL_SHA
from klikback.core.mmf2.write_mfa import inflated_images


def compress(raw):
    _LZ4.LZ4_compress_HC.argtypes = (
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
    )
    capacity = _LZ4.LZ4_compressBound(len(raw))
    target = ctypes.create_string_buffer(capacity)
    size = _LZ4.LZ4_compress_HC(raw, target, len(raw), capacity, 10)
    if size <= 0:
        raise ValueError("Image compression failed")
    return target.raw[:size]


def pixels(original, alpha):
    im = image(original, max_side=16384)
    raw = bytearray(im.tobytes("raw", "BGRA"))
    raw[3::4] = bytes(im.width * im.height)
    if alpha:
        plane = im.getchannel("A").tobytes()
        stride = (im.width + 3) // 4 * 4
        raw += b"".join(
            plane[y * im.width : (y + 1) * im.width] + bytes(stride - im.width)
            for y in range(im.height)
        )
    return bytes(raw)


def recipe(original, target):
    if digest(original.data) != ORIGINAL_SHA:
        raise ValueError("Unsupported original game")
    source = inflated_images(original)
    bank, slots = image_bank(target.payload(0x6666), target.payload(0x5555))
    rows, literals = [], {}
    # Index both layouts so cloned native objects also reuse original artwork.
    lookup = {}
    for handle, raw in source.items():
        for alpha in (False, True):
            try:
                lookup.setdefault(digest(pixels(raw, alpha)), handle)
            except ValueError:
                pass  # An unsupported original format cannot be guessed.
    for handle, stored in bank.items():
        raw = lz4_decode(stored.packed, struct.unpack_from("<I", stored.header, 40)[0])
        source_handle = lookup.get(digest(raw))
        row = {
            "handle": handle,
            "header": base64.b64encode(stored.header).decode(),
            "record_sha256": digest(stored.bytes()),
        }
        if source_handle is None:
            row["literal"] = str(handle)
            literals[str(handle)] = stored.packed
        else:
            if compress(raw) != stored.packed:
                raise ValueError(
                    f"Original image {handle} needs a different compressor; refusing to bundle it"
                )
            row["source_handle"] = source_handle
        rows.append(row)
    return {
        "schema": 1,
        "source_sha256": ORIGINAL_SHA,
        "slots": slots,
        "rows": rows,
        "bank_sha256": digest(target.payload(0x6666)),
        "offsets_sha256": digest(target.payload(0x5555)),
    }, literals


def restore(original, specification, literals, progress=None):
    from visuals.fusion25 import StoredImage

    if (
        specification.get("schema") != 1
        or specification.get("source_sha256") != ORIGINAL_SHA
        or digest(original.data) != ORIGINAL_SHA
    ):
        raise ValueError("Unsupported image recipe or original")
    slots = specification["slots"]
    if type(slots) is not int or not 0 < slots <= 65536:
        raise ValueError("Invalid image slot count")
    source = inflated_images(original)
    result = {}
    if progress:
        progress("images", 0, len(specification["rows"]))
    for index, row in enumerate(specification["rows"], 1):
        handle = row["handle"]
        if type(handle) is not int or not 0 <= handle < slots or handle in result:
            raise ValueError("Duplicate or invalid image handle")
        head = base64.b64decode(row["header"], validate=True)
        if (
            len(head) != 44
            or struct.unpack_from("<I", head)[0] != handle + 1
            or head[24] != 8
            or head[25] not in (8, 24)
        ):
            raise ValueError("Invalid image record header")
        if "source_handle" in row:
            raw = pixels(source[row["source_handle"]], bool(head[25] & 16))
            if len(raw) != struct.unpack_from("<I", head, 40)[0]:
                raise ValueError("Reconstructed image dimensions differ")
            packed = compress(raw)
        else:
            packed = literals[row["literal"]]
        stored = StoredImage(handle, head, packed)
        if digest(stored.bytes()) != row["record_sha256"]:
            raise ValueError("Reconstructed image checksum differs")
        result[handle] = stored
        if progress:
            progress("images", index, len(specification["rows"]))
    bank, offsets = write_images(result, slots)
    if (
        digest(bank) != specification["bank_sha256"]
        or digest(offsets) != specification["offsets_sha256"]
    ):
        raise ValueError("Reconstructed image bank differs")
    return bank, offsets
