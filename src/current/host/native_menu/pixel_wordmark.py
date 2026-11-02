"""Native pixel lettering for the intro, following its original 3px letter grid.

Glyphs are vector-like cell masks, rendered straight into the Fusion image bank.
No platform font, external image file or runtime font installation is required.
"""

import struct

# Seven cell rows: the original lower-case baseline is row 4; g/y descend.
GLYPHS = {
    " ": ("..",) * 7,
    ".": (".", ".", ".", ".", "#", ".", "."),
    "S": (".###", "#...", ".##.", "...#", "###.", "....", "...."),
    "O": (".##.", "#..#", "#..#", "#..#", ".##.", "....", "...."),
    "M": ("#...#", "##.##", "#.#.#", "#...#", "#...#", ".....", "....."),
    "T": ("###", ".#.", ".#.", ".#.", ".#.", "...", "..."),
    "H": ("#..#", "#..#", "####", "#..#", "#..#", "....", "...."),
    "X": ("#..#", "#..#", ".##.", "#..#", "#..#", "....", "...."),
    "a": ("....", ".##.", "...#", ".###", ".###", "....", "...."),
    "b": ("#...", "#...", "###.", "#..#", "###.", "....", "...."),
    "c": ("....", ".###", "#...", "#...", ".###", "....", "...."),
    "d": ("...#", "...#", ".###", "#..#", ".###", "....", "...."),
    "e": ("....", ".##.", "#.##", "##..", ".###", "....", "...."),
    "f": (".##", ".#.", "###", ".#.", ".#.", "...", "..."),
    "g": ("....", ".###", "#..#", "#..#", ".###", "...#", ".##."),
    "i": ("#", ".", "#", "#", "#", ".", "."),
    "l": (".", "#", "#", "#", "#", ".", "."),
    "m": (".....", "##.#.", "#.#.#", "#.#.#", "#.#.#", ".....", "....."),
    "n": ("....", "###.", "#..#", "#..#", "#..#", "....", "...."),
    "o": ("....", ".##.", "#..#", "#..#", ".##.", "....", "...."),
    "r": ("...", "#.#", "##.", "#..", "#..", "...", "..."),
    "s": ("...", ".##", "##.", "..#", "##.", "...", "..."),
    "t": (".#.", "###", ".#.", ".#.", "..#", "...", "..."),
    "y": ("....", "#..#", "#..#", "#..#", ".###", "...#", ".##."),
}
LINES = (
    ("grynsoft.com", 3, 0, 255),
    ("Original by Solgryn", 2, 27, 255),
    ("Modded by THXel", 2, 49, 153),
)
WIDTH, HEIGHT = 208, 63
IMAGE_HANDLES = frozenset((5979, 5980, 5981))


def cells(text):
    result = []
    x = 0
    for ch in text:
        rows = GLYPHS[ch]
        for y, row in enumerate(rows):
            result.extend((x + i, y) for i, p in enumerate(row) if p == "#")
        x += len(rows[0]) + 1
    return x - 1, result


def rectangles():
    for text, scale, y, shade in LINES:
        width, pixels = cells(text)
        left = (WIDTH - width * scale) // 2
        assert left >= 0
        for x, row in pixels:
            yield left + x * scale, y + row * scale, scale, shade


def raw_image(template, *, cyan=False):
    """Use original colour-key format; centre hotspot follows native animation."""
    stride = (WIDTH + 1) // 2 * 2 * 3
    pixels = bytearray(stride * HEIGHT)
    for x, y, size, shade in rectangles():
        for dy in range(size):
            for dx in range(size):
                v = (
                    shade
                    if not cyan
                    else max(
                        35, shade - (85 if ((x + dx) // 9 + (y + dy) // 9) % 2 else 0)
                    )
                )
                rgb = bytes((v, v, 0)) if cyan else bytes((v, v, v))  # native BGR
                off = (y + dy) * stride + (x + dx) * 3
                pixels[off : off + 3] = rgb
    head = bytearray(template[:32])
    struct.pack_into("<I", head, 0, 0xFFFFFFFF)
    struct.pack_into("<I", head, 8, len(pixels))
    struct.pack_into("<HH", head, 12, WIDTH, HEIGHT)
    head[16:18] = bytes((4, 0))
    struct.pack_into("<hhhhI", head, 20, WIDTH // 2, 0, 0, 0, 0)
    return bytes(head) + pixels


def update_bank(images):
    images = dict(images)
    for handle in IMAGE_HANDLES:
        images[handle] = raw_image(images[handle], cyan=handle == 5981)
    return images
