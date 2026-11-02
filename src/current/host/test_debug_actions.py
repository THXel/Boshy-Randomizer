"""Diagnostic edits must be isolated, reversible and visibly noncompetitive."""

import json
import tempfile
import unittest
from functools import partial
from pathlib import Path
from unittest.mock import patch
from menu_host.store import Store, save
from menu_host.draft import Draft
from export_native_run import export
from native_menu import debug_actions as debug
from transition.router import GROUP, STAGES


class DebugActionTests(unittest.TestCase):
    def test_test_copy_grants_teleport_and_restore_preserve_original_and_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(
                Path(tmp) / "p",
                runs=Path(tmp) / "r",
                exporter=partial(export, dynamic=True),
            )
            with store.lock():
                draft = Draft()
                draft.set_mode("target")
                draft.update(characters=True)
                store.create(1, draft)
                original = store.current(1)
                folder = store.folder(1)
                before = {
                    n: (folder / n).read_bytes()
                    for n in ("SaveFile1.ini", "onlineLicense.ini", "plan.json")
                }
                seed = draft.shared()
                debug.prepare(store, 1, "item", "Awesomesauce")
                testfolder, p, c = store.resume(1)
                self.assertEqual(p["shared_seed"], seed)
                self.assertEqual(c.getint("Collectables", "Awesomesauce"), 1)
                self.assertEqual(c.getint(debug.MARKER, "Enabled"), 1)
                self.assertEqual(store.current(1)["debug_original"], original)
                for n, data in before.items():
                    self.assertEqual((folder / n).read_bytes(), data)
                self.assertNotEqual(folder, testfolder)
                debug.prepare(store, 1, "character", "Orc")
                self.assertEqual(
                    save(store.folder(1) / "onlineLicense.ini").getint(
                        "Unlockables", "Orc"
                    ),
                    1,
                )
                spot = "save9.ini"
                debug.prepare(store, 1, "teleport", spot)
                _, p, c = store.resume(1)
                self.assertEqual(c.getint(GROUP, "CurrentStage"), STAGES[spot]["id"])
                self.assertEqual(c.getint("Positions", "frame"), STAGES[spot]["frame"])
                self.assertEqual(c.getint("Positions", "xpos"), STAGES[spot]["x"])
                pointer = store.pointer(1).read_bytes()
                for op, value in [
                    ("teleport", "boss_solgryn.ini"),
                    ("item", "fake"),
                    ("victory", "Solgryn"),
                ]:
                    with self.assertRaises(ValueError):
                        debug.prepare(store, 1, op, value)
                    self.assertEqual(store.pointer(1).read_bytes(), pointer)
                store.active = 1
                with self.assertRaises(RuntimeError):
                    debug.prepare(store, 1, "item", "Gastly")
                store.active = None
                debug.restore(store, 1)
                self.assertEqual(store.current(1), original)
                for n, data in before.items():
                    self.assertEqual((folder / n).read_bytes(), data)

    def test_validation_failure_never_commits_or_keeps_partial_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Store(
                Path(tmp) / "p",
                runs=Path(tmp) / "r",
                exporter=partial(export, dynamic=True),
            )
            with store.lock():
                store.create(1, Draft())
                pointer = store.pointer(1).read_bytes()
                folders = set(store.runs.iterdir())
                validate = store.validate_folder
                calls = 0

                def reject_copy(folder, meta):
                    nonlocal calls
                    calls += 1
                    if calls > 1:
                        raise ValueError("simulated validation failure")
                    return validate(folder, meta)

                with patch.object(store, "validate_folder", side_effect=reject_copy):
                    with self.assertRaises(ValueError):
                        debug.prepare(store, 1, "item", "Gastly")
                self.assertEqual(store.pointer(1).read_bytes(), pointer)
                self.assertEqual(set(store.runs.iterdir()), folders)

    def test_recording_is_bounded_and_labels_are_complete(self):
        from native_menu.diagnostics import Diagnostics, TEXT
        from types import SimpleNamespace

        d = Diagnostics(SimpleNamespace())
        d.recording = True
        d.record_started = 100
        d.record_last = 0
        state = dict(
            phase="playing",
            frame="Example",
            slot=1,
            seed="ABC",
            recent_transitions=[],
            recent_errors=[],
        )
        with patch("native_menu.diagnostics.snapshot", return_value=state):
            for tick in range(100, 705):
                with patch("native_menu.diagnostics.time.monotonic", return_value=tick):
                    d.record_tick()
        self.assertFalse(d.recording)
        self.assertEqual(len(d.recorded), 600)
        for labels in TEXT.values():
            self.assertEqual(len(labels), 5)
        from tracker.localization import present

        for index, language in enumerate(("de", "en", "es", "ru", "ja")):
            data = present(dict(location="Example", test_run=True), language)
            self.assertTrue(data["location"].startswith(debug.TEST_LABELS[index]))
