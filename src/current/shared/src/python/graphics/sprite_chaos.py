"""Geometry-preserving scenery, floor materials and actor palettes, revision 2."""

import hashlib
import json
import logging
import struct
import zlib
from pathlib import Path
from PIL import Image, ImageOps, ImageEnhance, ImageChops
from intro_cast import chunks, image
from sprite_scenery import SOURCES

MAGIC = b'BRV2'
TILES = (58, 54, 404, 2575, 1556, 3698, 4909, 2542)
PALETTES = (
    '#ef95ba',
    '#8fdaf2',
    '#e9c26c',
    '#b0ed8b',
    '#c7a0f0',
    '#f0a36b',
    '#83e6d3',
    '#e0e1ec',
)
CATEGORY_KEYS = {
    1: 'sprite_backgrounds',
    2: 'sprite_decor',
    4: 'sprite_tiles',
    8: 'sprite_actors',
}


def catalogue():
    return json.loads(
        Path(__file__)
        .with_name('sprite_chaos_catalogue.json')
        .read_text(encoding='utf-8')
    )['records']


def selected(r, options):
    return bool(
        options.get(CATEGORY_KEYS[r['category']], False)
        or r['category'] == 1
        and options.get('sprite_dim', 0)
    )


def choice(seed, r):
    cat = r['category']
    values = PALETTES if cat == 8 else TILES if cat == 4 else SOURCES
    identity = 'floor:' + str(min(r['frames'])) if cat == 4 else str(r['oi'])
    candidates = values if cat == 4 else [v for v in values if v != r['image']]
    return min(
        candidates,
        key=lambda v: hashlib.sha256(
            f'boshy-graphics-v2\0{seed}\0{cat}\0{identity}\0{v}'.encode()
        ).digest(),
    )


