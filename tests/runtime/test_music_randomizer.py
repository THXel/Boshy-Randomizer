import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import music_randomizer as music
import run_extras as extras
import run_settings as settings
import seed_share
from test_compact_seeds import options


class Music(unittest.TestCase):
    def test_deterministic_combined_permutation_without_self_swaps(self):
        a = music.mapping('same')
        self.assertEqual(a, music.mapping('same'))
        self.assertNotEqual(a, music.mapping('different'))
        self.assertEqual(set(a), set(music.SOURCE_TRACKS))
        self.assertEqual(set(a.values()), set(music.TRACKS))
        self.assertTrue(all(k != v for k, v in a.items()))

    def test_excluded_song_is_never_a_replacement_but_its_original_cue_is_handled(self):
        for seed in ('8080DDD1', 'same', 'different'):
            swaps = music.mapping(seed)
            self.assertIn('Do teh mario!', swaps)
            self.assertNotIn('Do teh mario!', swaps.values())
            allowed = [swaps[name] for name in music.TRACKS]
            self.assertEqual(len(set(allowed)), len(music.TRACKS))

    def test_music_and_shots_have_distinct_flags(self):
        o = options()
        self.assertFalse(o['extras']['music'])
        before = extras.flags(o)
        o['extras']['music'] = True
        self.assertEqual(extras.flags(o) ^ before, 4096)
        o['extras']['shot_mode'] = 'spot'
        self.assertEqual(extras.flags(o) ^ before, 4096 | 2048)

    def test_new_setting_is_shared_without_changing_route(self):
        o = options()
        before = settings.route('MUSIC', o)
        o['extras']['music'] = True
        code = seed_share.encode('MUSIC', o, ROOT)
        self.assertEqual(settings.decode(code), ('MUSIC', settings.normalize(o)))
        self.assertEqual(settings.route('MUSIC', o), before)

    def test_old_music_seed_formats_are_rejected(self):
        for code in ('BR3-ARI0q80AZSwBuA', 'BR4-ARI0q80AGVBuhw'):
            with self.assertRaises(ValueError):
                settings.decode(code)

    def test_old_versions_cannot_smuggle_new_option(self):
        for version in (1, 2, 3):
            e = extras.defaults()
            e['version'] = version
            with self.assertRaises(ValueError):
                extras.normalize(e)

    def test_localized_compact_hack_controls_do_not_overlap(self):
        import ui_i18n
        from menu_controls import controls
        from types import SimpleNamespace

        rows = controls(SimpleNamespace(page='extras'))
        for a, b in zip(rows, rows[1:]):
            self.assertLess(a[1][3], b[1][1])
        for lang in ui_i18n.SUPPORTED:
            for text in extras.EXTRAS[-1][1:3]:
                self.assertIn(text, ui_i18n.catalog(lang))


if __name__ == '__main__':
    unittest.main()
