"""Rare optional native spider attack, using assets from the user's game only."""

import hashlib
import json
import struct
import time
from pathlib import Path

MAGIC = b'BRS1'
ROAR = 'aaaaaaaaaaaah_newandlouder'
SPRITE_VERSION = 2


def prepare_orientations(base):
    from PIL import Image

    folder = Path(base) / 'menu-runtime'
    with Image.open(folder / 'spider.png') as source:
        source = source.convert('RGBA')
        # The original spider faces down; its central body is at (64, 28).
        tile = Image.new('RGBA', (192, 192))
        tile.alpha_composite(
            source, (96 - source.width // 2, 96 - round(source.height * 28 / 85))
        )
        for facing in range(32):
            tile.rotate(facing * 360 / 32, resample=Image.Resampling.BICUBIC).save(
                folder / f'spider-{facing:02d}.png'
            )


def initial(seed):
    state = (
        int.from_bytes(
            hashlib.sha256(('boshy-spider-v1\0' + str(seed)).encode()).digest()[:4],
            'little',
        )
        or 1
    )
    return dict(
        version=1, rng=state, remaining=300000 + state % 1500001, attacks=0, hits=0
    )


def prepare(base, manifest):
    from lab import EXPECTED
    from native_session import atomic

    base = Path(base)
    folder = base / 'menu-runtime'
    folder.mkdir(exist_ok=True)
    if not manifest['options'].get('extras', {}).get('spider', False):
        atomic(folder / 'spider.bin', MAGIC + bytes(52))
        return
    from intro_cast import read_game, image
    from music_randomizer import extract

    _, images = read_game(
        base / 'IWBTB/I Wanna Be The Boshy.exe', EXPECTED, extra_images=(2287,)
    )
    im = image(images[2287], max_side=2048)
    im.thumbnail((128, 128))
    im.save(folder / 'spider.png')
    prepare_orientations(base)
    audio = extract(base / 'IWBTB/I Wanna Be The Boshy.exe', EXPECTED, names=(ROAR,))[
        ROAR
    ]
    if not audio.startswith(b'OggS'):
        raise ValueError('Unexpected spider sound')
    atomic(folder / 'spider.ogg', audio)
    state = initial(manifest['seed'])
    path = base / 'native-runs' / manifest['run_id'] / 'spider.json'
    if path.exists():
        saved = json.loads(path.read_text(encoding='utf-8'))
        if (
            saved.get('version') != 1
            or any(
                type(saved.get(k)) is not int
                for k in ('rng', 'remaining', 'attacks', 'hits')
            )
            or not 0 < saved['rng'] <= 0xFFFFFFFF
            or not 0 <= saved['remaining'] <= 1800000
        ):
            raise ValueError('Invalid spider state')
        state = saved
    atomic(
        folder / 'spider.bin',
        MAGIC
        + manifest['run_id'].encode()
        + struct.pack(
            '<5I', state['rng'], state['remaining'], state['attacks'], state['hits'], 1
        ),
    )


class SpiderCycle:
    def __init__(self, player):
        from native_telemetry import NativeReader

        self.player = player
        self.reader = NativeReader(player)
        self.last = 0
        self.data = None

    def observe(self, force=False):
        now = time.monotonic()
        if not force and now - self.last < 5:
            return
        self.last = now
        try:
            state = self.reader.read('SpiderState', 10)
        except (OSError, RuntimeError, ValueError, struct.error):
            return
        if not state or state[0] != 0x42525331 or state[1] != 1 or state[7]:
            return
        from native_session import write_json

        self.data = dict(
            version=1, rng=state[3], remaining=state[2], attacks=state[4], hits=state[5]
        )
        write_json(self.player.folder / 'spider.json', self.data)
