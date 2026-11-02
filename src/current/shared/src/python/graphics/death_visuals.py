"""Validated, locally supplied death-screen animation and blood sprites.

Cosmetic installation preference, independent of saved seeds. Pack graphics stay
outside the game-free distribution, alongside the user's soundpack audio.
"""

import hashlib
import json
import struct
from pathlib import Path
from PIL import Image
from native_session import atomic, write_json

MAGIC = b'BRD1'
MAX_SCREEN = 96
MAX_BLOOD = 32


def prepare(base, pack, data=None):
    base = Path(base)
    folder = base / 'menu-runtime'
    folder.mkdir(exist_ok=True)
    plan = folder / 'deathpack.bin'
    # Invalidate first. A failed replacement cannot leave a previous pack active.
    atomic(plan, struct.pack('<4s9I32s', MAGIC, *([0] * 9), b''))
    write_json(folder / 'deathpack-map.json', dict(pack='original', active=False))
    visual = (data or {}).get('death_visuals')
    if pack == 'original' or not visual:
        return False
    if visual.get('version') != 1:
        raise ValueError('Unsupported death visual manifest')
    root = (base / 'soundpacks' / pack).resolve()
    rows = []
    groups = []
    durations = []
    for role, limit in [('screen', MAX_SCREEN), ('blood', MAX_BLOOD)]:
        group = visual[role]
        frames = group['frames']
        fps = group['fps']
        loop = group.get('loop', len(frames) - 1)
        if not isinstance(frames, list) or not 1 <= len(frames) <= limit:
            raise ValueError('Death animation frame count')
        if (
            type(fps) != int
            or not 1 <= fps <= 50
            or type(loop) != int
            or not 0 <= loop < len(frames)
        ):
            raise ValueError('Death animation timing')
        if role == 'screen' and 'ticks' in group:
            durations = group['ticks']
            if (
                not isinstance(durations, list)
                or len(durations) != len(frames)
                or any(type(t) != int or not 1 <= t <= 500 for t in durations)
                or sum(durations) > 3000
            ):
                raise ValueError('Death screen timeline')
        groups.append(
            (
                len(frames),
                (
                    0
                    if (role == 'screen' and durations)
                    or (role == 'blood' and group.get('random_static') is True)
                    else fps
                ),
                loop,
            )
        )
        for i, row in enumerate(frames):
            rel = Path(row['file'])
            source = root / rel
            if (
                rel.is_absolute()
                or '..' in rel.parts
                or source.is_symlink()
                or not source.resolve().is_relative_to(root)
            ):
                raise ValueError('Death image path')
            raw = source.read_bytes()
            if len(raw) > 2_000_000 or hashlib.sha256(raw).hexdigest() != row['sha256']:
                raise ValueError('Death image checksum')
            with Image.open(source) as image:
                expected = (
                    (640, 480) if role == 'screen' else tuple(visual['blood']['size'])
                )
                if (
                    image.format != 'PNG'
                    or image.size != expected
                    or not all(1 <= v <= 640 for v in image.size)
                ):
                    raise ValueError('Death image dimensions')
                image.verify()
            rows.append((role, i, raw))
    width, height = visual['blood']['size']
    hx, hy = visual['blood']['origin']
    if any(type(v) != int for v in (width, height, hx, hy)) or not (
        1 <= width <= 64 and 1 <= height <= 64 and 0 <= hx < width and 0 <= hy < height
    ):
        raise ValueError('Blood sprite geometry')
    identity = hashlib.sha256(json.dumps(visual, sort_keys=True).encode()).hexdigest()[
        :32
    ]
    cache = folder / 'deathpacks' / identity
    for role, i, raw in rows:
        dest = cache / role / f'{i:03d}.png'
        dest.parent.mkdir(parents=True, exist_ok=True)
        if not dest.exists() or dest.read_bytes() != raw:
            atomic(dest, raw)
    # Immutable files are all in place before the plan becomes visible.
    screen, blood = groups
    header = struct.pack(
        '<4s9I32s',
        MAGIC,
        *screen,
        *blood,
        width,
        height,
        hx | (hy << 16),
        identity.encode('ascii'),
    ) + struct.pack('<' + 'H' * len(durations), *durations)
    atomic(plan, header)
    write_json(
        folder / 'deathpack-map.json',
        dict(
            pack=pack,
            active=True,
            identity=identity,
            screen_frames=screen[0],
            blood_frames=blood[0],
        ),
    )
    return True
