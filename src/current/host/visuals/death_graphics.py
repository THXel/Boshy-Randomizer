"""Lossless render preparation for decorative death sprites only."""
import struct
from PIL import Image
from visuals.embedded_blood import raw_image


def trim(image, origin):
    box = image.getchannel("A").getbbox()
    if box is None:
        return Image.new("RGBA", (1, 1)), (0, 0)
    left, top, _, _ = box
    return image.crop(box), (origin[0] - left, origin[1] - top)


def encode(image, origin):
    """Opaque screens need no alpha blending. Never change visible pixels."""
    raw = raw_image(image, origin)
    if image.getchannel("A").getextrema() != (255, 255):
        return raw
    colours = set(image.convert("RGB").getdata())
    # Find an unused colour key: an opaque black screen must stay black.
    key = next(n for n in range(0x1000000) if (n & 255, (n >> 8) & 255, n >> 16) not in colours)
    size = ((image.width + 1) // 2 * 2 * 3) * image.height
    header = bytearray(raw[:32])
    header[17] = 0
    struct.pack_into("<I", header, 8, size)
    struct.pack_into("<I", header, 28, key)
    return bytes(header) + raw[32:32+size]
