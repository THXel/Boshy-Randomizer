"""Read the build stamp from the compiled title's native event chunk.

Storage format cross-check: reference-nebula/Nebula.Core/Memory/Decryption.cs.
No executable changes, process access or runtime injection are involved.
"""

import struct
import zlib


def title_events(app):
    from klikback.core.mmf2.chunk_census import walk_chunks

    frame = app.by_id[0x3333][1].payload
    chunks, _, _ = walk_chunks(frame, 0, len(frame), keep_payload=True)
    chunk = next(c for c in chunks if c.id == 0x333D)
    if chunk.payload is not None:
        return chunk.payload
    if chunk.flags != 3 or app.pbuild <= 285:
        raise ValueError("Unsupported compiled event storage")
    material = bytes(
        b for cid in (0x2224, 0x223B, 0x222E) for b in (app.payload(cid) or b"") if b
    )
    key = bytearray(material[:128].ljust(256, b"\0"))
    if len(material) < 255:
        key[len(material) + 1] = sum(material) * 2 & 255
    table, index, pos = list(range(256)), 0, 0
    for i in range(256):
        if key[pos] == 0:
            pos = 0
        index = (index + key[pos] + table[i]) & 255
        pos = (pos + 1) & 255
        table[index], table[i] = table[i], table[index]
    raw = frame[chunk.offset + 8 : chunk.offset + 8 + chunk.size]
    size = struct.unpack_from("<I", raw)[0]
    if not 0 < size < 8_000_000:
        raise ValueError("Compiled event size")
    encrypted = bytearray(raw[4:])
    encrypted[0] ^= (chunk.id & 255) ^ (chunk.id >> 8)
    i = j = 0
    for offset in range(len(encrypted)):
        i = (i + 1) & 255
        j = (j + table[i]) & 255
        table[i], table[j] = table[j], table[i]
        encrypted[offset] ^= table[(table[i] + table[j]) & 255]
    packed = struct.unpack_from("<I", encrypted)[0]
    if packed != len(encrypted) - 4:
        raise ValueError("Compiled event compression size")
    decoder = zlib.decompressobj()
    result = decoder.decompress(encrypted[4:], size + 1)
    if len(result) != size or not decoder.eof or decoder.unused_data:
        raise ValueError("Compiled event data differs")
    return result
