"""Input geometry and animation independence for the original-style presentation."""

import copy
import tempfile
import unittest
from pathlib import Path
from native_menu import layout
from native_menu.model import Model
from native_menu.render import Renderer
from native_menu.transport import Mailbox, read, write
from menu_host.store import Store


class AppearanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.m = Model(Store(self.folder, runs=self.folder / "runs"))

    def tearDown(self):
        self.tmp.cleanup()

    def click(self, page, index):
        self.m.go(page)
        x, y, r, b = layout.row_rect(page, index)
        self.m.key(1000, (x + r) // 2, (y + b) // 2)

    def test_native_mouse_matches_save_buttons_and_action_cards(self):
        for i in range(3):
            self.click("home", i)
            self.assertEqual(self.m.slot, i + 1)
            self.assertIsNone(self.m.action)
        self.click("home", 6)
        self.assertEqual(self.m.page, "settings")
        self.click(
            "settings",
            next(i for i, row in enumerate(self.m.rows()) if row.key == "gameplay"),
        )
        self.assertEqual(self.m.page, "gameplay")
        seed = self.m.draft.seed
        self.click("gameplay", 0)
        self.assertTrue(self.m.draft.options["extras"]["god_mode"])
        self.assertNotEqual(seed, self.m.draft.seed)
        self.m.key(1000, 50, 215)
        self.assertEqual(self.m.page, "settings")
        self.click("home", 3)
        self.assertEqual(self.m.action, "new")

    def test_illustrations_and_gaps_are_not_controls(self):
        before = copy.deepcopy(self.m.draft.options)
        for xy in [
            (320, 90),
            (68, 170),
            (150, 250),
            (300, 370),
            (400, 335),
            (600, 470),
        ]:
            self.m.key(1000, *xy)
            self.assertEqual(self.m.page, "home")
            self.assertIsNone(self.m.action)
        self.assertEqual(self.m.draft.options, before)
        self.m.go("gameplay")
        self.m.key(1000, 600, 220)
        self.assertEqual(self.m.offset, 8)
        self.assertEqual(self.m.visible()[0].key, "no_screen_shaking")

    def test_animation_preserves_seed_options_focus_and_input_ack(self):
        r = Renderer(self.folder)
        m = self.m
        m.draft.seed = "B05A2026"
        before = copy.deepcopy(m.draft.options)
        mail = Mailbox(self.folder, r, m)
        state = (self.folder / "native-state.json").read_bytes()
        frame = (self.folder / "native-panel.png").read_bytes()
        mail.publish(5, state=False)
        self.assertEqual((self.folder / "native-state.json").read_bytes(), state)
        self.assertEqual((self.folder / "native-panel.png").read_bytes(), frame)
        self.assertEqual(m.draft.seed, "B05A2026")
        self.assertEqual(m.draft.options, before)
        self.assertEqual(read(self.folder / "native-view.ini")["ack"], 0)
        write(self.folder / "native-input.ini", dict(Sequence=1, Key=40))
        self.assertTrue(mail.poll())
        self.assertEqual(m.focus, 1)
        self.assertEqual(mail.step, 5)
        self.assertFalse(mail.poll())
        self.assertEqual(read(self.folder / "native-view.ini")["ack"], 1)
