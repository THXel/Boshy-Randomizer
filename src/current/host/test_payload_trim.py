"""Ship only the menu helpers imported by the native launcher."""

import tempfile
import unittest
from pathlib import Path
from distribution.payload import stage, SHARED_MENU_FILES, LEGACY_HOST_FILES
from app_paths import LAB, REPO


class PayloadTrimTests(unittest.TestCase):
    def test_native_payload_excludes_retired_gui_and_keeps_shared_helpers(self):
        with tempfile.TemporaryDirectory() as t:
            root = stage(LAB, REPO, Path(t) / "payload")
            self.assertEqual(
                {p.name for p in (root / "shared/src/python/menu").iterdir()},
                set(SHARED_MENU_FILES),
            )
            self.assertTrue(
                all(not (root / "app" / name).exists() for name in LEGACY_HOST_FILES)
            )
            for name in (
                "native_menu/help.py",
                "native_menu/labels.py",
                "native_menu/presets.py",
                "gameplay/dresser.py",
                "platform_support/name_dialog.py",
            ):
                self.assertTrue((root / "app" / name).is_file())
