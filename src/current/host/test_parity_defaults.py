"""Previously missing first-use defaults and persistent readable menu text."""

import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw
from menu_host.store import Store
from menu_host.draft import Draft
from native_menu.classic import ClassicModel, ClassicRenderer
from native_menu.preferences import save_preferences
from native_menu import layout
from native_menu.help import wrapped
from native_menu.help_labels import TEXT


class ParityDefaultsTests(unittest.TestCase):
    def test_first_use_spider_and_saved_opt_out_and_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "profile", runs=Path(tmp) / "runs")
            m = ClassicModel(store)
            self.assertTrue(m.draft.options["extras"]["spider"])
            m.go("gameplay")
            m.select("spider")
            self.assertFalse(m.draft.options["extras"]["spider"])
            self.assertFalse(ClassicModel(store).draft.options["extras"]["spider"])
            m.fresh_draft()
            self.assertFalse(m.draft.options["extras"]["spider"])
            imported = Draft()
            imported.update(spider=True)
            m.draft.import_seed(imported.shared())
            self.assertTrue(m.draft.options["extras"]["spider"])
            self.assertFalse(ClassicModel(store).draft.options["extras"]["spider"])

    def test_large_text_mouse_keyboard_persistence_and_seed_independence(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(Path(tmp) / "profile", runs=Path(tmp) / "runs")
            m = ClassicModel(store)
            renderer = ClassicRenderer(Path(tmp) / "art")
            original = m.draft.shared()
            m.go("tools")
            m.focus = next(i for i, r in enumerate(m.rows()) if r.key == "font_size")
            m.key(13)
            self.assertEqual(m.font_size, "large")
            self.assertEqual(m.draft.shared(), original)
            self.assertEqual(ClassicModel(store).font_size, "large")
            draw = ImageDraw.Draw(Image.new("RGBA", (640, 480)))
            for index, language in enumerate(("de", "en", "es", "ru", "ja")):
                m.language = language
                fonts = renderer.fonts(language, "large")
                self.assertEqual(fonts[11].size, 13)
                for translations in TEXT.values():
                    self.assertLessEqual(
                        len(
                            wrapped(draw, translations[index], fonts[11], 580, language)
                        ),
                        4,
                    )
                for page in (
                    "settings",
                    "loadout",
                    "gameplay",
                    "cosmetics",
                    "tools",
                    "seed",
                    "character_picker",
                ):
                    m.go(page)
                    self.assertEqual(renderer.render(m).size, (640, 480))
            m.go("tools")
            i = next(i for i, r in enumerate(m.rows()) if r.key == "font_size")
            x, y, r, b = layout.row_rect(m.page, i)
            m.key(1000, x + 40, y + 8)
            self.assertEqual(m.font_size, "normal")
            self.assertEqual(m.draft.shared(), original)
            save_preferences(store.root, font_size="broken")
            self.assertEqual(ClassicModel(store).font_size, "normal")
