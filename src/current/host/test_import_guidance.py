"""Installer failures identify the reason without changing import boundaries."""

import tempfile, unittest, hashlib, json
from pathlib import Path
from unittest.mock import patch
from distribution import original
from distribution.import_errors import OriginalImportError, explanation


class ImportGuidanceTests(unittest.TestCase):
    def test_each_size_limit_has_a_distinct_actionable_reason(self):
        for args, code in (
            ((20001, 0, 0), "file_count"),
            ((1, 2000000001, 0), "total_size"),
            ((1, 0, 500000001), "file_size"),
        ):
            with self.assertRaises(OriginalImportError) as error:
                original._check_limits(*args, "Original folder")
            self.assertEqual(error.exception.code, code)
            self.assertNotEqual(
                explanation(error.exception, "german"),
                explanation(error.exception, "english"),
            )

    def test_missing_and_multiple_games_are_distinguished(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            with self.assertRaises(OriginalImportError) as e:
                original.import_original(source, root / "copy")
            self.assertEqual(e.exception.code, "missing_game")
            self.assertFalse((root / "copy").exists())
            (source / original.ORIGINAL_NAME).write_bytes(b"original")
            (source / "backup").mkdir()
            (source / "backup" / original.ORIGINAL_NAME).write_bytes(b"original")
            with self.assertRaises(OriginalImportError) as e:
                original.import_original(source, root / "copy")
            self.assertEqual(e.exception.code, "multiple_games")
            self.assertFalse((root / "copy").exists())

    def test_valid_original_is_copied_and_rejection_keeps_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            game = source / original.ORIGINAL_NAME
            game.write_bytes(b"original")
            expected = hashlib.sha256(b"original").hexdigest()
            with (
                patch.object(original, "MAX_FILES", 0),
                self.assertRaises(OriginalImportError),
            ):
                original.import_original(source, root / "rejected", expected=expected)
            self.assertEqual(game.read_bytes(), b"original")
            self.assertFalse((root / "rejected").exists())
            self.assertEqual(
                original.import_original(
                    source, root / "valid", expected=expected
                ).read_bytes(),
                b"original",
            )

    def test_unknown_error_text_is_not_embedded_in_user_guidance(self):
        self.assertNotIn(
            "private-secret", explanation(ValueError("private-secret /home/user"))
        )


if __name__ == "__main__":
    unittest.main()
