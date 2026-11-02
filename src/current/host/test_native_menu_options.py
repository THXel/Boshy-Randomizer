"""Boundary regressions for every native menu value and recoverable UI errors."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock
from native_menu.model import Model, GRAPHICS, LANGUAGES, DIM_LEVELS
from native_menu.controller import Controller
from menu_host.store import Store
from menu_host.draft import validate
from run_settings import decode


class OptionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.m = Model(Store(self.folder, runs=self.folder / "runs"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_each_graphics_option_both_directions_preserves_a_valid_seed(self):
        self.m.go("cosmetics")
        for key in GRAPHICS:
            for direction in (1, -1):
                for _ in range(5):
                    before = self.m.draft.seed
                    self.m.select(key, direction)
                    self.assertNotEqual(self.m.draft.seed, before, key)
                    seed, options = decode(self.m.draft.shared())
                    self.assertEqual(seed, self.m.draft.seed)
                    self.assertEqual(options, validate(self.m.draft.options))
        self.assertIn(self.m.draft.options["extras"]["sprite_dim"], DIM_LEVELS)

    def test_dim_wraps_in_both_directions(self):
        self.m.go("cosmetics")
        for expected in (40, 60, 0, 20):
            self.m.select("sprite_dim")
            self.assertEqual(self.m.draft.options["extras"]["sprite_dim"], expected)
        for expected in (0, 60, 40, 20):
            self.m.select("sprite_dim", -1)
            self.assertEqual(self.m.draft.options["extras"]["sprite_dim"], expected)

    def test_last_station_cannot_be_removed_and_message_is_localized(self):
        self.m.draft.update(
            level_pool=["save1.ini"], level_count=1, boss_pool=[], route_boss_count=0
        )
        self.m.go("levels")
        seed = self.m.draft.seed
        for language in LANGUAGES:
            self.m.language = language
            self.m.select("level_pool:save1.ini")
            self.assertEqual(self.m.draft.seed, seed)
            self.assertEqual(self.m.message, self.m.t("route_required"))
            self.assertEqual(self.m.draft.options["level_pool"], ["save1.ini"])
        self.m.go("route")
        for key in ("level_count", "route_boss_count"):
            for direction in (1, -1):
                self.m.select(key, direction)
                validate(self.m.draft.options)
        self.assertEqual(self.m.draft.seed, seed)

    def controller(self):
        # No game/export needed to exercise clipboard errors and transactional imports.
        c = Controller.__new__(Controller)
        c.model = self.m
        c.folder = self.folder
        c.clipboard = Mock()
        c.mail = Mock()
        return c

    def test_clipboard_failure_is_localized_and_logged_without_losing_draft(self):
        c = self.controller()
        c.clipboard.put.side_effect = RuntimeError("test clipboard disconnected")
        for lang in LANGUAGES:
            self.m.language = lang
            before = self.m.draft.shared()
            c.action("copy")
            self.assertEqual(self.m.message, self.m.t("clipboard_failed"))
            self.assertEqual(self.m.draft.shared(), before)
        self.assertEqual(
            json.loads((self.folder / "native-error.json").read_text())["operation"],
            "copy",
        )

    def test_invalid_import_preserves_seed_and_options(self):
        c = self.controller()
        c.clipboard.get.return_value = "not-a-seed"
        before = self.m.draft.shared()
        for lang in LANGUAGES:
            self.m.language = lang
            c.action("import")
            self.assertEqual(self.m.draft.shared(), before)
            self.assertEqual(self.m.message, self.m.t("invalid_seed"))

    def test_valid_import_restores_every_encoded_option(self):
        c = self.controller()
        self.m.go("cosmetics")
        self.m.select("sprite_dim")
        self.m.select("music")
        expected = copy.deepcopy(self.m.draft.options)
        code = self.m.draft.shared()
        self.m.select("sprite_actors")
        c.clipboard.get.return_value = code
        c.action("import")
        self.assertEqual(self.m.draft.options, expected)
        self.assertEqual(self.m.draft.shared(), code)
        self.assertEqual(self.m.message, "")
