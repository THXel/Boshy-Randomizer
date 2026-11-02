"""Failure-path ownership checks for the private Wine menu host."""

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from menu_host.processes import games
from menu_host.runtime import Runtime


class ProcessTests(unittest.TestCase):
    def test_headless_games_but_not_editor_helpers_zombies_or_foreign_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runs = root / "runs"
            folder = runs / "rebuilt-menu-test"
            folder.mkdir(parents=True)
            proc = root / "proc"
            proc.mkdir()

            def process(pid, cwd, args, state="S"):
                p = proc / str(pid)
                p.mkdir()
                (p / "cwd").symlink_to(cwd, target_is_directory=True)
                (p / "stat").write_text(f"{pid} (name with ) spaces) {state} 1 1")
                (p / "cmdline").write_bytes(b"\0".join(args))

            process(1, folder, [b"wine", str(folder / "Boshy.exe").encode()])
            process(2, folder, [b"C:\\BoshySceneTests\\rebuilt-menu-test\\Boshy.exe"])
            process(3, folder, [b"phase_bridge.exe"])
            process(4, folder, [b"Boshy.exe"], "Z")
            process(5, root, [b"Boshy.exe"])
            process(6, folder, [b"mmf2u.exe"])
            process(7, folder, [b"not-Boshy.exe"])
            process(8, folder / "missing", [b"Boshy.exe"])
            self.assertEqual(games(runs, proc), {1: folder, 2: folder})


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.store = SimpleNamespace(
            active=1,
            summary=Mock(return_value={"seed": "abc"}),
            resume=Mock(return_value=(self.folder, {"game_sha256": "test"}, None)),
        )
        self.runtime = Runtime(self.store)
        self.runtime.slot = 1
        self.runtime.folder = self.folder
        self.runtime.events = []
        self.window_patch = patch("menu_host.runtime.windows", return_value=[])
        self.game_patch = patch("menu_host.runtime.games", return_value={})
        self.window_patch.start()
        self.games = self.game_patch.start()
        self.time_patch = patch("menu_host.runtime.CLOSE_TIMEOUT", 0)
        self.time_patch.start()

    def tearDown(self):
        self.time_patch.stop()
        self.game_patch.stop()
        self.window_patch.stop()
        if self.runtime.log:
            self.runtime.log.close()
        self.tmp.cleanup()

    def test_headless_existing_game_blocks_launch_before_resume(self):
        self.store.active = None
        self.games.return_value = {999: self.folder}
        with self.assertRaises(RuntimeError):
            self.runtime.start(1)
        self.store.resume.assert_not_called()

    def test_window_disappearing_does_not_unlock_live_process(self):
        self.runtime.proc = Mock()
        self.runtime.proc.poll.return_value = None
        with self.assertRaisesRegex(RuntimeError, "gesperrt"):
            self.runtime.close("window-closed")
        self.assertEqual(self.store.active, 1)
        self.runtime.proc.terminate.assert_not_called()
        self.store.resume.assert_not_called()

    def test_wine_handoff_remains_locked_after_launcher_exit(self):
        self.runtime.proc = Mock()
        self.runtime.proc.poll.return_value = 0
        self.games.return_value = {999: self.folder}
        with self.assertRaisesRegex(RuntimeError, "gesperrt"):
            self.runtime.close()
        self.assertEqual(self.store.active, 1)

    def test_failed_start_terminates_only_own_headless_child_then_unlocks(self):
        child = Mock()
        child.poll.return_value = None
        child.terminate.side_effect = lambda: setattr(child.poll, "return_value", -15)
        self.runtime.proc = child
        self.runtime.close("startup-error")
        child.terminate.assert_called_once()
        self.assertIsNone(self.store.active)
        self.assertEqual(
            json.loads((self.folder / "host-session.json").read_text())[0]["reason"],
            "startup-error",
        )

    def test_failed_termination_keeps_slot_locked(self):
        self.runtime.proc = Mock()
        self.runtime.proc.poll.return_value = None
        with self.assertRaises(RuntimeError):
            self.runtime.close("startup-error")
        self.assertEqual(self.store.active, 1)
        self.assertFalse((self.folder / "host-session.json").exists())

    def test_unassigned_duplicate_windows_are_closed_normally(self):
        self.runtime.game_windows = Mock(side_effect=[["0x1", "0x2"], []])
        with patch("menu_host.runtime.subprocess.run") as run:
            self.runtime.close("startup-error")
        self.assertEqual(
            [c.args[0] for c in run.call_args_list],
            [["wmctrl", "-ic", "0x1"], ["wmctrl", "-ic", "0x2"]],
        )
        self.assertIsNone(self.store.active)

    def test_reader_timeout_closes_owned_game_and_reports_error(self):
        self.runtime.owned = Mock(return_value=True)
        self.runtime.reader = Mock()
        self.runtime.reader.frame.side_effect = TimeoutError("observer timeout")
        reader = self.runtime.reader
        with self.assertRaises(TimeoutError):
            self.runtime.poll()
        reader.close.assert_called_once()
        self.assertIsNone(self.store.active)

    def test_log_open_failure_leaves_no_stuck_slot(self):
        self.store.active = None
        (self.folder / "host-runtime.log").mkdir()
        with patch("menu_host.runtime.verify_engine"), self.assertRaises(
            IsADirectoryError
        ):
            self.runtime.start(1)
        self.assertIsNone(self.store.active)

    def test_launch_failure_cleans_log_and_does_not_leave_slot_locked(self):
        self.store.active = None
        with patch("menu_host.runtime.verify_engine"), patch(
            "menu_host.runtime.subprocess.Popen", side_effect=OSError("spawn failed")
        ):
            with self.assertRaisesRegex(OSError, "spawn failed"):
                self.runtime.start(1)
        self.assertIsNone(self.store.active)
        self.assertIsNone(self.runtime.log)

    def test_normal_close_does_not_terminate_launcher(self):
        child = Mock()
        child.poll.return_value = 0
        self.runtime.proc = child
        self.runtime.close()
        child.terminate.assert_not_called()
        self.assertIsNone(self.store.active)


