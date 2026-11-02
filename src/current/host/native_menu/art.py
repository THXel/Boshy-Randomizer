"""Original animated cast and paired menu landscapes from the verified local game.

Only decoded presentation assets are cached. This never changes game objects,
collisions, saves or the run's random-number state.
"""

import hashlib
import random
import struct
from functools import lru_cache
from PIL import Image, ImageEnhance, ImageOps
from export_native_run import ORIGINAL
from visuals.scenery_pack import ORIGINAL_SHA
from intro_cast import CAST, read_game, image
from intro_themes import THEMES


@lru_cache(maxsize=1)
def assets():
    objects, raw = read_game(
        ORIGINAL,
        ORIGINAL_SHA,
        extra_images={h for _, bg, tile in THEMES for h in (bg, tile)},
    )
    cast = {}
    for oid, name in CAST.items():
        anims = objects[oid]
        handles = anims.get((1, 0)) or anims.get((0, 0))
        frames = []
        for handle in handles:
            source = image(raw[handle])
            # Anchor every frame at the original hotspot to avoid animation jitter.
            hx, hy = struct.unpack_from("<hh", raw[handle], 20)
            canvas = Image.new("RGBA", (96, 96))
            canvas.alpha_composite(source, (48 - hx, 64 - hy))
            frames.append(canvas)
        cast[name] = tuple(frames)
    themes = []
    for name, bg, tile in THEMES:
        src = image(raw[bg], max_side=2048)
        backdrop = Image.new("RGBA", src.size, "#1c3246")
        backdrop.alpha_composite(src)
        backdrop = ImageOps.fit(backdrop, (672, 496), method=Image.Resampling.NEAREST)
        backdrop = ImageEnhance.Brightness(backdrop).enhance(0.72)
        themes.append((name, backdrop, image(raw[tile])))
    return cast, tuple(themes)


def choose(seed):
    cast, themes = assets()
    rng = random.Random(hashlib.sha256(("menu-art-v2:" + seed).encode()).digest())
    return rng.randrange(len(themes)), tuple(rng.sample(sorted(cast), 3))
