"""Real inter-process exclusion, durable replacement and package boundaries."""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from platform_support.storage import lock_file, replace
from distribution.payload import stage, copy_tree
from app_paths import LAB, REPO


class PlatformSupportTests(unittest.TestCase):
    def test_competing_process_cannot_take_held_lock_and_can_take_released_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "held.lock"
            script = """from platform_support.storage import lock_file
import sys
try:
 with lock_file(sys.argv[1]): pass
except OSError:
 sys.exit(23)
"""
            command = [sys.executable, "-c", script, str(path)]
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            with lock_file(path):
                self.assertEqual(
                    subprocess.run(command, env=env, timeout=10).returncode, 23
                )
            self.assertEqual(subprocess.run(command, env=env, timeout=10).returncode, 0)

    def test_failed_replacement_preserves_previous_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "active.json"
            target.write_bytes(b"previous")
            with self.assertRaises(OSError):
                replace(root / "missing", target)
            self.assertEqual(target.read_bytes(), b"previous")
            candidate = root / "candidate"
            candidate.write_bytes(b"next")
            replace(candidate, target)
            self.assertEqual(target.read_bytes(), b"next")
            self.assertFalse(candidate.exists())

    def test_host_payload_excludes_live_tests_and_game_fixtures(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = stage(LAB, REPO, Path(tmp) / "host")
            files = [p.relative_to(root) for p in root.rglob("*") if p.is_file()]
            self.assertEqual(len(files), len({p.as_posix().casefold() for p in files}))
            self.assertFalse(
                any(
                    p.suffix.lower() in (".exe", ".mfa", ".msi", ".deb", ".bpatch")
                    for p in files
                )
            )
            self.assertFalse(
                any(
                    "test_" in p.name
                    or p.name.endswith("_live.py")
                    or "__pycache__" in p.parts
                    for p in files
                )
            )
            self.assertTrue((root / "app/distribution/windows_entry.py").is_file())
            self.assertTrue(
                (root / "app/resources/fonts/NotoSansCJK-Regular.ttc").is_file()
            )
            self.assertTrue((root / "app/KlikBack/LICENSE").is_file())
            self.assertFalse((root / "app/god_mode_boss_probe.py").exists())
            self.assertTrue(
                (root / "shared/assets/catalogues/slot_reward_plan.json").is_file()
            )

    def test_case_aliases_deduplicate_only_identical_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "source"
            src.mkdir()
            (src / "Badge.png").write_bytes(b"image")
            (src / "badge.png").write_bytes(b"image")
            copy_tree(src, root / "target")
            self.assertEqual(len(list((root / "target").iterdir())), 1)
            (src / "badge.png").write_bytes(b"different")
            with self.assertRaisesRegex(ValueError, "Conflicting"):
                copy_tree(src, root / "second")

    def test_slow_window_is_allowed_but_exited_game_fails_immediately(self):
        from unittest.mock import patch, Mock
        from native_menu.window import wait_for_window
        folder = Path("/test/run")
        elapsed = [0.0]
        row = ("0x123", "0", "42", "host", "I Wanna Be The Boshy")
        def advance(seconds):
            elapsed[0] += seconds
        with (patch("native_menu.window.time.monotonic", side_effect=lambda: elapsed[0]),
              patch("native_menu.window.time.sleep", side_effect=advance),
              patch("native_menu.window.games", return_value={42: folder}),
              patch("native_menu.window.windows", side_effect=lambda: [row] if elapsed[0] > 35 else [])):
            self.assertEqual(wait_for_window(Mock(poll=lambda: None), folder, 90), row)
            elapsed[0] = 0
            with self.assertRaisesRegex(RuntimeError, "exit 5"):
                wait_for_window(Mock(poll=lambda: 5), folder, 90)
            self.assertEqual(elapsed[0], 0)


if __name__ == "__main__":
    unittest.main()
