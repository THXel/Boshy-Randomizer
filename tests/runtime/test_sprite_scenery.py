import hashlib
import json
import random
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import sprite_scenery as scenery
from run_extras import defaults, normalize, flags
from seed_codec import defaults as options
from seed_share import encode, decode


class SceneryTests(unittest.TestCase):
    def test_deterministic_independent_mapping_and_variation(self):
        state = random.getstate()
        a = scenery.mapping('A')
        self.assertEqual(a, scenery.mapping('A'))
        self.assertEqual(random.getstate(), state)
        self.assertNotEqual(a, scenery.mapping('B'))
        self.assertGreater(len(set(a.values())), 5)
        for r in scenery.catalogue():
            self.assertNotEqual(a[r['oi']], r['image'])

    def test_original_alpha_and_geometry_preserved(self):
        im = Image.new('RGBA', (5, 3), (50, 60, 70, 255))
        im.putalpha(Image.frombytes('L', im.size, bytes([0, 13, 128, 254, 255] * 3)))
        out = scenery.texture(im, Image.new('RGBA', (9, 8), (200, 150, 90, 255)))
        self.assertEqual(out.size, im.size)
        self.assertEqual(out.getchannel('A').tobytes(), im.getchannel('A').tobytes())
        self.assertNotEqual(out.tobytes(), im.tobytes())

    def test_collision_and_geometry_changes_are_rejected(self):
        row = dict(oi=123, width=640, height=480, image=99)
        header = struct.pack('<HH', 123, 1)
        for obstacle, w, ty in ((0, 640, 1), (1, 640, 1), (0, 639, 1), (0, 640, 2)):
            body = struct.pack('<4IH', 18, obstacle, w, 480, 99)

            def chunks(data, start, end):
                return (
                    [(0x2229, b'fake')]
                    if data == b'game'
                    else [(0x4444, struct.pack('<HH', 123, ty)), (0x4446, body)]
                )

            with (
                tempfile.TemporaryDirectory() as d,
                patch.object(scenery, 'chunks', side_effect=chunks),
            ):
                p = Path(d) / 'game'
                p.write_bytes(b'game')
                expected = hashlib.sha256(b'game').hexdigest()
                if (obstacle, w, ty) == (0, 640, 1):
                    scenery.audit_game(p, expected, [row])
                else:
                    with self.assertRaises(ValueError):
                        scenery.audit_game(p, expected, [row])

    def test_off_and_failed_generation_clear_stale_plan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d) / 'menu-runtime'
            root.mkdir()
            p = root / 'scenery.bin'
            p.write_bytes(b'stale')
            self.assertFalse(scenery.prepare(d, dict(options={})))
            self.assertEqual(p.read_bytes(), b'BRV1' + bytes(36))
            with self.assertLogs(level='ERROR'):
                self.assertFalse(
                    scenery.prepare(
                        d,
                        dict(
                            run_id='a' * 32,
                            seed='A',
                            options={'extras': {'sprite_scenery': True}},
                        ),
                    )
                )
            self.assertEqual(p.read_bytes(), b'BRV1' + bytes(36))

    def test_option_defaults_off_and_roundtrips_without_flag_overlap(self):
        self.assertFalse(defaults()['sprite_scenery'])
        o = options()
        before = flags(o)
        o['extras']['sprite_scenery'] = True
        self.assertEqual(flags(o) ^ before, 32768)
        self.assertEqual(decode(encode('TEST', o))[1], o)
        old = {k: v for k, v in defaults().items() if not k.startswith('sprite_')}
        old['version'] = 5
        self.assertEqual(normalize(old), old)

    def test_saved_seed_keeps_archived_encoder(self):
        from seed_share import encode_saved
        from types import SimpleNamespace

        old = SimpleNamespace(encode=lambda seed, options, base: 'BR9-original')
        rules = SimpleNamespace(module=lambda name: old)
        self.assertEqual(encode_saved('OLD', {}, ROOT, rules), 'BR9-original')

    def test_native_catalogue_matches_reviewed_scenes_and_layout(self):
        text = (ROOT / 'sprite_scenery_catalogue.h').read_text()
        for r in scenery.catalogue():
            self.assertTrue(
                all(
                    3 <= f <= 64 and f not in (42, 46, 48, 49, 50, 57, 59)
                    for f in r['frames']
                )
            )
            mask = sum(1 << (f - 1) for f in r['frames'])
            entry = '{%d,%d,%d,0x%xU,0x%xU}' % (
                r['oi'],
                r['width'],
                r['height'],
                mask & 0xFFFFFFFF,
                mask >> 32,
            )
            self.assertIn(entry, text)

    def test_hack_rows_do_not_overlap_and_all_translations_exist(self):
        from types import SimpleNamespace
        from menu_controls import controls

        rows = controls(SimpleNamespace(page='extras'))
        rects = [r for _, r in rows]
        for a, b in zip(rects, rects[1:]):
            self.assertLess(a[3], b[1])
        from run_extras import EXTRAS

        label, hint = EXTRAS[-1][1:3]
        for lang in ('de', 'en', 'ru', 'es', 'ja'):
            data = json.loads((ROOT / f'locales/{lang}.json').read_text())
            self.assertTrue(data[label])
            self.assertTrue(data[hint])


if __name__ == '__main__':
    unittest.main()
