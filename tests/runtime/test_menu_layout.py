import sys
import tempfile
import unittest
import json
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from menu_model import Menu
from menu_layout import load, save, viewport, inverse
from menu_controls import controls


class Layout(unittest.TestCase):
    def model(self, base=ROOT):
        with patch(
            'menu_model.summary', return_value={'exists': False, 'completed': False}
        ):
            return Menu(NS(base=base))

    def test_preferences_default_validate_and_remain_local(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'INI').mkdir()
            self.assertEqual(load(root), 'standard')
            save(root, 'large')
            self.assertEqual(load(root), 'large')
            with self.assertRaises(ValueError):
                save(root, 'huge')
            (root / 'INI/menu_preferences.json').write_text('{broken')
            self.assertEqual(load(root), 'standard')

    def test_viewport_fits_and_mouse_maps_exactly_back(self):
        for page in (
            'slots',
            'new',
            'advanced',
            'characters',
            'appearance',
            'seed',
            'result',
        ):
            self.assertIsNone(viewport(page, (1760, 1320)))
            for size in ((640, 480), (800, 600), (960, 720), (1280, 720)):
                v = viewport(page, size)
                if not v:
                    continue
                src, dst = v
                self.assertTrue(0 <= dst[0] < dst[2] <= 880)
                self.assertTrue(0 <= dst[1] < dst[3] <= 660)
                point = ((dst[0] + dst[2]) / 2, (dst[1] + dst[3]) / 2)
                got = inverse(point, v)
                self.assertAlmostEqual(got[0], (src[0] + src[2]) / 2)
                self.assertAlmostEqual(got[1], (src[1] + src[3]) / 2)
                self.assertIsNone(inverse((0, 0), v))

    def test_widescreen_preserves_physical_text_proportions(self):
        for size in ((1280, 720), (1920, 1080), (720, 1280)):
            src, dst = viewport('new', size)
            sx = (dst[2] - dst[0]) / (src[2] - src[0]) * size[0] / 880
            sy = (dst[3] - dst[1]) / (src[3] - src[1]) * size[1] / 660
            self.assertAlmostEqual(sx, sy, delta=0.01)

    def test_font_selection_keeps_seed_options_and_returns_to_parent(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'INI').mkdir()
            m = self.model(root)
            seed = m.seed
            options = json.dumps(m.options, sort_keys=True)
            m.page = 'slots'
            m.focus = 6
            m.key(13)
            self.assertEqual(m.page, 'appearance')
            m.focus = 2
            m.key(13)
            self.assertEqual(load(root), 'large')
            m.focus = 3
            m.key(13)
            self.assertEqual((m.page, m.focus), ('slots', 6))
            self.assertEqual(m.seed, seed)
            self.assertEqual(json.dumps(m.options, sort_keys=True), options)
            self.assertIsNone(m.requested_slot)

    def test_resized_mouse_click_selects_same_button(self):
        m = self.model()
        m.page = 'new'
        m.presentation = viewport('new', (640, 480))
        src, dst = m.presentation
        l, t, r, b = dict(controls(m))[10]
        x = (l + r) / 2
        y = (t + b) / 2
        x = dst[0] + (x - src[0]) * (dst[2] - dst[0]) / (src[2] - src[0])
        y = dst[1] + (y - src[1]) * (dst[3] - dst[1]) / (src[3] - src[1])
        m.event(5, x, y)
        self.assertEqual(m.focus, 10)
        m.event(3, x, y)
        self.assertEqual(m.page, 'appearance')

    def test_size_events_validate_dimensions(self):
        m = self.model()
        m.event(7, 640, 480)
        self.assertEqual(m.display_size, (640, 480))
        m.event(7, 0, 0)
        self.assertEqual(m.display_size, (640, 480))


if __name__ == '__main__':
    unittest.main()
