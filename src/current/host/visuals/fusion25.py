"""Strict reader/writer for the hash-pinned Fusion 295 optimized graphics banks.

Format cross-check: AITYunivers/NebulaFD a24d4d1, Image2.5Plus.cs and
ObjectProperties.cs. All executable code and unrelated chunks are carried intact.
"""

import ctypes
import os
import sys
from pathlib import Path
import ctypes.util
import struct
import zlib
from dataclasses import dataclass
from PIL import Image


@dataclass
class StoredImage:
    handle: int
    header: bytes
    packed: bytes

    @property
    def size(self):
        return struct.unpack_from("<HH", self.header, 20)

    def rgba(self):
        width, height = self.size
        if self.header[24] != 8 or self.header[25] not in (8, 24):
            raise ValueError("Unsupported optimized pixel format")
        n = struct.unpack_from("<I", self.header, 40)[0]
        pixel_size = width * height * 4
        alpha_size = ((width + 3) // 4 * 4) * height if self.header[25] & 16 else 0
        if not 0 < n == pixel_size + alpha_size <= 64_000_000:
            raise ValueError("Unexpected pixel size")
        raw = lz4_decode(self.packed, n)
        im = Image.frombytes("RGBA", self.size, raw[:pixel_size], "raw", "BGRA")
        if alpha_size:
            im.putalpha(
                Image.frombytes(
                    "L", self.size, raw[pixel_size:], "raw", "L", (width + 3) // 4 * 4
                )
            )
        if not self.header[25] & 16:
            key = struct.unpack_from("<I", self.header, 36)[0]
            rgb = bytes((key & 255, (key >> 8) & 255, (key >> 16) & 255))
            pixels = im.convert("RGB").tobytes()
            im.putalpha(
                Image.frombytes(
                    "L",
                    self.size,
                    bytes(
                        0 if pixels[i : i + 3] == rgb else 255
                        for i in range(0, len(pixels), 3)
                    ),
                )
            )
        return im

    def clone(self, handle, im):
        original = self.rgba()
        if (
            im.mode != "RGBA"
            or im.size != self.size
            or im.getchannel("A").tobytes() != original.getchannel("A").tobytes()
        ):
            raise ValueError("Texture changed geometry or alpha")
        alpha = im.getchannel("A").tobytes()
        stride = (im.width + 3) // 4 * 4
        plane = b"".join(
            alpha[y * im.width : (y + 1) * im.width] + bytes(stride - im.width)
            for y in range(im.height)
        )
        pixels = im.tobytes("raw", "BGRA") + plane
        packed = lz4_encode(pixels)
        head = bytearray(self.header)
        struct.pack_into("<I", head, 0, handle + 1)
        struct.pack_into("<I", head, 4, 0xFFFFFFFF)
        struct.pack_into("<I", head, 8, 1)
        struct.pack_into("<I", head, 16, len(packed) + 4)
        struct.pack_into("<I", head, 40, len(pixels))
        head[25] = 24  # explicit alpha retains every original cutout
        return StoredImage(handle, bytes(head), packed)

    def bytes(self):
        return self.header + self.packed


def lz4_library():
    name = (str(Path(sys.executable).parent / "liblz4.dll")
            if os.name == "nt" else ctypes.util.find_library("lz4"))
    if not name:
        raise RuntimeError("The bundled LZ4 library is missing")
    lib = ctypes.CDLL(name)
    lib.LZ4_decompress_safe.argtypes = [
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
    ]
    lib.LZ4_compressBound.argtypes = [ctypes.c_int]
    lib.LZ4_compress_default.argtypes = [
        ctypes.c_char_p,
        ctypes.c_void_p,
        ctypes.c_int,
        ctypes.c_int,
    ]
    return lib


_LZ4 = lz4_library()


def lz4_decode(data, size):
    out = ctypes.create_string_buffer(size)
    if _LZ4.LZ4_decompress_safe(data, out, len(data), size) != size:
        raise ValueError("LZ4 length or stream mismatch")
    return out.raw


def lz4_encode(data):
    cap = _LZ4.LZ4_compressBound(len(data))
    out = ctypes.create_string_buffer(cap)
    size = _LZ4.LZ4_compress_default(data, out, len(data), cap)
    if size <= 0:
        raise ValueError("LZ4 compression failed")
    return out.raw[:size]


def image_bank(data, offsets):
    index = struct.unpack("<%dI" % (len(offsets) // 4), offsets)
    count = struct.unpack_from("<I", data)[0]
    pos, result = 4, {}
    for _ in range(count):
        header = data[pos : pos + 44]
        if len(header) != 44:
            raise ValueError("Truncated image header")
        handle = struct.unpack_from("<I", header)[0] - 1
        size = struct.unpack_from("<I", header, 16)[0]
        end = pos + 40 + size
        if (
            size < 4
            or end > len(data)
            or handle in result
            or not 0 <= handle < len(index)
            or index[handle] != pos + 260
        ):
            raise ValueError("Image boundary or index mismatch")
        result[handle] = StoredImage(handle, header, data[pos + 44 : end])
        pos = end
    if pos != len(data) or any(v and i not in result for i, v in enumerate(index)):
        raise ValueError("Unconsumed image bank or orphan index")
    return result, len(index)


def write_images(images, index_size):
    out = bytearray(struct.pack("<I", len(images)))
    index = [0] * index_size
    for handle, im in images.items():
        if not 0 <= handle < index_size or im.handle != handle:
            raise ValueError("Invalid image handle")
        index[handle] = len(out) + 260
        out.extend(im.bytes())
    return bytes(out), struct.pack("<%dI" % index_size, *index)


def property_bank(data, offsets):
    index = struct.unpack("<%dI" % (len(offsets) // 4), offsets)
    result = []
    pos = 0
    for expected in index:
        if expected != pos or pos + 8 > len(data):
            raise ValueError("Property index mismatch")
        size, packed = struct.unpack_from("<II", data, pos)
        dec = zlib.decompressobj()
        raw = dec.decompress(data[pos + 8 : pos + 8 + packed], size + 1)
        if len(raw) != size or not dec.eof or dec.unused_data:
            raise ValueError("Property compression mismatch")
        result.append(raw)
        pos += 8 + packed
    if pos != len(data):
        raise ValueError("Unconsumed property data")
    return result


def write_properties(properties):
    out, index = bytearray(), []
    for raw in properties:
        index.append(len(out))
        packed = zlib.compress(raw, 9)
        out.extend(struct.pack("<II", len(raw), len(packed)) + packed)
    return bytes(out), struct.pack("<%dI" % len(index), *index)


def animation_slot(body, anim, direction, frame):
    # Optimized object header interchanges movement/animation offsets.
    start = struct.unpack_from("<H", body, 4)[0]
    size, count = struct.unpack_from("<HH", body, start)
    if not 0 <= anim < count or start + size > len(body):
        raise ValueError("Animation bounds")
    offset = struct.unpack_from("<H", body, start + 4 + anim * 2)[0]
    if not offset or not 0 <= direction < 32:
        raise ValueError("Animation absent")
    doff = struct.unpack_from("<H", body, start + offset + direction * 2)[0]
    d = start + offset + doff
    nframes = struct.unpack_from("<H", body, d + 6)[0]
    at = d + 8 + frame * 2
    if not doff or not 0 <= frame < nframes or at + 2 > start + size:
        raise ValueError("Animation frame absent")
    return at


def integrity_sum(data):
    """Fusion 295 data checksum, verified against loader at 0x4026b7/0x4026e1."""
    value = 0
    end = len(data) // 4 * 4
    for (word,) in struct.iter_unpack("<I", data[:end]):
        value = ((value << 1) + (value >> 31) + word) & 0xFFFFFFFF
    for byte in data[end:]:
        value = ((value << 1) + (value >> 31) + byte) & 0xFFFFFFFF
    return value


def rebuild(app, replacements, *, sound_bank=False):
    allowed = {0x6668, 0x5557} if sound_bank else {0x2256, 0x2257, 0x6666, 0x5555}
    if not replacements.keys() <= allowed:
        raise ValueError("Only the selected native bank and its references may change")
    parts = [app.data[: app.chunks[0].offset]]
    end = 0
    for chunk in app.chunks:
        end = chunk.offset + 8 + chunk.size
        if chunk.id == 0x2242 and replacements:
            # Keep the native integrity check. The four-byte stream-encrypted
            # checksum is adjusted by XOR delta; its key-bearing name/copyright/
            # editor-path chunks are immutable. No engine instructions change.
            if chunk.flags != 2 or chunk.size != 4:
                raise ValueError("Unexpected integrity record")
            old_start = app.by_id[0x222F][0].offset
            prefix = b"".join(parts)
            # All permitted edits occur after TargetFilename, so start is stable.
            before = integrity_sum(app.data[old_start : chunk.offset])
            after = integrity_sum(prefix[old_start:])
            encrypted = struct.unpack_from("<I", app.data, chunk.offset + 8)[0]
            parts.append(
                app.data[chunk.offset : chunk.offset + 8]
                + struct.pack("<I", encrypted ^ before ^ after)
            )
        elif chunk.id not in replacements:
            parts.append(app.data[chunk.offset : end])
        else:
            raw = replacements[chunk.id]
            if chunk.flags == 1:
                packed = zlib.compress(raw, 9)
                raw = struct.pack("<II", len(raw), len(packed)) + packed
            elif chunk.flags != 0:
                raise ValueError("Unexpected encrypted graphics chunk")
            parts.append(struct.pack("<HHI", chunk.id, chunk.flags, len(raw)) + raw)
    parts.append(app.data[end:])
    return b"".join(parts)