if __name__ == "__main__":
    unittest.main()


class WindowEnumerationTests(unittest.TestCase):
    def test_disappearing_window_retries_without_trusting_partial_output(self):
        from subprocess import CompletedProcess
        from menu_host.runtime import windows

        failed = CompletedProcess(
            ["wmctrl", "-lp"],
            1,
            "0xdead 0 9 host I Wanna Be The Boshy\n",
            "X Error: BadWindow (invalid Window parameter)",
        )
        good = CompletedProcess(
            ["wmctrl", "-lp"],
            0,
            "0x123 0 42 host I Wanna Be The Boshy\n0x456 0 43 host Fusion\n",
            "",
        )
        with patch(
            "menu_host.runtime.subprocess.run", side_effect=[failed, good]
        ) as run, patch("menu_host.runtime.time.sleep"):
            self.assertEqual(
                windows(), [["0x123", "0", "42", "host", "I Wanna Be The Boshy"]]
            )
            self.assertEqual(run.call_count, 2)

    def test_other_window_query_failure_is_not_hidden(self):
        from subprocess import CompletedProcess, CalledProcessError
        from menu_host.runtime import windows

        result = CompletedProcess(["wmctrl", "-lp"], 1, "", "Cannot open display")
        with patch(
            "menu_host.runtime.subprocess.run", return_value=result
        ) as run, self.assertRaises(CalledProcessError):
            windows()
        self.assertEqual(run.call_count, 1)

    def test_persistent_window_race_has_a_finite_retry_limit(self):
        from subprocess import CompletedProcess, CalledProcessError
        from menu_host.runtime import windows

        result = CompletedProcess(
            ["wmctrl", "-lp"], 1, "", "BadWindow (invalid Window parameter)"
        )
        with patch(
            "menu_host.runtime.subprocess.run", return_value=result
        ) as run, patch("menu_host.runtime.time.sleep"), self.assertRaises(
            CalledProcessError
        ):
            windows()
        self.assertEqual(run.call_count, 3)
