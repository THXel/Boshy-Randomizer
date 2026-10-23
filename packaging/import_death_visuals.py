#!/usr/bin/env python3
"""Import death cosmetics from a user's GM8 project and original game folder.

Accepts a locally extracted .gm81 project, never downloads or ships game assets.
WannaFest additionally needs the OFL Press Start 2P font. The original death
impact and jingle are combined; reset sounds and behavior remain unchanged.
"""

import argparse
import hashlib
import json
import random
import struct
import zlib
import subprocess
import wave
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont


class Reader:
    def __init__(self, data):
        self.data = data
        self.at = 0

    def take(self, n):
        if not 0 <= n <= len(self.data) - self.at:
            raise ValueError('Truncated GM8 project')
        out = self.data[self.at : self.at + n]
        self.at += n
        return out

    def u(self):
        return struct.unpack('<I', self.take(4))[0]

    def string(self):
        return self.take(self.u()).decode('utf-8')

    def packed(self):
        return Reader(zlib.decompress(self.take(self.u())))

    def assets(self):
        if self.u() != 800:
            raise ValueError('Unsupported GM8 resource version')
        count = self.u()
        if count > 100000:
            raise ValueError('GM8 resource count')
        out = []
        for _ in range(count):
            r = self.packed()
            out.append(r if r.u() else None)
        return out


def sprites(project, wanted):
    r = Reader(Path(project).read_bytes())
    r.take(28)
    if r.u() != 800:
        raise ValueError('Unsupported GM8 project')
    r.packed()
    r.assets()
    r.take(8)
    if r.u() != 800:
        raise ValueError('Unsupported GM8 constants')
    for _ in range(r.u()):
        r.string()
        r.string()
    r.take(8)
    r.assets()
    bank = r.assets()
    result = {}
    for index in wanted:
        r = bank[index]
        if r is None:
            raise ValueError('Missing death sprite')
        name = r.string()
        r.take(8)
        if r.u() != 800:
            raise ValueError('Unsupported sprite')
        origin = (r.u(), r.u())
        count = r.u()
        frames = []
        if not 1 <= count <= 64:
            raise ValueError('Sprite frame count')
        for _ in range(count):
            if r.u() != 800:
                raise ValueError('Unsupported sprite frame')
            w, h = r.u(), r.u()
            if not 0 < w <= 2048 or not 0 < h <= 2048:
                raise ValueError('Sprite dimensions')
            raw = r.take(r.u())
            if len(raw) != w * h * 4:
                raise ValueError('Sprite pixels')
            frames.append(Image.frombytes('RGBA', (w, h), raw, 'raw', 'BGRA'))
        result[index] = (name, origin, frames)
    return result


def blood_texture(project):
    r = Reader(Path(project).read_bytes())
    r.take(28)
    if r.u() != 800:
        raise ValueError('Unsupported GM8 project')
    r.packed()
    r.assets()
    r.take(8)
    if r.u() != 800:
        raise ValueError('Unsupported GM8 constants')
    for _ in range(r.u()):
        r.string()
        r.string()
    r.take(8)
    r.assets()
    r.assets()
    for background in r.assets():
        if background is None:
            continue
        name = background.string()
        background.take(8)
        if name != 'texBlood':
            continue
        if background.u() != 710:
            raise ValueError('Unsupported GM8 background')
        background.take(28)
        if background.u() != 800:
            raise ValueError('Unsupported background image')
        w, h = background.u(), background.u()
        raw = background.take(background.u())
        if (w, h) != (8, 8) or len(raw) != 256:
            raise ValueError('Unexpected blood texture')
        return Image.frombytes('RGBA', (w, h), raw, 'raw', 'BGRA')
    raise ValueError('WannaFest blood texture missing')


