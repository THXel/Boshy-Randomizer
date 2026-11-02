"""Recreate the Fusion audio bank using only audio from the user's original EXE.

The recipe contains headers, names, source handles and hashes, never audio bytes.
This is one component of a future resource-aware patcher, not a whole-game patch.
Exact output hashes reject corrupt recipes and incompatible compression results.
"""

import base64
import hashlib
import struct
import zlib
from music.bank import read, Sound, write
from visuals.scenery_pack import ORIGINAL_SHA


def digest(data):
    return hashlib.sha256(data).hexdigest()


def original_sounds(app):
    if digest(app.data) != ORIGINAL_SHA:
        raise ValueError("Unsupported original game version")
    data = app.payload(0x6668)
    count = struct.unpack_from("<I", data)[0]
    result = {}
    pos = 4
    for _ in range(count):
        handle, _, _, size, flags, _, name_size = struct.unpack_from("<7I", data, pos)
        if flags & 32:
            raw = data[pos + 28 : pos + 28 + size]
            pos += 28 + size
        else:
            packed = struct.unpack_from("<I", data, pos + 28)[0]
            raw = zlib.decompress(data[pos + 32 : pos + 32 + packed])
            pos += 32 + packed
        if len(raw) != size or not 0 < name_size <= size or handle in result:
            raise ValueError("Invalid original audio record")
        result[handle] = raw[name_size:]
    if pos != len(data):
        raise ValueError("Original audio boundary")
    return result


def recipe(original, target):
    source = original_sounds(original)
    by_hash = {digest(audio): handle for handle, audio in source.items()}
    bank_data, offsets = target.payload(0x6668), target.payload(0x5557)
    bank, slots = read(bank_data, offsets)
    rows = []
    for sound in bank.values():
        sha = digest(sound.audio)
        if sha not in by_hash:
            raise ValueError("Target contains audio absent from original")
        rows.append(
            dict(
                target_handle=sound.handle,
                source_handle=by_hash[sha],
                audio_sha256=sha,
                header=base64.b64encode(sound.header).decode("ascii"),
                name=base64.b64encode(sound.raw[: sound.name_bytes]).decode("ascii"),
            )
        )
    result = dict(
        schema=1,
        source_sha256=ORIGINAL_SHA,
        target_sha256=digest(target.data),
        bank_sha256=digest(bank_data),
        offsets_sha256=digest(offsets),
        slots=slots,
        rows=rows,
    )
    # Refuse recipes that cannot reproduce this exact compiled component.
    if restore(original, result) != (bank_data, offsets):
        raise ValueError("Audio recipe differs from target")
    return result


def restore(original, specification, progress=None):
    if (
        specification.get("schema") != 1
        or specification.get("source_sha256") != ORIGINAL_SHA
    ):
        raise ValueError("Unsupported audio recipe")
    slots = specification["slots"]
    if type(slots) is not int or not 0 < slots <= 4096:
        raise ValueError("Invalid audio slot count")
    rows = specification["rows"]
    if not 0 < len(rows) <= slots:
        raise ValueError("Invalid audio recipe count")
    source = original_sounds(original)
    sounds = {}
    if progress:
        progress("audio", 0, len(rows))
    for index, row in enumerate(rows, 1):
        h = row["target_handle"]
        if type(h) is not int or not 0 <= h < slots or h in sounds:
            raise ValueError("Duplicate or invalid target audio handle")
        audio = source[row["source_handle"]]
        if digest(audio) != row["audio_sha256"]:
            raise ValueError("Source audio checksum")
        head = base64.b64decode(row["header"], validate=True)
        name = base64.b64decode(row["name"], validate=True)
        if len(head) != 32 or not 2 <= len(name) <= 512 or len(name) % 2:
            raise ValueError("Audio recipe header")
        handle, _, _, size, flags, _, chars, packed_size = struct.unpack("<8I", head)
        raw = name + audio
        if handle != h + 1 or chars * 2 != len(name) or size != len(raw) or flags & 32:
            raise ValueError("Audio recipe metadata")
        packed = zlib.compress(raw, 9)
        if len(packed) != packed_size:
            raise ValueError("Incompatible audio compression")
        sounds[h] = Sound(
            h, name.decode("utf-16le").rstrip("\0"), head, raw, head + packed
        )
        if progress:
            progress("audio", index, len(rows))
    bank, offsets = write(sounds, slots)
    if (
        digest(bank) != specification["bank_sha256"]
        or digest(offsets) != specification["offsets_sha256"]
    ):
        raise ValueError("Reconstructed audio bank checksum")
    return bank, offsets
