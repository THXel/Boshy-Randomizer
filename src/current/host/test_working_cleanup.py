"""Reversible cleanup must never consume saves or recovery data."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as S
from unittest.mock import patch
from menu_host import cleanup


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runs = self.root / "runs"
        self.runs.mkdir()
        self.profile = self.root / "profile"
        self.profile.mkdir()
        self.protected = {}
        self.store = S(
            root=self.profile,
            runs=self.runs,
            lockfile=True,
            writable=lambda: None,
            current=lambda slot: self.protected.get(slot),
            folder=lambda slot: self.protected[slot],
        )
        self.trash = self.root / "trash"
        self.trash.mkdir()

    def folder(self, n, closed=True):
        path = self.runs / ("rebuilt-menu-" + format(n, "032x"))
        path.mkdir()
        (path / "Boshy.exe").write_bytes(b"fixture")
        cleanup.started(path, self.profile)
        if closed:
            cleanup.finished(path, self.profile)
            data = cleanup.metadata(path)
            data["closed"] = n
            (path / cleanup.MARKER).write_text(json.dumps(data))
        return path

    def collect(self, active=None):
        with patch.object(
            cleanup, "recycle", side_effect=lambda p: p.rename(self.trash / p.name)
        ):
            return cleanup.collect(self.store, active_games=lambda: active or {})

    def test_keep_three_and_recycle_only_marked_completed_working_copies(self):
        paths = [self.folder(n) for n in range(1, 7)]
        unmarked = self.folder(7)
        (unmarked / cleanup.MARKER).unlink()
        open_copy = self.folder(8, False)
        saved = self.folder(9)
        (saved / "plan.json").write_text("{}")
        other = self.folder(10)
        data = cleanup.metadata(other)
        data["profile"] = "another-profile"
        (other / cleanup.MARKER).write_text(json.dumps(data))
        result = self.collect()
        self.assertEqual(result["recycled"], 3)
        self.assertTrue(
            all(p.exists() for p in paths[3:] + [unmarked, open_copy, saved, other])
        )
        self.assertTrue(
            all(
                (self.trash / p.name / "Boshy.exe").read_bytes() == b"fixture"
                for p in paths[:3]
            )
        )

    def test_save_journal_and_live_process_remain_protected(self):
        paths = [self.folder(n) for n in range(1, 8)]
        self.protected[1] = paths[0]
        (self.profile / "native-session.json").write_text(
            json.dumps({"working": paths[1].name})
        )
        self.collect({123: paths[2]})
        self.assertTrue(all(p.exists() for p in paths[:3]))
        self.assertFalse(paths[3].exists())

    def test_missing_lock_and_invalid_journal_fail_closed(self):
        paths = [self.folder(n) for n in range(1, 6)]
        self.store.lockfile = None
        self.assertTrue(self.collect()["blocked"])
        self.store.lockfile = True
        (self.profile / "native-session.json").write_text("{")
        self.assertTrue(self.collect()["blocked"])
        self.assertTrue(all(p.exists() for p in paths))

    def test_recycle_error_keeps_copy_and_does_not_abort_game(self):
        paths = [self.folder(n) for n in range(1, 5)]
        with patch.object(cleanup, "recycle", side_effect=OSError("bin unavailable")):
            result = cleanup.collect(self.store, active_games=lambda: {})
        self.assertEqual(result["skipped"], 1)
        self.assertTrue(all(p.exists() for p in paths))

    def test_process_inventory_failure_keeps_everything(self):
        paths = [self.folder(n) for n in range(1, 5)]
        with patch.object(cleanup, "recycle") as recycle:
            result = cleanup.collect(
                self.store,
                active_games=lambda: (_ for _ in ()).throw(OSError("denied")),
            )
        self.assertTrue(result["blocked"])
        recycle.assert_not_called()

    def test_directory_link_is_never_followed(self):
        import os, subprocess

        paths = [self.folder(n) for n in range(1, 5)]
        outside = self.root / "outside"
        outside.mkdir()
        (outside / "important").write_text("keep")
        link = paths[0] / "link"
        if os.name == "nt":
            subprocess.run(
                ["cmd.exe", "/c", "mklink", "/J", str(link), str(outside)],
                check=True,
                capture_output=True,
            )
        else:
            link.symlink_to(outside, target_is_directory=True)
        try:
            result = self.collect()
            self.assertEqual(result["skipped"], 1)
            self.assertEqual((outside / "important").read_text(), "keep")
            self.assertTrue(paths[0].exists())
        finally:
            if os.name == "nt":
                link.rmdir()
            else:
                link.unlink()


if __name__ == "__main__":
    unittest.main()
