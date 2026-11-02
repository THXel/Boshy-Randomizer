"""Registration, startup ownership, and opt-in removal regressions."""

import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from distribution.linux import lifecycle
from distribution.linux.setup_window import Cancelled
from distribution import user_data, setup_worker


class LifecycleTests(unittest.TestCase):
    def test_waits_for_real_registration_and_propagates_cancel(self):
        lookup = Mock(side_effect=[None, None, 112])
        progress = Mock()
        with patch.object(lifecycle.time, "sleep"):
            self.assertEqual(lifecycle.wait_registration(lookup, progress), "112")
        self.assertEqual(lookup.call_count, 3)
        with self.assertRaises(Cancelled):
            lifecycle.wait_registration(
                Mock(return_value=None), Mock(side_effect=Cancelled)
            )
        with self.assertRaises(TimeoutError):
            lifecycle.wait_registration(Mock(return_value=None), Mock(), timeout=0)

    def test_first_lutris_database_can_exist_before_schema(self):
        from distribution.linux import launcher

        with tempfile.TemporaryDirectory() as tmp:
            data = Path(tmp)
            (data / "lutris").mkdir()
            sqlite3.connect(data / "lutris/pga.db").close()
            with patch.object(launcher, "DATA", data):
                self.assertIsNone(launcher.registered_game())

    def test_window_manager_snapshot_failure_is_not_a_ready_window(self):
        with patch.object(lifecycle.subprocess, "run", return_value=Mock(returncode=1)):
            self.assertIsNone(lifecycle.owned_window(Path("/prefix")))
        with patch.object(
            lifecycle.subprocess,
            "run",
            side_effect=lifecycle.subprocess.TimeoutExpired("wmctrl", 5),
        ):
            self.assertIsNone(lifecycle.owned_window(Path("/prefix")))

    def test_selected_lutris_prefix_and_unknown_entry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "lutris/games").mkdir(parents=True)
            prefix = root / "custom-prefix"
            prefix.mkdir()
            (root / "lutris/games/my-game.yml").write_text(
                "game:\n  prefix: " + str(prefix) + "\n"
            )
            with sqlite3.connect(root / "lutris/pga.db") as db:
                db.execute(
                    "CREATE TABLE games (id INTEGER, installed INTEGER, configpath TEXT)"
                )
                db.execute('INSERT INTO games VALUES (112,1,"my-game")')
            with patch.dict(os.environ, XDG_CONFIG_HOME=str(root)):
                self.assertEqual(lifecycle.game_prefix(root, 112), prefix)
                with self.assertRaises(ValueError):
                    lifecycle.game_prefix(root, 99)

    def test_start_waits_for_window_and_does_not_restart_open_game(self):
        for windows, expected in [([None, None, "0x123"], 1), (["0x123"], 0)]:
            with tempfile.TemporaryDirectory() as tmp:
                base = Path(tmp)
                with (
                    patch.object(lifecycle, "game_prefix", return_value=base),
                    patch.object(lifecycle, "owned_window", side_effect=windows),
                    patch.object(lifecycle.subprocess, "Popen") as launch,
                    patch.object(lifecycle.subprocess, "run") as focus,
                    patch.object(lifecycle.time, "sleep"),
                ):
                    launch.return_value.poll.return_value = 0
                    progress = Mock()
                    lifecycle.launch_game(base, base, 112, progress)
                    self.assertEqual(launch.call_count, expected)
                    focus.assert_called_once_with(
                        ["wmctrl", "-ia", "0x123"], check=False, timeout=5
                    )
                    self.assertEqual(progress.call_count, 1 + len(windows))

    def test_start_timeout_is_not_reported_as_success(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with (
                patch.object(lifecycle, "game_prefix", return_value=base),
                patch.object(lifecycle, "owned_window", return_value=None),
                patch.object(lifecycle.subprocess, "Popen") as launch,
            ):
                launch.return_value.poll.return_value = 0
                with self.assertRaises(TimeoutError):
                    lifecycle.launch_game(base, base, 112, Mock(), timeout=0)

    def test_owned_window_excludes_original_and_uninstaller(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            prefix = root / "prefix"
            prefix.mkdir()
            proc = root / "proc"
            proc.mkdir()
            for pid, directory in [
                (1, prefix / "original"),
                (
                    2,
                    prefix
                    / "drive_c/users/u/AppData/Local/BoshyRandomizer/runs/rebuilt-menu-a",
                ),
                (3, root / "other/runs"),
            ]:
                directory.mkdir(parents=True)
                (proc / str(pid)).mkdir()
                (proc / str(pid) / "cwd").symlink_to(directory)
            result = Mock(
                returncode=0,
                stdout="0x1 0 1 host I Wanna Be The Boshy\n0x2 0 3 host Boshy\n0x3 0 2 host I Wanna Be The Boshy\n",
            )
            with patch.object(lifecycle.subprocess, "run", return_value=result):
                self.assertEqual(lifecycle.owned_window(prefix, proc=proc), "0x3")


class RemovalTests(unittest.TestCase):
    def run_worker(self, base, delete=False, fail=False):
        args = [
            "setup_worker.py",
            "uninstall",
            "--root",
            str(base / "app"),
            "--report",
            str(base / "report.json"),
        ]
        if delete:
            args.append("--delete-user-data")
        with (
            patch("sys.argv", args),
            patch.object(setup_worker.transaction, "installation_lock"),
            patch.object(
                setup_worker.transaction,
                "uninstall",
                side_effect=RuntimeError("busy") if fail else None,
                return_value=[],
            ),
        ):
            return setup_worker.main()

    def test_default_preserves_explicit_choice_deletes_only_own_data(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, LOCALAPPDATA=tmp),
        ):
            base = Path(tmp)
            own = base / "BoshyRandomizer"
            own.mkdir()
            (own / "save.ini").write_text("save")
            other = base / "OtherGame"
            other.mkdir()
            (other / "save.ini").write_text("original")
            self.assertEqual(self.run_worker(base), 0)
            self.assertEqual((own / "save.ini").read_text(), "save")
            self.assertEqual(self.run_worker(base, delete=True, fail=True), 1)
            self.assertTrue(own.exists())
            self.assertEqual(self.run_worker(base, delete=True), 0)
            self.assertFalse(own.exists())
            self.assertEqual((other / "save.ini").read_text(), "original")
            self.assertIn(
                "removed_user_data",
                json.loads((base / "report.json").read_text())["result"],
            )

    def test_links_refused_before_removing_any_data(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, LOCALAPPDATA=tmp),
        ):
            base = Path(tmp)
            own = base / "BoshyRandomizer"
            own.mkdir()
            outside = base / "OtherGame"
            outside.mkdir()
            (outside / "keep").write_text("keep")
            (own / "linked").symlink_to(outside, target_is_directory=True)
            with self.assertRaises(ValueError):
                user_data.remove_user_data()
            self.assertEqual((outside / "keep").read_text(), "keep")
            self.assertTrue(own.exists())

    def test_report_cannot_recreate_deleted_profile(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, LOCALAPPDATA=tmp),
        ):
            base = Path(tmp)
            own = base / "BoshyRandomizer"
            own.mkdir()
            args = [
                "worker",
                "uninstall",
                "--delete-user-data",
                "--root",
                str(base / "app"),
                "--report",
                str(own / "report.json"),
            ]
            with (
                patch("sys.argv", args),
                patch.object(setup_worker.transaction, "installation_lock"),
                patch.object(setup_worker.transaction, "uninstall") as remove,
            ):
                self.assertEqual(setup_worker.main(), 1)
                remove.assert_not_called()


if __name__ == "__main__":
    unittest.main()
