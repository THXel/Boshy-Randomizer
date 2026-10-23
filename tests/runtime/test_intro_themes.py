import json
import random
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import intro_themes as themes
import intro_cast as cast


def raw(width, height):
    header = bytearray(32)
    struct.pack_into('<HH', header, 12, width, height)
    header[16] = 4
    struct.pack_into('<hh', header, 20, width // 2, height - 1)
    return bytes(header) + bytes([31, 91, 151]) * ((width + 1) // 2 * 2 * height)


class IntroThemesTests(unittest.TestCase):
    def test_no_immediate_repeats(self):
        previous = None
        rng = random.Random(87)
        seen = set()
        for _ in range(200):
            chosen = themes.choose(previous, rng)
            self.assertNotEqual(chosen, previous)
            seen.add(chosen)
            previous = chosen
        self.assertEqual(seen, set(range(len(themes.THEMES))))

    def test_gameplay_rng_untouched(self):
        before = random.getstate()
        themes.choose(None)
        self.assertEqual(random.getstate(), before)

    def test_original_outline_and_partial_alpha_preserved(self):
        original = Image.new('RGBA', (5, 3), (80, 100, 120, 255))
        original.putalpha(Image.frombytes('L', (5, 3), bytes([0, 13, 128, 255, 0] * 3)))
        result = themes.floor(original, Image.new('RGB', (2, 2), (200, 100, 50)))
        self.assertEqual(result.size, original.size)
        self.assertEqual(
            result.getchannel('A').tobytes(), original.getchannel('A').tobytes()
        )
        self.assertNotEqual(
            result.convert('RGB').tobytes(), original.convert('RGB').tobytes()
        )

    def test_background_fills_original_extent_and_dims(self):
        source = Image.new('RGBA', (5, 4), (255, 255, 255, 255))
        result = themes.backdrop(source, (9, 7))
        self.assertEqual(result.size, (9, 7))
        self.assertEqual(result.getchannel('A').getextrema(), (255, 255))
        self.assertLess(result.getpixel((3, 3))[0], 160)

    def test_large_images_require_explicit_opt_in(self):
        data = raw(300, 1)
        with self.assertRaises(ValueError):
            cast.image(data)
        self.assertEqual(cast.image(data, max_side=2048).size, (300, 1))

    def test_plan_keeps_geometry_hotspots_paths_and_rollback_assets(self):
        images = {h: raw(4, 4) for h in themes.IMAGE_IDS}
        for oi, _, h in themes.TARGETS:
            images[h] = (
                raw(823, 480)
                if oi == 30
                else raw(32, 32) if oi in (22, 24) else raw(16, 16)
            )
        with tempfile.TemporaryDirectory() as folder:
            plan = themes.make_plan(folder, images, 0)
            self.assertEqual(len(plan), 1572)
            self.assertEqual(plan[:12], b'BRT1' + struct.pack('<II', 13, 0))
            for index, (oi, direction, h) in enumerate(themes.TARGETS):
                original = cast.image(images[h], max_side=2048)
                record = struct.unpack_from('<4I2i96s', plan, 12 + 120 * index)
                self.assertEqual(record[:4], (oi, direction, *original.size))
                self.assertEqual(record[4:6], struct.unpack_from('<hh', images[h], 20))
                self.assertEqual(
                    record[6].rstrip(b'\0'),
                    ('..\\menu-runtime\\theme\\' + f'{index:02d}.png').encode(),
                )
                with Image.open(Path(folder) / f'{index:02d}.png') as result:
                    self.assertEqual(result.size, original.size)
                    if oi != 30:
                        self.assertEqual(
                            result.getchannel('A').tobytes(),
                            original.getchannel('A').tobytes(),
                        )
                with Image.open(Path(folder) / f'o{index:02d}.png') as rollback:
                    self.assertEqual(rollback.tobytes(), original.tobytes())

    def test_invalid_theme_rejected(self):
        for value in (-1, 4, True, '0', None):
            with self.assertRaises(ValueError):
                themes.make_plan('/unused', {}, value)

    def test_failed_preparation_clears_stale_plan_keeps_previous(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'menu-runtime'
            root.mkdir()
            (root / 'theme.bin').write_bytes(b'stale')
            last = root / 'theme-last.json'
            last.write_text('{"theme":1}')
            with (
                patch.object(
                    themes, 'make_plan', side_effect=ValueError('Missing graphic')
                ),
                self.assertLogs(level='ERROR'),
            ):
                self.assertIsNone(themes.prepare(folder, {}))
            self.assertFalse((root / 'theme.bin').exists())
            self.assertEqual(json.loads(last.read_text()), {'theme': 1})


if __name__ == '__main__':
    unittest.main()
