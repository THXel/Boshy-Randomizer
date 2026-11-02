"""Receipt-based previews, explicit toggles, native cleanup and new-run defaults."""

import configparser
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from menu_host.draft import Draft, BETA_BOSSES
from menu_host.store import Store
from native_menu.classic import ClassicModel
from native_menu.icons import row_art, assets
from gameplay.collections import collected
from distribution.progress import Reporter, Cancelled
from distribution import transaction, original
from distribution.identity import sha256
from distribution.import_errors import explanation, MESSAGES
from distribution.linux import language


class MenuPolishTests(unittest.TestCase):
    def test_new_run_omits_beta_but_explicit_selection_and_import_survive(self):
        d = Draft()
        self.assertFalse(BETA_BOSSES.intersection(d.options["boss_pool"]))
        for key in BETA_BOSSES:
            d.update(boss_pool=d.options["boss_pool"] + [key])
        restored = Draft()
        restored.import_seed(d.shared())
        self.assertEqual(restored.options, d.options)
        d.set_mode("boss_rush")
        self.assertTrue(BETA_BOSSES.issubset(d.options["boss_pool"]))
        fresh = Draft()
        fresh.set_mode("boss_rush")
        self.assertFalse(BETA_BOSSES.intersection(fresh.options["boss_pool"]))

    def test_empty_slots_do_not_discard_an_explicitly_imported_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = ClassicModel(Store(Path(tmp) / "p", runs=Path(tmp) / "r"))
            d = Draft()
            d.update(god_mode=True)
            m.draft.import_seed(d.shared())
            m.slot = 2
            m.load_slot()
            self.assertEqual(m.draft.shared(), d.shared())
            m.loaded_saved_slot = True
            m.slot = 3
            m.load_slot()
            self.assertFalse(BETA_BOSSES.intersection(m.draft.options["boss_pool"]))
            self.assertFalse(m.draft.options["extras"]["god_mode"])

    def test_boss_and_level_art_never_falls_back_to_a_generic_symbol(self):
        with tempfile.TemporaryDirectory() as tmp:
            m = ClassicModel(Store(Path(tmp) / "p", runs=Path(tmp) / "r"))
            for page in ("bosses", "levels"):
                m.go(page)
                for row in m.rows():
                    path = row_art(m, row)
                    self.assertIsNotNone(path, row.key)
                    self.assertTrue(path.is_file(), row.key)
                    self.assertNotEqual(
                        path, assets().files[assets().fallback], row.key
                    )

    def test_collection_receipts_do_not_grant_uncollected_rewards(self):
        save = configparser.ConfigParser()
        profile = configparser.ConfigParser()
        save.read_dict({"Collectables": {"Gastly": "1", "Rupees": "0"}})
        profile.read_dict({"Unlockables": {"Mario": "1", "Sonic": "0"}})
        items, chars = collected(save, profile)
        self.assertEqual([r["name"] for r in items if r["done"]], ["Gastly"])
        self.assertEqual([r["name"] for r in chars if r["done"]], ["Mario"])

    def test_installer_errors_and_controls_have_all_five_locales(self):
        import ast

        for source in (
            "distribution/linux/launcher.py",
            "distribution/linux/setup_window.py",
        ):
            for node in ast.walk(ast.parse(Path(source).read_text())):
                if (
                    isinstance(node, ast.Call)
                    and (
                        getattr(node.func, "id", "") == "tr"
                        or getattr(node.func, "attr", "") == "tr"
                    )
                    and len(node.args) == 2
                    and all(isinstance(a, ast.Constant) for a in node.args)
                ):
                    self.assertIn(node.args[1].value, language.TEXT)
        for code in MESSAGES:
            self.assertEqual(len(MESSAGES[code]), 5, code)
        for lang in ("german", "english", "spanish", "russian", "japanese"):
            self.assertTrue(explanation(Cancelled(), lang))

    def test_cancel_at_verification_cleans_staging_and_preserves_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            game = source / original.ORIGINAL_NAME
            game.write_bytes(b"original")
            patched = root / "patched"
            patched.write_bytes(b"patched")
            kwargs = dict(expected_source=sha256(game))
            transaction.install(
                source,
                root / "app",
                "v1",
                sha256(patched),
                lambda s, d: d.write_bytes(b"patched"),
                **kwargs
            )
            before = (root / "app/active.json").read_bytes()
            flag = root / "stop"
            reporter = Reporter(io.StringIO(), cancel_file=flag)

            def progress(stage, current=0, total=0):
                if stage == "verifying":
                    flag.touch()
                reporter(stage, current, total)

            with self.assertRaises(Cancelled):
                transaction.install(
                    source,
                    root / "app",
                    "v2",
                    sha256(patched),
                    lambda s, d: d.write_bytes(b"patched"),
                    progress=progress,
                    **kwargs
                )
            self.assertEqual(before, (root / "app/active.json").read_bytes())
            self.assertFalse((root / "app/versions/v2").exists())
            self.assertEqual(list((root / "app").glob(".install-*")), [])
