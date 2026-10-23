"""Convert this freestanding i386 object's ELF sections/symbols/relocations to COFF.
Only absolute and PC-relative relocations are accepted; no silent translation.
"""

import struct
from pathlib import Path


def convert(source, target):
    b = Path(source).read_bytes()
    assert b[:7] == b'\x7fELF\x01\x01\x01'
    shoff = struct.unpack_from('<I', b, 32)[0]
    ents, n, strings = struct.unpack_from('<3H', b, 46)
    sections = [struct.unpack_from('<10I', b, shoff + i * ents) for i in range(n)]
    names = b[sections[strings][4] : sections[strings][4] + sections[strings][5]]

    def string(data, off):
        return data[off : data.index(0, off)].decode()

    sn = lambda i: string(names, sections[i][0])
    selected = [i for i, s in enumerate(sections) if s[2] & 2 and s[1] in (1, 8)]
    secmap = {s: i + 1 for i, s in enumerate(selected)}
    syidx = next(i for i, s in enumerate(sections) if s[1] == 2)
    sy = sections[syidx]
    strs = sections[sy[6]]
    strs = b[strs[4] : strs[4] + strs[5]]
    symbols = []
    mapping = {}
    st = bytearray(b'\0' * 4)

    def long(s):
        o = len(st)
        st.extend(s.encode() + b'\0')
        return o

    def name(s, section=False):
        raw = s.encode()
        if len(raw) <= 8:
            return raw.ljust(8, b'\0')
        o = long(s)
        return (
            ('/' + str(o)).encode().ljust(8, b'\0')
            if section
            else struct.pack('<II', 0, o)
        )

    for i, off in enumerate(range(sy[4], sy[4] + sy[5], 16)):
        no, value, size, info, other, idx = struct.unpack_from('<IIIBBH', b, off)
        if not i:
            continue
        if idx not in secmap:
            continue
        nam = string(strs, no) if no else 'section_' + sn(idx)
        mapping[i] = len(symbols)
        symbols.append(
            struct.pack(
                '<8sIhHBB',
                name('_' + nam),
                value,
                secmap[idx],
                0,
                2 if info >> 4 else 3,
                0,
            )
        )
    data = bytearray()
    headers = []
    base = 20 + 40 * len(selected)
    for idx in selected:
        s = sections[idx]
        raw = bytearray(b[s[4] : s[4] + s[5]]) if s[1] != 8 else bytearray()
        rels = []
        for r in sections:
            if r[1] != 9 or r[7] != idx:
                continue
            for off in range(r[4], r[4] + r[5], 8):
                addr, info = struct.unpack_from('<II', b, off)
                typ = info & 255
                symbol = info >> 8
                assert typ in (1, 2, 4) and symbol in mapping, (sn(idx), typ, symbol)
                if typ in (2, 4):
                    struct.pack_into(
                        '<I',
                        raw,
                        addr,
                        (struct.unpack_from('<I', raw, addr)[0] + 4) & 0xFFFFFFFF,
                    )
                rels.append(
                    struct.pack('<IIH', addr, mapping[symbol], 6 if typ == 1 else 20)
                )
        rp = base + len(data) if raw else 0
        data.extend(raw)
        rr = base + len(data) if rels else 0
        data.extend(b''.join(rels))
        flags = (
            0x60000020
            if s[2] & 4
            else 0xC0000080 if s[1] == 8 else 0xC0000040 if s[2] & 1 else 0x40000040
        ) | 0x00300000
        headers.append(
            struct.pack(
                '<8s6I2HI',
                name(sn(idx), True),
                0,
                0,
                s[5],
                rp,
                rr,
                0,
                len(rels),
                0,
                flags,
            )
        )
    struct.pack_into('<I', st, 0, len(st))
    hdr = struct.pack(
        '<HHIIIHH', 0x14C, len(headers), 0, base + len(data), len(symbols), 0, 0
    )
    Path(target).write_bytes(hdr + b''.join(headers) + data + b''.join(symbols) + st)
