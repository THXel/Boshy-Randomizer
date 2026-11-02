import errno
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import unquote_to_bytes
from platform_support.trash_files import move_to_home_trash


class WineTrashTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "working copy"
        self.source.mkdir()
        (self.source / "proof.txt").write_text("recoverable")
        self.trash = self.root / "Trash"

    def test_move_keeps_content_and_recovery_metadata(self):
        original = "/home/example/a %ä/working copy".encode()
        target, info = move_to_home_trash(self.source, self.trash, original)
        self.assertFalse(self.source.exists())
        self.assertEqual((target / "proof.txt").read_text(), "recoverable")
        text = info.read_text()
        self.assertTrue(text.startswith("[Trash Info]\n"))
        encoded = next(
            line[5:] for line in text.splitlines() if line.startswith("Path=")
        )
        self.assertEqual(unquote_to_bytes(encoded), original)
        self.assertRegex(text, r"DeletionDate=\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    def test_cross_device_failure_keeps_source_without_copy_delete_fallback(self):
        with patch(
            "platform_support.trash_files.os.rename",
            side_effect=OSError(errno.EXDEV, "Different volumes"),
        ):
            with self.assertRaises(OSError):
                move_to_home_trash(self.source, self.trash, b"/original")
        self.assertEqual((self.source / "proof.txt").read_text(), "recoverable")
        self.assertEqual(list((self.trash / "files").iterdir()), [])
        self.assertEqual(list((self.trash / "info").iterdir()), [])

    def test_existing_trash_item_is_never_overwritten(self):
        fixed = SimpleNamespace(hex="unique")
        target = self.trash / "files/boshy-unique"
        target.mkdir(parents=True)
        (target / "keep").write_text("existing")
        with patch("platform_support.trash_files.uuid.uuid4", return_value=fixed):
            with self.assertRaises(FileExistsError):
                move_to_home_trash(self.source, self.trash, b"/original")
        self.assertTrue(self.source.exists())
        self.assertEqual((target / "keep").read_text(), "existing")

    def test_metadata_error_does_not_move_source(self):
        with patch(
            "platform_support.trash_files.Path.open",
            side_effect=PermissionError("Read only"),
        ):
            with self.assertRaises(PermissionError):
                move_to_home_trash(self.source, self.trash, b"/original")
        self.assertTrue(self.source.exists())

    def test_linked_trash_directory_is_rejected(self):
        import subprocess

        other = self.root / "other"
        other.mkdir()
        if os.name == "nt":
            subprocess.run(
                ["cmd.exe", "/c", "mklink", "/J", str(self.trash), str(other)],
                check=True,
                capture_output=True,
            )
        else:
            self.trash.symlink_to(other, target_is_directory=True)
        try:
            with self.assertRaises(OSError):
                move_to_home_trash(self.source, self.trash, b"/original")
            self.assertTrue(self.source.exists())
            self.assertEqual(list(other.iterdir()), [])
        finally:
            if os.name == "nt":
                self.trash.rmdir()
            else:
                self.trash.unlink()

    def test_wine_host_environment_and_home_translation(self):
        from platform_support.wine_trash import trash_location
        from unittest.mock import Mock

        paths = Mock()
        self.assertEqual(
            str(trash_location(paths, {"WINE_HOST_XDG_DATA_HOME": "/custom/data"})),
            "/custom/data/Trash",
        )
        paths.unix.return_value = b"/home/player"
        self.assertEqual(
            str(trash_location(paths, {"WINEHOMEDIR": "Z:/home/player"})),
            "/home/player/.local/share/Trash",
        )
        paths.unix.assert_called_once_with("Z:/home/player")
        with self.assertRaises(OSError):
            trash_location(paths, {})
        with self.assertRaises(OSError):
            trash_location(paths, {"WINE_HOST_XDG_DATA_HOME": "/unsafe/../data"})


if __name__ == "__main__":
    unittest.main()
