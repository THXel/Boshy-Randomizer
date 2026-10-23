"""Whole original background groups, with native layers and movement preserved."""

import hashlib
import json
import struct
import zlib
import logging
from pathlib import Path
from PIL import Image, ImageEnhance
from io import BytesIO
from intro_cast import chunks, image

MAGIC = b'BGB1'
PARALLAX_MASK_VERSION = 1


def catalogue():
    return json.loads(
        Path(__file__)
        .with_name('background_sets_catalogue.json')
        .read_text(encoding='utf-8')
    )


def mapping(seed, shuffle=True):
    sets = catalogue()['sets']
    out = []
    for i, target in enumerate(sets):
        candidates = [
            n
            for n, source in enumerate(sets)
            if not target['locked'] or source['coefficient'] == target['coefficient']
        ]
        alternatives = [n for n in candidates if n != i]
        out.append(
            min(
                alternatives or candidates,
                key=lambda n: hashlib.sha256(
                    f'boshy-background-set-v1\0{seed}\0{i}\0{n}'.encode()
                ).digest(),
            )
            if shuffle
            else i
        )
    return out


def assets(game, expected):
    data = Path(game).read_bytes()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Unsupported game checksum')
    rows = catalogue()['objects']
    wanted = {r['oi']: r for r in rows}
    found = set()
    bank = None
    oi = kind = None
    for t, b in chunks(data, 2495627, len(data)):
        if t == 0x2229:
            for tag, body in chunks(b, 4, len(b)):
                if tag == 0x4444:
                    oi, kind = struct.unpack_from('<HH', body)
                elif tag == 0x4446 and oi in wanted:
                    row = wanted[oi]
                    if (
                        kind != row['type']
                        or hashlib.sha256(body).hexdigest() != row['sha256']
                    ):
                        raise ValueError('Background object changed')
                    found.add(oi)
        elif t == 0x6666:
            bank = b
    if found != set(wanted) or bank is None:
        raise ValueError('Missing background resources')
    needed = {r['image'] for r in rows}
    out = {}
    at = 4
    for _ in range(struct.unpack_from('<I', bank)[0]):
        handle, length, packed = struct.unpack_from('<III', bank, at)
        at += 12
        if at + packed > len(bank):
            raise ValueError('Background bank bounds')
        if handle in needed:
            if not 32 <= length <= 12_000_000:
                raise ValueError('Background size')
            decoder = zlib.decompressobj()
            raw = decoder.decompress(bank[at : at + packed], length + 1)
            if len(raw) != length or not decoder.eof or decoder.unused_data:
                raise ValueError('Background image length')
            out[handle] = raw
        at += packed
    if set(out) != needed or at != len(bank):
        raise ValueError('Incomplete background images')
    return out


def parallax_texture(source):
    # The native Parallaxer scans GetPixel against a colour key, not alpha.
    # Its trapezoid is a per-row width mask, not the final displayed outline.
    alpha = source.convert('RGBA').getchannel('A')
    if any(alpha.histogram()[1:255]):
        raise ValueError('Parallax mask must be binary')
    result = Image.new('RGB', source.size, (0, 0, 0))
    result.paste(source.convert('RGB'), (0, 0), alpha)
    return result


def repair_parallax_assets(base):
    """Repair presentation from a frozen older prepare without changing its mapping."""
    folder = Path(base) / 'menu-runtime/background-sets'
    for i, row in enumerate(catalogue()['objects']):
        if row['oi'] != 681:
            continue
        for prefix in ('o', ''):
            path = folder / f'{prefix}{i:02d}.png'
            with Image.open(path) as picture:
                if picture.size != (row['width'], row['height']):
                    raise ValueError('Parallax geometry')
                result = parallax_texture(picture)
            data = BytesIO()
            result.save(data, format='PNG')
            from native_session import atomic

            atomic(path, data.getvalue())


def prepare(base, manifest):
    from native_session import atomic
    from lab import EXPECTED

    root = Path(base) / 'menu-runtime'
    root.mkdir(exist_ok=True)
    plan = root / 'background-sets.bin'
    atomic(plan, MAGIC + bytes(76))
    ex = manifest['options'].get('extras', {})
    if (
        ex.get('version', 0) < 7
        or not ex.get('sprite_scenery')
        or not (ex.get('sprite_backgrounds') or ex.get('sprite_dim', 0))
    ):
        return False
    try:
        run_id = manifest['run_id']
        dim = ex.get('sprite_dim', 20)
        if (
            len(run_id) != 32
            or any(c not in '0123456789abcdef' for c in run_id)
            or dim not in (0, 20, 40, 60)
        ):
            raise ValueError('Background plan')
        rows = catalogue()['objects']
        images = assets(Path(base) / 'IWBTB/I Wanna Be The Boshy.exe', EXPECTED)
        folder = root / 'background-sets'
        folder.mkdir(exist_ok=True)
        for i, r in enumerate(rows):
            raw = images[r['image']]
            if struct.unpack_from('<HH', raw, 12) != (
                r['width'],
                r['height'],
            ) or struct.unpack_from('<4h', raw, 20) != tuple(
                r[k] for k in ('hx', 'hy', 'ax', 'ay')
            ):
                raise ValueError('Background geometry')
            original = image(raw, max_side=4096)
            out = ImageEnhance.Brightness(original).enhance(1 - dim / 100)
            out.putalpha(original.getchannel('A'))
            if r['oi'] == 681:
                original = parallax_texture(original)
                out = parallax_texture(out)
            original.save(folder / f'o{i:02d}.png')
            out.save(folder / f'{i:02d}.png')
        choices = mapping(manifest['seed'], ex.get('sprite_backgrounds', False))
        atomic(
            root / 'background-sets-map.json',
            (
                json.dumps(
                    dict(version=1, run_id=run_id, dim=dim, sets=choices), indent=2
                )
                + '\n'
            ).encode(),
        )
        atomic(
            plan, MAGIC + run_id.encode('ascii') + struct.pack('<11I', 9, dim, *choices)
        )
        return True
    except Exception:
        logging.exception('Whole background sets unavailable; keeping existing scenery')
        return False
