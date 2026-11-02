"""Paired intro textures from user-owned game assets. No gameplay seed dependency."""

import json
import logging
import random
import struct
from pathlib import Path
from PIL import Image, ImageChops, ImageEnhance, ImageOps
from intro_cast import image

# Audited image IDs from the checksum-verified original game.
THEMES = (
    ('Green Greens', 4017, 4336),
    ('Wario Skyline', 3205, 883),
    ('Ninja Gaiden', 3800, 3492),
    ('Desert Sunset', 998, 3706),
)
# oi, direction, original image. Types and layouts are independently checked in C.
TARGETS = (
    (30, 0, 88),
    (38, 0, 19),
    (38, 8, 72),
    (38, 16, 80),
    (38, 24, 85),
    (22, 0, 8),
    (24, 0, 76),
    (32, 0, 95),
    (33, 0, 93),
    (34, 0, 94),
    (35, 0, 6),
    (36, 0, 10),
    (37, 0, 12),
)
IMAGE_IDS = {h for _, _, h in TARGETS} | {
    h for _, bg, tile in THEMES for h in (bg, tile)
}


def choose(previous, rng=None):
    return (rng or random.SystemRandom()).choice(
        [i for i in range(len(THEMES)) if i != previous]
    )


def floor(original, tile):
    """Preserve every alpha pixel: visible outline and collision mask stay identical."""
    original = original.convert('RGBA')
    tile = tile.convert('RGB')
    texture = Image.new('RGB', original.size)
    for y in range(0, original.height, tile.height):
        for x in range(0, original.width, tile.width):
            texture.paste(tile, (x, y))
    # Keep the old edge highlights and joints lightly visible under the new material.
    shading = ImageOps.grayscale(original).point(lambda n: 96 + n * 159 // 255)
    shaded = ImageChops.multiply(texture, Image.merge('RGB', (shading,) * 3))
    shaded.putalpha(original.getchannel('A'))
    return shaded


def backdrop(source, size):
    # Fill the original image extent; dim the scene so white menu lettering reads well.
    canvas = Image.new('RGB', source.size, '#101825')
    canvas.paste(source, (0, 0), source.getchannel('A'))
    canvas = ImageOps.fit(canvas, size, method=Image.Resampling.NEAREST)
    return ImageEnhance.Brightness(canvas).enhance(0.58).convert('RGBA')


def make_plan(folder, images, theme):
    if type(theme) is not int or not 0 <= theme < len(THEMES):
        raise ValueError('Unknown intro theme')
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'effects.bin').unlink(missing_ok=True)
    _, bg, tile = THEMES[theme]
    background = image(images[bg], max_side=2048)
    material = image(images[tile])
    records = []
    for index, (oi, direction, handle) in enumerate(TARGETS):
        raw = images[handle]
        original = image(raw, max_side=2048)
        w, h = original.size
        hx, hy = struct.unpack_from('<hh', raw, 20)
        result = backdrop(background, (w, h)) if oi == 30 else floor(original, material)
        if oi == 30:
            from intro_atmosphere import prepare as prepare_atmosphere

            result = prepare_atmosphere(folder, result, theme)
        result.save(folder / f'{index:02d}.png')
        original.save(folder / f'o{index:02d}.png')
        path = ('..\\menu-runtime\\theme\\' + f'{index:02d}.png').encode('ascii')
        records.append(struct.pack('<4I2i96s', oi, direction, w, h, hx, hy, path))
    return b'BRT1' + struct.pack('<II', len(records), theme) + b''.join(records)


def prepare(base, images, *, rng=None):
    from native_session import atomic

    root = Path(base) / 'menu-runtime'
    plan = root / 'theme.bin'
    try:
        try:
            previous = json.loads(
                (root / 'theme-last.json').read_text(encoding='utf-8')
            ).get('theme')
        except (OSError, ValueError, AttributeError):
            previous = None
        theme = choose(previous, rng)
        payload = make_plan(root / 'theme', images, theme)
        atomic(plan, payload)
        atomic(
            root / 'theme-last.json',
            json.dumps(
                {'version': 1, 'theme': theme, 'name': THEMES[theme][0]}
            ).encode(),
        )
        return theme
    except Exception:
        plan.unlink(missing_ok=True)
        (root / 'theme/effects.bin').unlink(missing_ok=True)
        logging.exception('Cosmetic intro theme unavailable; keeping original scenery')
        return None
