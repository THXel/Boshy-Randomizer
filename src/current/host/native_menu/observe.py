"""Read native title objects using the actual frame capacity; never write memory."""

import struct


def objects(reader, types=(2,)):
    run = reader.u32(reader.base + 0xA35DC)
    capacity = reader.u32(run + 0x40)
    if not 1 <= capacity <= 20000:
        raise RuntimeError("Title frame object capacity is not ready")
    table = reader.u32(run + 0x1278)
    data = b"".join(
        reader.read(table + i, min(256, capacity * 8 - i))
        for i in range(0, capacity * 8, 256)
    )
    result = []
    for slot in range(capacity):
        ptr = struct.unpack_from("<I", data, slot * 8)[0]
        if ptr < 65536:
            continue
        raw = reader.read(ptr, 160)
        if (
            struct.unpack_from("<I", raw, 8)[0] != run
            or struct.unpack_from("<H", raw, 0)[0] != slot
            or struct.unpack_from("<H", raw, 24)[0] not in types
            or struct.unpack_from("<H", raw, 124)[0] & 1
        ):
            continue
        oi = struct.unpack_from("<H", raw, 18)[0]
        oip = struct.unpack_from("<I", raw, 28)[0]
        name = (
            reader.read(oip + 90, 64)
            .decode("utf-16le", errors="replace")
            .split("\0")[0]
        )
        result.append(
            dict(
                ptr=ptr,
                slot=slot,
                rel=struct.unpack_from("<I", raw, 128)[0],
                w=struct.unpack_from("<i", raw, 96)[0],
                h=struct.unpack_from("<i", raw, 100)[0],
                oi=oi,
                name=name,
                x=struct.unpack_from("<i", raw, 76)[0],
                y=struct.unpack_from("<i", raw, 84)[0],
            )
        )
    return result


def values(reader, obj, n=5):
    p = reader.u32(obj["ptr"] + obj["rel"])
    data = reader.read(p, n * 16)
    return [
        struct.unpack_from(
            "<i" if struct.unpack_from("<I", data, i * 16)[0] == 0 else "<d",
            data,
            i * 16 + 8,
        )[0]
        for i in range(n)
    ]
