"""Persistent-process slot switching must never mix saves or asset banks."""

import tempfile
import unittest
from pathlib import Path
from functools import partial
from menu_host.store import Store, digest
from menu_host.draft import Draft
from export_native_run import export
from native_menu.classic import BASE_SHA
from native_menu.session_store import WorkingSession


class CombinedSessionTests(unittest.TestCase):
    def test_truncated_working_options_never_replace_saved_options(self):
        from native_menu.display import prepare_options, Settings

        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            store = Store(
                root / "p", root / "runs", exporter=partial(export, dynamic=True)
            )
            with store.lock():
                store.create(1, Draft())
                target = store.folder(1)
                prepare_options(target, Settings())
                expected = (target / "options.ini").read_bytes()
                folder = root / "working"
                folder.mkdir()
                session = WorkingSession(folder, store, BASE_SHA)
                session.stage(1)
                (folder / "options.ini").write_bytes(b"")
                with self.assertRaisesRegex(ValueError, "could not be validated"):
                    session.commit()
                self.assertEqual((target / "options.ini").read_bytes(), expected)
                self.assertTrue(session.marker.exists())
                (folder / "options.ini").write_bytes(expected)
                session.commit()
                self.assertEqual((target / "options.ini").read_bytes(), expected)
                self.assertFalse(session.marker.exists())

    def test_two_slots_commit_only_the_bound_save_and_reject_cross_slot_data(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            store = Store(
                root / "p", runs=root / "runs", exporter=partial(export, classic=True)
            )
            with store.lock():
                for slot, mode, seed in [
                    (1, "normal", "12345678"),
                    (2, "target", "ABCDEF12"),
                ]:
                    draft = Draft()
                    draft.set_mode(mode)
                    draft.seed = seed
                    draft.update(no_mouse_ghost=True)
                    store.create(slot, draft)
                folder = root / "working"
                folder.mkdir()
                session = WorkingSession(folder, store, BASE_SHA)
                hashes = {s: digest(store.folder(s) / "SaveFile1.ini") for s in (1, 2)}
                session.stage(2)
                self.assertEqual(digest(folder / "SaveFile1.ini"), hashes[2])
                store.active = 2
                session.commit()
                store.active = None
                self.assertFalse(session.marker.exists())
                self.assertEqual(digest(store.folder(1) / "SaveFile1.ini"), hashes[1])
                session.stage(2)
                (folder / "SaveFile1.ini").write_bytes(
                    (store.folder(1) / "SaveFile1.ini").read_bytes()
                )
                with self.assertRaisesRegex(ValueError, "could not be validated"):
                    session.commit()
                self.assertTrue(session.marker.exists())
                self.assertEqual(digest(store.folder(2) / "SaveFile1.ini"), hashes[2])
                with self.assertRaisesRegex(RuntimeError, "recovered"):
                    session.stage(1)

    def test_different_asset_bank_is_rejected_before_working_save_changes(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            store = Store(
                root / "p", runs=root / "r", exporter=partial(export, classic=True)
            )
            with store.lock():
                d = Draft()
                store.create(1, d)
                folder = root / "w"
                folder.mkdir()
                sentinel = folder / "SaveFile1.ini"
                sentinel.write_bytes(b"keep")
                session = WorkingSession(folder, store, "wrong bank")
                with self.assertRaisesRegex(ValueError, "asset bank"):
                    session.stage(1)
                self.assertEqual(sentinel.read_bytes(), b"keep")
                self.assertFalse(session.marker.exists())


class InterruptedSessionTests(unittest.TestCase):
    def test_recovery_validates_before_restoring_only_the_bound_slot(self):
        import json, uuid

        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            s = Store(root / "p", root / "runs", exporter=partial(export, classic=True))
            with s.lock():
                d = Draft()
                s.create(1, d)
                working = s.runs / ("rebuilt-menu-" + uuid.uuid4().hex)
                working.mkdir()
                session = WorkingSession(working, s, BASE_SHA)
                session.stage(1)
                original = digest(s.folder(1) / "SaveFile1.ini")
                self.assertEqual(
                    WorkingSession.recover(s), dict(slot=1, recovered=True)
                )
                self.assertEqual(digest(s.folder(1) / "SaveFile1.ini"), original)
                self.assertIsNone(WorkingSession.recover(s))
                session = WorkingSession(working, s, BASE_SHA)
                session.stage(1)
                (working / "SaveFile1.ini").write_bytes(b"partial write")
                with self.assertRaisesRegex(ValueError, "validated"):
                    WorkingSession.recover(s)
                self.assertTrue(session.marker.exists())
                self.assertEqual(digest(s.folder(1) / "SaveFile1.ini"), original)
                journal = json.loads(session.marker.read_text())
                journal["phase"] = "staging"
                session.marker.write_text(json.dumps(journal))
                self.assertEqual(
                    WorkingSession.recover(s),
                    dict(slot=1, recovered=False, unstarted=True),
                )
                self.assertEqual(digest(s.folder(1) / "SaveFile1.ini"), original)


if __name__ == "__main__":
    unittest.main()
