"""Common bounded frame decoding for Linux/Wine and native Windows readers."""

import json
import struct
from app_paths import LAB

FRAME_NAMES = set(
    json.loads(
        (LAB / "transition/frame_names.json").read_text(encoding="utf-8")
    ).values()
)


class FrameObserver:
    def u32(self, a):
        return struct.unpack("<I", self.read(a, 4))[0]

    def frame(self):
        run = self.u32(self.base + 0xA35DC)
        if run < 65536:
            raise RuntimeError("Frame loading")
        frame = self.u32(run + 0x1C)
        if frame < 65536:
            raise RuntimeError("Frame loading")
        raw = self.read(self.u32(frame + 16), 128)
        end = next(i for i in range(0, len(raw), 2) if raw[i : i + 2] == b"\0\0")
        name = raw[:end].decode("utf-16le")
        if name not in FRAME_NAMES:
            raise RuntimeError("Unknown frame name: " + name)
        return name