def blood_wannafest(texture):
    # Blood3D draws an 8x8x8 cube with texBlood, not the tiny sprBlood used
    # by the HP damage effect. Bake those textured faces into native 2D frames.
    import numpy as np

    vertices = np.array(
        [(x, y, z) for x in (-4, 4) for y in (-4, 4) for z in (-4, 4)], dtype=float
    )
    faces = (
        (0, 1, 3, 2),
        (4, 6, 7, 5),
        (0, 4, 5, 1),
        (2, 3, 7, 6),
        (0, 2, 6, 4),
        (1, 5, 7, 3),
    )
    tex = np.array(texture)
    frames = []
    for frame in range(32):
        a = frame * math.tau / 32
        cx, sx = math.cos(a + 0.3), math.sin(a + 0.3)
        cy, sy = math.cos(a * 2 + 0.7), math.sin(a * 2 + 0.7)
        cz, sz = math.cos(a * 3), math.sin(a * 3)
        rx = np.array(((1, 0, 0), (0, cx, -sx), (0, sx, cx)))
        ry = np.array(((cy, 0, sy), (0, 1, 0), (-sy, 0, cy)))
        rz = np.array(((cz, -sz, 0), (sz, cz, 0), (0, 0, 1)))
        points = vertices @ (rz @ ry @ rx).T
        canvas = np.zeros((20, 20, 4), dtype=np.uint8)
        for face in sorted(faces, key=lambda f: float(points[list(f), 2].mean())):
            p = points[list(face), :2] + 10
            matrix = np.column_stack((p[1] - p[0], p[3] - p[0]))
            if abs(np.linalg.det(matrix)) < 1e-8:
                continue
            inverse = np.linalg.inv(matrix)
            for y in range(
                max(0, math.floor(p[:, 1].min())), min(20, math.ceil(p[:, 1].max()))
            ):
                for x in range(
                    max(0, math.floor(p[:, 0].min())), min(20, math.ceil(p[:, 0].max()))
                ):
                    u, v = inverse @ (np.array((x + 0.5, y + 0.5)) - p[0])
                    if 0 <= u < 1 and 0 <= v < 1:
                        canvas[y, x] = tex[min(7, int(v * 8)), min(7, int(u * 8))]
        frames.append(Image.fromarray(canvas))
    return frames


