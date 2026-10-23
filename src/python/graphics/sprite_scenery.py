"""Seeded, reviewed collision-free scenery. Extracted from the user's game only."""

import hashlib
import json
import logging
import struct
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance
from intro_cast import read_game, image, chunks

MAGIC = b'BRV1'
# Full landscape artwork, excluding menus, text, attacks and interactable sprites.
SOURCES = (4017, 3205, 3800, 998, 3201, 3203, 3796, 3877, 2702, 4283, 4286)


def catalogue():
    return json.loads(
        Path(__file__)
        .with_name('sprite_scenery_catalogue.json')
        .read_text(encoding='utf-8')
    )['objects']


def mapping(seed, rows=None):
    return {
        r['oi']: min(
            (h for h in SOURCES if h != r['image']),
            key=lambda h: hashlib.sha256(
                f'boshy-scenery-v1\0{seed}\0{r["oi"]}\0{h}'.encode()
            ).digest(),
        )
        for r in (catalogue() if rows is None else rows)
    }


def texture(original, source):
    """Preserve dimensions and every alpha value, including translucent decoration."""
    source = source.convert('RGBA')
    canvas = Image.new('RGB', source.size, '#101825')
    canvas.paste(source, (0, 0), source.getchannel('A'))
    out = (
        ImageEnhance.Brightness(
            ImageOps.fit(canvas, original.size, method=Image.Resampling.NEAREST)
        )
        .enhance(0.8)
        .convert('RGBA')
    )
    out.putalpha(original.convert('RGBA').getchannel('A'))
    return out


def audit_game(path, expected, rows):
    """Refuse objects that gained collisions, changed size, or changed source image."""
    data = Path(path).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Unsupported game checksum')
    wanted = {r['oi']: r for r in rows}
    found = set()
    oi = None
    kind = None
    for tag, payload in chunks(data, 2495627, len(data)):
        if tag != 0x2229:
            continue
        for tag, body in chunks(payload, 4, len(payload)):
            if tag == 0x4444:
                oi, kind = struct.unpack_from('<HH', body)
            elif tag == 0x4446 and oi in wanted:
                row = wanted[oi]
                if (
                    kind != 1
                    or len(body) != 18
                    or struct.unpack('<4IH', body)
                    != (18, 0, row['width'], row['height'], row['image'])
                ):
                    raise ValueError('Scenery object is not collision-free: ' + str(oi))
                found.add(oi)
    if found != set(wanted):
        raise ValueError('Missing scenery objects')


def prepare(base, manifest):
    if manifest['options'].get('extras', {}).get('version', 0) >= 7:
        from sprite_chaos import prepare as expanded

        return expanded(base, manifest)
    from native_session import atomic
    from lab import EXPECTED

    root = Path(base) / 'menu-runtime'
    root.mkdir(exist_ok=True)
    plan = root / 'scenery.bin'
    # Clear stale session first; a failed preparation always leaves original scenery.
    atomic(plan, MAGIC + bytes(36))
    if not manifest['options'].get('extras', {}).get('sprite_scenery', False):
        return False
    try:
        session = manifest['run_id']
        if len(session) != 32 or any(c not in '0123456789abcdef' for c in session):
            raise ValueError('Scenery session')
        rows = catalogue()
        game = Path(base) / 'IWBTB/I Wanna Be The Boshy.exe'
        audit_game(game, EXPECTED, rows)
        _, images = read_game(
            game, EXPECTED, extra_images=set(SOURCES) | {r['image'] for r in rows}
        )
        swaps = mapping(manifest['seed'], rows)
        folder = root / 'scenery'
        folder.mkdir(exist_ok=True)
        for i, row in enumerate(rows):
            original = image(images[row['image']], max_side=2048)
            source = image(images[swaps[row['oi']]], max_side=2048)
            if original.size != (row['width'], row['height']):
                raise ValueError('Scenery dimensions')
            original.save(folder / f'o{i:02d}.png')
            texture(original, source).save(folder / f'{i:02d}.png')
        atomic(
            root / 'scenery-map.json',
            (
                json.dumps(dict(version=1, run_id=session, swaps=swaps), indent=2)
                + '\n'
            ).encode(),
        )
        atomic(plan, MAGIC + session.encode('ascii') + struct.pack('<I', len(rows)))
        return True
    except Exception:
        logging.exception('Scenery shuffle unavailable; keeping original scenery')
        return False
