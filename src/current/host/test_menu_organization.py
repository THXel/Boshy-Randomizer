"""Defaults, category ownership and the setup-window handoff."""

import queue
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock

from menu_host.draft import Draft, SUPPORTED
from menu_host.store import Store
from native_menu.classic import ClassicModel
from native_menu import layout
from distribution.linux.setup_window import SetupWindow


class OrganizationTests(unittest.TestCase):
    def model(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return ClassicModel(Store(Path(tmp.name) / "p", runs=Path(tmp.name) / "r"))

    def test_fresh_defaults_and_explicit_seed_settings(self):
        m = self.model()
        self.assertEqual(m.draft.options["difficulty"], 1)
        self.assertEqual(m.draft.options["start_character"], "Dark Boshy")
        d = Draft()
        d.update(difficulty=3, start_character="Luigi")
        m.draft.import_seed(d.shared())
        self.assertEqual(m.draft.options["difficulty"], 3)
        self.assertEqual(m.draft.options["start_character"], "Luigi")
        m.fresh_draft()
        self.assertEqual(m.draft.options["difficulty"], 1)
        self.assertEqual(m.draft.options["start_character"], "Dark Boshy")

    def test_seed_has_one_entry_and_both_back_inputs_return_to_its_card(self):
        m = self.model()
        m.go("tools")
        self.assertNotIn("seed", [r.key for r in m.rows()])
        for key, x, y in [(27, 0, 0), (1000, 50, 215)]:
            m.go("settings")
            m.focus = next(i for i, r in enumerate(m.rows()) if r.key == "seed")
            index = m.focus
            m.key(13)
            self.assertEqual(m.page, "seed")
            m.key(key, x, y)
            self.assertEqual((m.page, m.focus), ("settings", index))

    def test_character_death_option_moves_and_stays_operable_and_lockable(self):
        m = self.model()
        m.go("gameplay")
        self.assertNotIn("death_character", [r.key for r in m.rows()])
        m.go("loadout")
        m.focus = next(i for i, r in enumerate(m.rows()) if r.key == "death_character")
        seed = m.draft.seed
        m.key(13)
        self.assertTrue(m.draft.options["extras"]["death_character"])
        self.assertNotEqual(seed, m.draft.seed)
        x, y, right, bottom = layout.row_rect(m.page, m.focus)
        m.key(1000, (x + right) // 2, (y + bottom) // 2)
        self.assertFalse(m.draft.options["extras"]["death_character"])
        m.store.current = Mock(return_value={"saved": True})
        before = m.draft.shared()
        m.key(13)
        self.assertEqual(m.draft.shared(), before)

    def test_every_extra_is_present_once_across_categories_in_all_languages(self):
        m = self.model()
        for lang in ("de", "en", "es", "ru", "ja"):
            m.language = lang
            keys = []
            for page in ("gameplay", "loadout", "cosmetics"):
                m.go(page)
                rows = m.rows()
                self.assertTrue(all(r.label for r in rows))
                keys += [r.key for r in rows]
            for extra in SUPPORTED:
                self.assertEqual(keys.count(extra), 1, (lang, extra))

    def fake_window(self):
        w = SetupWindow.__new__(SetupWindow)
        w.tr = lambda de, en: en
        w.window = Mock()
        w.events = queue.Queue()
        w.started = time.monotonic()
        w.running = True
        w.delegated = False
        w.mode = "setup"
        for name in (
            "bar",
            "text",
            "detail",
            "hint",
            "elapsed",
            "close",
            "retry",
            "log_button",
            "launch_option",
        ):
            setattr(w, name, Mock())
        return w

    def test_helper_hides_during_installer_and_returns_on_all_terminal_results(self):
        for kind, value in [("done", "7"), ("error", "failure"), ("cancelled", None)]:
            w = self.fake_window()
            w.events.put(("progress", ("wizard", 0, 0)))
            w.poll()
            w.window.withdraw.assert_called_once()
            w.window.deiconify.assert_not_called()
            self.assertTrue(w.delegated)
            w.events.put((kind, value))
            w.poll()
            w.window.deiconify.assert_called_once()
            self.assertFalse(w.running)
            if kind == "done":
                w.launch_option.pack.assert_called_once()

    def test_registration_restores_helper_after_installer(self):
        w = self.fake_window()
        w.events.put(("progress", ("wizard", 0, 0)))
        w.events.put(("progress", ("registration", 0, 0)))
        w.poll()
        w.window.withdraw.assert_called_once()
        w.window.deiconify.assert_called_once()
