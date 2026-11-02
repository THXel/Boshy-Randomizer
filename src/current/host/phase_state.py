"""Temporary phase fixtures, restricted by the bridge to BoshySceneTests."""

import struct, hashlib
from pathlib import Path
from phase_inspect import Bridge, MemoryReadUnavailable


class RuntimeNotReady(RuntimeError):
    """The old frame has unloaded and the next frame is not ready to inspect."""


class State:
    def __init__(self, case):
        self.b = Bridge(case)
        self.case = case
        self.unicode = case.startswith("rebuilt")
        self.names = {}
        self.writes = []
        path = (
            Path("/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshySceneTests")
            / case
            / "Boshy.exe"
        )
        with path.open("rb") as f:
            digest = hashlib.file_digest(f, "sha256").hexdigest()
        profiles = {
            "b13b8c524871f35f919c22b7b48a39c86312cc928e2b87a7e474858a939ff046": 0xA35DC,
            "7a13c810bb928a598858799889d8524bbb961d3e9c7903ba99e1655e7811e082": 0xA35DC,
            "d09c9569d909bde1496161b9891f7a7f96c6b15d6bcfd8ae7d54dace0fe43185": 0xA35DC,
            "f568f367852d0b5bb9c2beb985c0d3c9d4aa02456635ff55945d91d9b31059d2": 0xA35DC,
            "e74eeec18771fb25d70040ac12706bbaff921ec924e10956d6d7fead233c96bb": 0xA35DC,
            "9ba1e7a8d7c8049de2c9d17e0505c34e37b5e54303baf05db942183731cc1644": 0xA35DC,
            "c5654a9ead809c0fb0fa695d32466b6c1f86fc390557e849e4aa3337e1526381": 0xA35DC,
            "93c2eb281c853ed52abf98891c2931ea881f04ff114a60e01c57f275dc122be5": 0xA35DC,
            "c146baa663fc0480573e8137e4057dfdd7548ab03b6dd5ce957665de9cea089c": 0xA35DC,
            "0fb7261949c37e49daf5cf2845204842eaf7157570bb3044dff825864b604977": 0xA35DC,
            "712a0fe5a3f0689dedad523b488ea701ea3818ac64a616d6da068dacd939fd15": 0xA35DC,
            "b972d7d361982a4c88c319ea72093194f45a36cc447905d5ace1d6c266ffa806": 0xA35DC,
            "ea52053ecefb6b58cfe1738abe3db7627fc2a17dc0aac2b20cc6c50b232a5354": 0xA35DC,
            "6c14c7e77240b5ea2923d4be067922d6613f8d4bdb1ff3d193db76adf7f37727": 0xA35DC,
            "dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806": 0x59A9C,
            "d75e8f45c2cc4512a6f6f4d3cf32905dc3b5b118a06754b65158ff3bdec73125": 0xA35DC,
        }
        assert (
            digest in profiles
        ), "Unsupported build: verify runtime layout before using fixtures"
        self.run_globals = [self.b.ready["base"] + profiles[digest]]
        self.refresh()
        assert self.b.u32(self.run + 0x40) == 20000

    def close(self):
        self.b.close()

    def cas(self, addr, old, new, reason):
        assert self.b.cmd(f"cas32 {addr:x} {old&0xffffffff:x} {new&0xffffffff:x}")[
            "written"
        ], reason
        self.writes.append(dict(address=addr, old=old, new=new, reason=reason))

    def refresh(self):
        if not self.unicode:
            self.run = self.b.u32(self.b.ready["base"] + 0x59A9C)
        else:
            candidates = {self.b.u32(addr) for addr in self.run_globals}
            valid = []
            for run in candidates:
                try:
                    if run > 65536 and self.b.u32(run + 0x40) == 20000:
                        valid.append(run)
                except MemoryReadUnavailable:
                    pass
            if not valid:
                raise RuntimeNotReady("Frame runtime is between loads")
            assert len(valid) == 1, ("Ambiguous current runtime", valid)
            self.run = valid[0]

    def frame_name(self):
        """Read CRunFrame::m_name through the hash-verified RunHeader layout."""
        self.refresh()
        frame = self.b.u32(self.run + 0x1C)
        if frame < 65536:
            raise RuntimeNotReady("Current frame has not been loaded")
        width, height = struct.unpack("<ii", self.b.read(frame, 8))
        assert 0 < width <= 100000 and 0 < height <= 100000
        name = self.b.u32(frame + 16)
        assert name >= 65536
        raw = self.b.read(name, 128)
        if self.unicode:
            end = next(i for i in range(0, len(raw), 2) if raw[i : i + 2] == b"\0\0")
            return raw[:end].decode("utf-16le")
        return raw.split(b"\0", 1)[0].decode("latin1")

    def objects(self):
        self.refresh()
        # OI addresses can be reused by another frame; cache within one snapshot only.
        self.names = {}
        b = self.b
        table = b.u32(self.run + 0x1278)
        n = b.u32(self.run + 0x40)
        assert n == 20000
        data = b"".join(
            b.read(table + i, min(64000, n * 8 - i)) for i in range(0, n * 8, 64000)
        )
        result = []
        for slot in range(n):
            ptr = struct.unpack_from("<I", data, slot * 8)[0]
            if ptr < 65536:
                continue
            raw = b.read(ptr, 160)
            if (
                struct.unpack_from("<I", raw, 8)[0] != self.run
                or struct.unpack_from("<H", raw, 0)[0] != slot
            ):
                continue
            typ = struct.unpack_from("<H", raw, 24)[0]
            if typ != 2 or struct.unpack_from("<H", raw, 124)[0] & 1:
                continue
            oi = struct.unpack_from("<H", raw, 18)[0]
            oip = struct.unpack_from("<I", raw, 28)[0]
            if oip not in self.names:
                nam = b.read(oip + 90, 64)
                self.names[oip] = nam.decode(
                    "utf-16le" if self.unicode else "latin1", errors="replace"
                ).split("\0")[0]
            rel = struct.unpack_from("<I", raw, 128)[0]
            result.append(
                dict(
                    ptr=ptr,
                    slot=slot,
                    oi=oi,
                    name=self.names[oip],
                    x=struct.unpack_from("<i", raw, 76)[0],
                    y=struct.unpack_from("<i", raw, 84)[0],
                    w=struct.unpack_from("<i", raw, 96)[0],
                    h=struct.unpack_from("<i", raw, 100)[0],
                    rel=rel,
                )
            )
        return result

    def values(self, o, n=5):
        ptr = self.b.u32(o["ptr"] + o["rel"])
        if ptr < 65536:
            return []
        data = self.b.read(ptr, n * 16)
        return [
            struct.unpack_from(
                "<i" if struct.unpack_from("<I", data, i * 16)[0] == 0 else "<d",
                data,
                i * 16 + 8,
            )[0]
            for i in range(n)
        ]

    def set_value(self, o, index, value):
        addr = self.b.u32(o["ptr"] + o["rel"]) + index * 16
        assert self.b.u32(addr) == 0
        old = self.b.u32(addr + 8)
        self.cas(addr + 8, old, value, f'{o["name"]} alterable {index}')

    def position(self, o, x, y):
        for offset, val in [(76, x), (84, y)]:
            for attempt in range(4):
                # Moving shots may advance between read and CAS. Never retry a
                # recycled slot or an object belonging to another frame.
                header = self.b.read(o["ptr"], 32)
                assert struct.unpack_from("<H", header, 0)[0] == o["slot"]
                assert struct.unpack_from("<I", header, 8)[0] == self.run
                assert struct.unpack_from("<H", header, 18)[0] == o["oi"]
                assert struct.unpack_from("<H", header, 24)[0] == 2
                addr = o["ptr"] + offset
                old = self.b.u32(addr)
                result = self.b.cmd(
                    f"cas32 {addr:x} {old & 0xffffffff:x} {val & 0xffffffff:x}"
                )
                if result["written"]:
                    self.writes.append(
                        dict(
                            address=addr,
                            old=old,
                            new=val,
                            reason=f"test {o['name']} position",
                        )
                    )
                    break
            else:
                raise RuntimeError("Object kept moving during bounded position fixture")

    def protect(self):
        self.refresh()
        bank = self.b.u32(self.run + 0x88)
        data = b""
        pos = 0
        patched = []
        already = 0
        head = 16 if self.unicode else 14
        while pos < 2000000:
            while len(data) < pos + 2:
                data += self.b.read(bank + len(data), 64000)
            size = -struct.unpack_from("<h", data, pos)[0]
            if not 14 <= size < 32768:
                break
            while len(data) < pos + size:
                data += self.b.read(bank + len(data), 64000)
            row = data[pos : pos + size]
            off = head
            try:
                for i in range(row[2] + row[3]):
                    n, kind, code = struct.unpack_from("<Hhh", row, off)
                    if n < 14 or off + n > size:
                        raise ValueError("event layout")
                    raw = row[off : off + n]
                    pattern = "Die\0".encode("utf-16le" if self.unicode else "latin1")
                    if (
                        i >= row[2]
                        and kind == -1
                        and code == 14
                        and raw[12] == 2
                        and n == (58 if self.unicode else 54)
                        and raw[26 : 26 + len(pattern)].lower() == pattern.lower()
                    ):
                        # Unicode runtime caches fastloop indices; changing the visible name
                        # does not disable the call. Set its verified literal repeat count to 0.
                        count_offset = n - 8
                        assert raw[count_offset - 6 : count_offset] == bytes.fromhex(
                            "ffff00000a00"
                        )
                        old = int.from_bytes(
                            raw[count_offset : count_offset + 4], "little"
                        )
                        assert old in (0, 1), ("Unexpected loop count", old)
                        if old == 0:
                            already += 1
                        else:
                            addr = bank + pos + off + count_offset
                            self.cas(
                                addr,
                                old,
                                0,
                                "temporary zero-count Die fastloop for visual fixture",
                            )
                            patched.append(pos + off)
                    off += n
                assert off == size
            except (ValueError, struct.error, AssertionError):
                raise RuntimeError(
                    f"Invalid runtime event layout at {pos}, head={head}"
                )
            pos += size
        assert patched or already, ("No death calls patched", pos)
        return {
            "bank": bank,
            "event_bytes": pos,
            "patched_calls": patched,
            "already_patched": already,
        }