def screen_kamilia(sprite, red):
    # The original RedEffect ramps up by .04 per 50 Hz step until it reaches .52.
    # Frame zero remains transparent because Boshy's native object also exists alive.
    schedule = list(range(15)) + list(range(15, 41, 5))
    frames = []
    color = red.getpixel((0, 0))[:3]
    for tick in schedule:
        canvas = Image.new(
            'RGBA', (800, 608), (*color, round(255 * min(0.52, tick * 0.04)))
        )
        part = sprite.copy()
        part.putalpha(
            part.getchannel('A').point(
                lambda a: round(a * max(0, min(1, (tick - 10) / 30)))
            )
        )
        canvas.alpha_composite(part, (400 - part.width // 2, 304 - part.height // 2))
        frames.append(canvas.resize((640, 480), Image.Resampling.LANCZOS))
    return (
        frames,
        50,
        len(frames) - 1,
        [b - a for a, b in zip(schedule, schedule[1:] + [45])],
    )


def screen_wannafest(parts, game, font):
    noise = [
        Image.open(game / 'data/textures/intro' / f'vhs{i}.jpg').convert('RGBA')
        for i in range(1, 6)
    ]
    title = [p.resize((644, 320), Image.Resampling.NEAREST) for p in parts]
    text = Image.new('RGBA', (800, 30))
    draw = ImageDraw.Draw(text)
    draw.text(
        (400, 0),
        "Press 'R' to try again",
        font=ImageFont.truetype(str(font), 8),
        anchor='mt',
        fill='white',
    )
    text = text.resize((2400, 90), Image.Resampling.NEAREST)
    text = text.crop((800, 0, 1600, 90))
    rng = random.Random('WannaFest death cosmetics v1')
    frames = []
    schedule = sorted(set(range(0, 200, 5)) | set(range(61, 69)) | set(range(78, 87)))
    for i, tick in enumerate(schedule):
        t = tick / 50
        f = max(0, min(1, -1.5 + t))
        canvas = Image.new('RGBA', (800, 608), (0, 0, 0, round(255 * f)))
        if t >= 0.8:
            shake = round(rng.uniform(-1, 1) * max(0, t - 1.9) * 3)
            for j, arrival in enumerate((1.315193, 1.661859)):
                remaining = max(0, (arrival - t) * 50)
                if remaining < 5:
                    offset = ((5 + remaining) ** 2 - 25) * 10 * (-1 if j == 0 else 1)
                    impact = (
                        max(0, 15 - max(0, t - arrival) * 50 * 3) if t >= arrival else 0
                    )
                    offset += impact * (1 if j == 0 else -1)
                    canvas.alpha_composite(
                        title[j], (round(400 - 80 * 4 + offset), 304 - 35 * 4 + shake)
                    )
            y = round(384 + max(0, (2.700136 - t) * 50) ** 2) + shake
            if y < 608:
                canvas.alpha_composite(text, (0, y))
            if f:
                texture = noise[i % 5]
                tile = Image.new('RGBA', (800, 608))
                dx = rng.randrange(texture.width)
                dy = (-i * 6) % texture.height
                for x in range(-dx, 800, texture.width):
                    for y in range(-dy, 608, texture.height):
                        tile.alpha_composite(texture, (x, y))
                # Original VideoNoise uses additive blending: white letters stay white.
                import numpy as np

                pixels = np.array(canvas, dtype=np.float32)
                grain = np.array(tile, dtype=np.float32)[:, :, :3]
                alpha = pixels[:, :, 3:4] / 255
                pixels[:, :, :3] = np.minimum(
                    255, pixels[:, :, :3] + grain * 0.6 * f / np.maximum(alpha, 1 / 255)
                )
                canvas = Image.fromarray(pixels.astype('uint8'), 'RGBA')
        frames.append(canvas.resize((640, 480), Image.Resampling.NEAREST))
    durations = [b - a for a, b in zip(schedule, schedule[1:] + [200])]
    return frames, 10, schedule.index(160), durations


def write_group(root, role, frames, fps, loop, origin=None):
    folder = root / 'death-visuals' / role
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, im in enumerate(frames):
        path = folder / f'{i:03d}.png'
        im.save(path)
        rows.append(
            dict(
                file=path.relative_to(root).as_posix(),
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    group = dict(frames=rows, fps=fps, loop=loop)
    if origin is not None:
        group.update(size=list(frames[0].size), origin=list(origin))
    return group


def death_audio(pack, game, root, data):
    impact = game / (
        'SE/sndDeath.wav'
        if pack == 'kamilia3'
        else 'data/sounds/wannafest/sndDeath.ogg'
    )
    jingle = game / (
        'Music/Death.ogg'
        if pack == 'kamilia3'
        else 'data/sounds/wannafest/game_over.ogg'
    )
    out = root / 'death-visuals/death-sequence.wav'
    delay = 0 if pack == 'kamilia3' else 800
    filters = f'[1:a]adelay={delay}:all=1[late];[0:a][late]amix=inputs=2:normalize=0:duration=longest,alimiter=limit=0.95:level=false:latency=true'
    subprocess.run(
        [
            'ffmpeg',
            '-hide_banner',
            '-loglevel',
            'error',
            '-y',
            '-i',
            str(impact),
            '-i',
            str(jingle),
            '-filter_complex',
            filters,
            '-ar',
            '44100',
            '-ac',
            '2',
            '-c:a',
            'pcm_s16le',
            str(out),
        ],
        check=True,
    )
    with wave.open(str(out)) as audio:
        duration = audio.getnframes() / audio.getframerate()
    name = out.relative_to(root).as_posix()
    data['tracks'] = [r for r in data['tracks'] if r['file'] != name]
    for row in data['tracks']:
        row['roles'] = [r for r in row.get('roles', []) if r != 'death']
    data['tracks'].append(
        dict(
            file=name,
            name='Original death sequence',
            seconds=duration,
            sha256=hashlib.sha256(out.read_bytes()).hexdigest(),
            roles=['death'],
            shuffle=False,
        )
    )


def build(pack, project, game, root, font=None):
    data = json.loads((root / 'pack.json').read_text())
    if data.get('id') != pack:
        raise ValueError('Soundpack identity mismatch')
    bank = sprites(project, (0, 21, 40) if pack == 'kamilia3' else (545,))
    if pack == 'kamilia3':
        screen, fps, loop, ticks = screen_kamilia(bank[21][2][0], bank[40][2][0])
        _, origin, blood = bank[0]
        blood = blood + [Image.new('RGBA', blood[0].size)]
        bloodfps = 16
        bloodloop = len(blood) - 1
    else:
        if font is None:
            raise ValueError('Press Start 2P font required')
        screen, fps, loop, ticks = screen_wannafest(bank[545][2], game, font)
        origin = (10, 10)
        blood = blood_wannafest(blood_texture(project))
        bloodfps = 16
        bloodloop = 0
    visual = dict(
        version=1,
        screen=write_group(root, 'screen', screen, fps, loop),
        blood=write_group(root, 'blood', blood, bloodfps, bloodloop, origin),
    )
    visual['screen']['ticks'] = ticks
    death_audio(pack, game, root, data)
    data['death_visuals'] = visual
    path = root / 'pack.json'
    temp = path.with_suffix('.json.tmp')
    temp.write_text(json.dumps(data, indent=2) + '\n')
    temp.replace(path)
    return dict(pack=pack, screen_frames=len(screen), blood_frames=len(blood))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('pack', choices=('kamilia3', 'wannafest22'))
    p.add_argument('project', type=Path)
    p.add_argument('game', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--font', type=Path)
    a = p.parse_args()
    print(json.dumps(build(a.pack, a.project, a.game, a.output, a.font)))
