"""Navigation contracts for a compact mouse and keyboard menu."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from menu_host.store import Store
from native_menu.classic import ClassicModel, ClassicRenderer
from native_menu import layout


class CompactMenuTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.m = ClassicModel(Store(root / "profile", runs=root / "runs"))

    def test_categories_retain_every_option_and_parent_focus(self):
        m = self.m
        m.go("settings")
        self.assertEqual(
            [r.key for r in m.rows()],
            [
                "new",
                "seed",
                "route",
                "loadout",
                "gameplay",
                "cosmetics",
                "preview",
                "tools",
            ],
        )
        for index, category in enumerate(m.rows()[2:], 2):
            m.focus = index
            m.key(13)
            self.assertEqual(m.page, category.key)
            m.key(27)
            self.assertEqual((m.page, m.focus), ("settings", index))
        for child, parent in layout.PARENTS.items():
            m.go(child)
            m.key(27)
            self.assertEqual(m.page, parent)

    def test_spatial_navigation_and_tab_cover_partial_pages_without_editing(self):
        m = self.m
        for page in (
            "settings",
            "route",
            "loadout",
            "gameplay",
            "character_picker",
            "levels",
            "bosses",
            "tools",
            "updates",
        ):
            m.go(page)
            before = m.draft.shared()
            seen = set()
            for _ in m.rows():
                seen.add(m.focus)
                m.key(9)
                self.assertIn(m.rows()[m.focus], m.visible())
            self.assertEqual(seen, set(range(len(m.rows()))))
            for key in (37, 38, 39, 40):
                for _ in m.rows():
                    m.key(key)
                    self.assertIn(m.rows()[m.focus], m.visible())
            self.assertEqual(m.draft.shared(), before)
        m.go("loadout")
        m.focus = 0
        m.key(40)
        self.assertEqual(m.focus, 2)
        m.key(40)
        self.assertEqual(m.focus, 0)
        m.key(39)
        m.key(40)
        self.assertEqual(m.focus, 3)

    def test_mouse_adjustments_match_keyboard_and_locked_settings_do_not_change(self):
        m = self.m
        m.go("route")
        m.focus = next(i for i, r in enumerate(m.rows()) if r.key == "difficulty")
        original = m.draft.options["difficulty"]
        m.key(107)
        self.assertEqual(m.draft.options["difficulty"], (original + 1) % 4)
        a, b, c, d = layout.adjust_rect(m.page, m.focus, -1)
        m.key(1000, (a + c) // 2, (b + d) // 2)
        self.assertEqual(m.draft.options["difficulty"], original)
        m.key(189)
        self.assertEqual(m.draft.options["difficulty"], (original - 1) % 4)
        a, b, c, d = layout.adjust_rect(m.page, m.focus, 1)
        m.key(1000, (a + c) // 2, (b + d) // 2)
        self.assertEqual(m.draft.options["difficulty"], original)
        m.store.current = Mock(return_value={"run": "saved"})
        before = m.draft.shared()
        for key in (13, 32, 107, 109, 187, 189):
            m.key(key)
        m.key(1000, (a + c) // 2, (b + d) // 2)
        self.assertEqual(m.draft.shared(), before)

    def test_hover_click_and_keyboard_share_card_geometry(self):
        m = self.m
        m.go("gameplay")
        for index in range(len(m.rows())):
            m.focus = index
            m.visible()
            a, b, c, d = layout.row_rect(m.page, index % layout.PAGE_SIZE)
            before = m.draft.shared()
            m.key(1001, (a + c) // 2, (b + d) // 2)
            self.assertEqual(m.focus, index)
            self.assertEqual(m.draft.shared(), before)
            key = m.rows()[index].key
            was = m.draft.options["extras"][key]
            m.key(1000, (a + c) // 2, (b + d) // 2)
            self.assertIs(m.draft.options["extras"][key], not was)
            m.key(32)
            self.assertIs(m.draft.options["extras"][key], was)

    def test_paging_wraps_and_reaches_last_character_using_mouse(self):
        m = self.m
        m.go("character_picker")
        count = len(m.rows())
        m.key(1000, 510, 215)
        self.assertEqual(m.focus, (count - 1) // 8 * 8)
        index = len(m.visible()) - 1
        selected = m.visible()[index].key.split(":", 1)[1]
        a, b, c, d = layout.row_rect(m.page, index)
        m.key(1000, (a + c) // 2, (b + d) // 2)
        self.assertEqual(m.draft.options["start_character"], selected)
        self.assertEqual(m.page, "loadout")

    def test_every_card_and_portrait_remains_inside_panel_in_all_languages(self):
        m = self.m
        renderer = ClassicRenderer(self.tmp.name)
        for lang in ("de", "en", "es", "ru", "ja"):
            m.language = lang
            for page in (
                "settings",
                "loadout",
                "route",
                "gameplay",
                "cosmetics",
                "shots",
                "tools",
                "seed",
                "character_picker",
                "updates",
                "levels",
                "bosses",
                "preview",
            ):
                m.go(page)
                for focus in range(0, len(m.rows()), layout.PAGE_SIZE):
                    m.focus = focus
                    image = renderer.render(m)
                    self.assertEqual(image.getpixel((635, 300))[3], 0)
                    for index in range(len(m.visible())):
                        a, b, c, d = layout.row_rect(page, index)
                        self.assertTrue(12 <= a < c <= 628 and 196 <= b < d <= 455)
                        self.assertEqual(
                            image.getpixel(((a + c) // 2, (b + d) // 2))[3], 255
                        )
