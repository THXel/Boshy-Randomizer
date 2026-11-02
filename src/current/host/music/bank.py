"""Strict Fusion 295 Unicode sound bank; preserve every non-music record."""

import struct
import zlib
from dataclasses import dataclass


@dataclass(frozen=True)
class Sound:
    handle: int
    name: str
    header: bytes
    raw: bytes
    stored: bytes

    @property
    def name_bytes(self):
        return struct.unpack_from("<I", self.header, 24)[0] * 2

    @property
    def audio(self):
        return self.raw[self.name_bytes :]

    def replace(self, audio):
        if not audio.startswith((b"OggS", b"RIFF", b"ID3")):
            raise ValueError("Unsupported embedded audio")
        raw = self.raw[: self.name_bytes] + audio
        if len(raw) > 32_000_000:
            raise ValueError("Sound too large")
        packed = zlib.compress(raw, 9)
        head = bytearray(self.header)
        struct.pack_into("<I", head, 12, len(raw))
        struct.pack_into("<I", head, 28, len(packed))
        return Sound(self.handle, self.name, bytes(head), raw, bytes(head) + packed)


def read(data, offsets):
    if len(data) < 4 or len(offsets) % 4:
        raise ValueError("Sound bank header")
    index = struct.unpack("<%dI" % (len(offsets) // 4), offsets)
    count = struct.unpack_from("<I", data)[0]
    if not 0 < count <= 4096:
        raise ValueError("Sound count")
    pos, sounds = 4, {}
    for _ in range(count):
        if pos + 32 > len(data):
            raise ValueError("Truncated sound header")
        head = data[pos : pos + 32]
        h, checksum, refs, size, flags, frequency, chars, packed = struct.unpack(
            "<8I", head
        )
        h -= 1
        end = pos + 32 + packed
        if (
            not 0 <= h < len(index)
            or h in sounds
            or index[h] != pos + 260
            or not 0 < chars <= 256
            or not chars * 2 <= size <= 32_000_000
            or not packed
            or end > len(data)
            or flags & 32
        ):
            raise ValueError("Sound boundary, flags or index")
        dec = zlib.decompressobj()
        raw = dec.decompress(data[pos + 32 : end], size + 1)
        if len(raw) != size or not dec.eof or dec.unused_data:
            raise ValueError("Sound compression")
        name = raw[: chars * 2].decode("utf-16le")
        if not name.endswith("\0") or "\0" in name.rstrip("\0"):
            raise ValueError("Sound name terminator")
        sounds[h] = Sound(h, name.rstrip("\0"), head, raw, data[pos:end])
        pos = end
    if pos != len(data) or any(v and h not in sounds for h, v in enumerate(index)):
        raise ValueError("Unconsumed sound bank or orphan index")
    return sounds, len(index)


def write(sounds, slots):
    out = bytearray(struct.pack("<I", len(sounds)))
    index = [0] * slots
    for h, sound in sounds.items():
        if not 0 <= h < slots or sound.handle != h:
            raise ValueError("Sound identity")
        index[h] = len(out) + 260
        out.extend(sound.stored)
    return bytes(out), struct.pack("<%dI" % slots, *index)
