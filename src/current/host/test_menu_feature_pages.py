"""User-facing menu navigation, seed stability and supported presets."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from native_menu.classic import ClassicModel, ClassicRenderer
from native_menu.layout import row_rect, hit
from menu_host.store import Store
from gameplay.characters import CHOICES


class FeaturePagesTests(unittest.TestCase):
    def model(self, path):
        return ClassicModel(Store(Path(path) / "profile", runs=Path(path) / "runs"))

    def test_portrait_navigation_does_not_commit_until_confirmed(self):
        with tempfile.TemporaryDirectory() as t:
            m = self.model(t)
            m.go("loadout")
            m.select("start_character")
            self.assertEqual(m.page, "character_picker")
            seed = m.draft.seed
            next_choice = (CHOICES.index(m.draft.options["start_character"]) + 1) % len(
                CHOICES
            )
            m.key(39)
            self.assertEqual(m.draft.seed, seed)
            self.assertEqual(m.focus, next_choice)
            m.key(13)
            self.assertEqual(m.page, "loadout")
            self.assertEqual(m.draft.options["start_character"], CHOICES[next_choice])
            self.assertNotEqual(m.draft.seed, seed)
            for i in range(8):
                x, y, _, _ = row_rect("character_picker", i)
                self.assertEqual(hit("character_picker", 8, x + 10, y + 10), i)

    def test_preview_is_read_only_and_presets_keep_mode_and_target_counts(self):
        with tempfile.TemporaryDirectory() as t:
            m = self.model(t)
            before = m.draft.shared()
            m.go("preview")
            self.assertGreater(len(m.rows()), 1)
            m.key(13)
            m.key(34)
            m.key(27)
            self.assertEqual(m.draft.shared(), before)
            for mode in ("normal", "target", "boss_rush", "level_rush", "randomizer"):
                m.draft.set_mode(mode)
                m.draft.update(target_count=9, boss_count=3)
                m.go("presets")
                m.select("preset:training")
                self.assertEqual(m.draft.options["mode"], mode)
                self.assertEqual(m.draft.options["target_count"], 9)
                self.assertEqual(m.draft.options["boss_count"], 3)
                for key in (
                    "god_mode",
                    "one_hp",
                    "autofire",
                    "skip_intro",
                    "fast_chests",
                ):
                    self.assertTrue(m.draft.options["extras"][key])
            m.store.current = Mock(return_value={"run": "saved"})
            m.go("presets")
            before = m.draft.shared()
            m.select("preset:standard")
            self.assertEqual(before, m.draft.shared())

    def test_chaos_uses_migrated_rules_and_preserves_personal_spider_choice(self):
        from menu_host.draft import Draft

        for mode in ("randomizer", "normal", "target", "boss_rush", "level_rush"):
            for spider in (False, True):
                with self.subTest(mode=mode, spider=spider):
                    d = Draft()
                    d.set_mode(mode)
                    d.update(spider=spider)
                    before = d.seed
                    d.apply_preset("chaos")
                    self.assertNotEqual(before, d.seed)
                    self.assertEqual(d.options["mode"], mode)
                    self.assertTrue(d.options["characters"])
                    self.assertTrue(d.options["extras"]["death_character"])
                    self.assertEqual(d.options["extras"]["shot_mode"], "death_and_spot")
                    self.assertEqual(d.options["extras"]["spider"], spider)
                    imported = Draft()
                    imported.import_seed(d.shared())
                    self.assertEqual(imported.options, d.options)

    def test_new_pages_render_in_all_five_languages(self):
        with tempfile.TemporaryDirectory() as t:
            m = self.model(t)
            r = ClassicRenderer(t)
            for language in ("de", "en", "es", "ru", "ja"):
                m.language = language
                for page in ("character_picker", "preview", "presets"):
                    m.go(page)
                    image = r.render(m)
                    self.assertEqual(image.size, (640, 480))
                    self.assertEqual(image.getpixel((300, 100))[3], 0)


if __name__ == "__main__":
    unittest.main()
