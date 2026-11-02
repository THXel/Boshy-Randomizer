"""Original intro choreography with independent, nonrepeating cosmetic casts."""

import json
import random
import struct
from pathlib import Path
from functools import lru_cache
from export_native_run import ORIGINAL
from visuals.scenery_pack import ORIGINAL_SHA
from intro_cast import read_game, choose, make_plan, CAST
from intro_themes import IMAGE_IDS, TARGETS, THEMES, floor, backdrop
from intro_cast import image

VARIANTS = 12


@lru_cache(maxsize=1)
def assets():
    return read_game(ORIGINAL, ORIGINAL_SHA, extra_images=IMAGE_IDS)


def make_theme(folder, images, theme):
    folder.mkdir(parents=True, exist_ok=True)
    _, bg, tile = THEMES[theme]
    background = image(images[bg], max_side=2048)
    material = image(images[tile])
    for index, (oi, direction, handle) in enumerate(TARGETS):
        original = image(images[handle], max_side=2048)
        result = (
            backdrop(background, original.size)
            if oi == 30
            else floor(original, material)
        )
        result.save(folder / f"{index:02d}.png")


def prepare(folder):
    root = Path(folder) / "classic-intro"
    if (root / "manifest.json").exists():
        return json.loads((root / "manifest.json").read_text())
    objects, images = assets()
    rng = random.SystemRandom()
    previous = None
    casts = []
    themes = rng.sample(range(4), 4)
    layouts = None
    for variant in range(VARIANTS):
        selected = choose(previous, rng)
        # Original intro transitions can re-enter Title during choreography.
        # Keep each role unique across the deck, even if entries are skipped.
        while any(any(old[i] == selected[i] for old in casts) for i in range(3)):
            selected = choose(previous, rng)
        casts.append(selected)
        blob = make_plan(root / str(variant), objects, images, selected)
        records = [struct.unpack_from("<6I2i96s", blob, 8 + i * 128) for i in range(32)]
        layout = [
            dict(
                oi=r[0],
                animation=r[1],
                direction=r[2],
                frame=r[3],
                width=r[4],
                height=r[5],
                hx=r[6],
                hy=r[7],
            )
            for r in records
        ]
        if layouts is not None and layouts != layout:
            raise ValueError("Intro animation geometry changed")
        layouts = layout
        if variant < 4:
            make_theme(root / "theme" / str(variant), images, themes[variant])
        else:
            import shutil

            shutil.copytree(
                root / "theme" / str(variant % 4),
                root / "theme" / str(variant),
                dirs_exist_ok=True,
            )
        previous = selected
    report = dict(
        schema=1,
        independent_of_run_seed=True,
        variants=VARIANTS,
        casts=casts,
        themes=themes,
        names=[[CAST[n] for n in c] for c in casts],
        layout=layouts,
    )
    (root / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def layout():
    objects, images = assets()
    result = []
    for oi in (18, 21, 23):
        for (animation, direction), handles in objects[oi].items():
            for frame, handle in enumerate(handles):
                hx, hy = struct.unpack_from("<hh", images[handle], 20)
                result.append((oi, animation, direction, frame, hx, hy))
    assert len(result) == 32
    return result