def render(original, source, category, dim=20, *, shuffle=True):
    original = original.convert('RGBA')
    alpha = original.getchannel('A')
    if category == 8:
        out = ImageOps.colorize(
            ImageOps.grayscale(original), '#080a10', source
        ).convert('RGBA')
    elif category == 4:
        tile = source.convert('RGB')
        material = Image.new('RGB', original.size)
        for y in range(0, original.height, tile.height):
            for x in range(0, original.width, tile.width):
                material.paste(tile, (x, y))
        light = ImageOps.grayscale(original).point(lambda n: 80 + n * 175 // 255)
        out = Image.blend(
            original.convert('RGB'),
            ImageChops.multiply(material, Image.merge('RGB', (light,) * 3)),
            0.78,
        ).convert('RGBA')
    else:
        if shuffle:
            source = source.convert('RGBA')
            canvas = Image.new('RGB', source.size, '#101825')
            canvas.paste(source, (0, 0), source.getchannel('A'))
            out = ImageOps.fit(
                canvas, original.size, method=Image.Resampling.NEAREST
            ).convert('RGBA')
        else:
            out = original.copy()
        if category == 1:
            out = ImageEnhance.Brightness(out).enhance(1 - dim / 100)
    out.putalpha(alpha)
    return out


def read_assets(game, expected, records):
    data = Path(game).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Unsupported game checksum')
    wanted = {r['oi'] for r in records}
    objects = {}
    bank = None
    oi = None
    kind = None
    for tag, payload in chunks(data, 2495627, len(data)):
        if tag == 0x2229:
            for tag, body in chunks(payload, 4, len(payload)):
                if tag == 0x4444:
                    oi, kind = struct.unpack_from('<HH', body)
                elif tag == 0x4446 and oi in wanted:
                    objects[oi] = (kind, body)
        elif tag == 0x6666:
            bank = payload
    if bank is None or set(objects) != wanted:
        raise ValueError('Incomplete graphics catalogue')
    from intro_cast import animations

    for r in records:
        kind, body = objects[r['oi']]
        if kind != r['type'] or len(body) != r['size']:
            raise ValueError('Graphics object layout')
        if kind == 1:
            if struct.unpack('<4IH', body) != (
                18,
                r['obstacle'],
                r['width'],
                r['height'],
                r['image'],
            ):
                raise ValueError('Floor collision geometry changed')
        else:
            if animations(body)[r['anim'], r['direction']][r['frame']] != r['image']:
                raise ValueError('Actor animation changed')
    needed = {r['image'] for r in records} | set(TILES) | set(SOURCES)
    pos = 4
    images = {}
    for _ in range(struct.unpack_from('<I', bank)[0]):
        handle, length, packed = struct.unpack_from('<III', bank, pos)
        pos += 12
        if pos + packed > len(bank):
            raise ValueError('Graphics bank bounds')
        if handle in needed:
            if not 32 <= length <= 12_000_000:
                raise ValueError('Graphics size')
            dec = zlib.decompressobj()
            raw = dec.decompress(bank[pos : pos + packed], length + 1)
            if len(raw) != length or not dec.eof or dec.unused_data:
                raise ValueError('Graphics length')
            images[handle] = raw
        pos += packed
    if needed - set(images) or pos != len(bank):
        raise ValueError('Incomplete graphics bank')
    for r in records:
        raw = images[r['image']]
        if struct.unpack_from('<HH', raw, 12) != (
            r['width'],
            r['height'],
        ) or struct.unpack_from('<4h', raw, 20) != (r['hx'], r['hy'], r['ax'], r['ay']):
            raise ValueError('Graphics anchor changed')
    return images


def prepare(base, manifest):
    from native_session import atomic
    from lab import EXPECTED

    root = Path(base) / 'menu-runtime'
    root.mkdir(exist_ok=True)
    plan = root / 'scenery.bin'
    atomic(plan, MAGIC + bytes(40))
    extra = manifest['options'].get('extras', {})
    if not extra.get('sprite_scenery', False):
        return False
    try:
        session = manifest['run_id']
        if len(session) != 32 or any(c not in '0123456789abcdef' for c in session):
            raise ValueError('Graphics session')
        allrows = catalogue()
        rows = [r for r in allrows if selected(r, extra)]
        mask = sum(k for k in CATEGORY_KEYS if any(r['category'] == k for r in rows))
        images = (
            read_assets(Path(base) / 'IWBTB/I Wanna Be The Boshy.exe', EXPECTED, rows)
            if rows
            else {}
        )
        decoded = {}
        folder = root / 'chaos'
        folder.mkdir(exist_ok=True)
        swaps = {}

        def im(handle):
            if handle not in decoded:
                decoded[handle] = image(images[handle], max_side=4096)
            return decoded[handle]

        for index, r in enumerate(allrows):
            if not selected(r, extra):
                continue
            original = im(r['image'])
            style = choice(manifest['seed'], r)
            source = style if r['category'] == 8 else im(style)
            out = render(
                original,
                source,
                r['category'],
                extra.get('sprite_dim', 20),
                shuffle=extra.get(CATEGORY_KEYS[r['category']], False),
            )
            # Never publish an altered outline; this also preserves MMF's alpha mask.
            if (
                out.size != original.size
                or out.getchannel('A').tobytes() != original.getchannel('A').tobytes()
            ):
                raise ValueError('Graphics mask changed')
            original.save(folder / f'o{index:03d}.png')
            out.save(folder / f'{index:03d}.png')
            swaps[str(r['oi'])] = style
        atomic(
            root / 'chaos-map.json',
            (
                json.dumps(
                    dict(version=2, run_id=session, options=extra, swaps=swaps),
                    indent=2,
                )
                + '\n'
            ).encode(),
        )
        atomic(
            plan,
            MAGIC + session.encode('ascii') + struct.pack('<II', len(allrows), mask),
        )
        return True
    except Exception:
        logging.exception('Sprite chaos unavailable; keeping original graphics')
        return False
