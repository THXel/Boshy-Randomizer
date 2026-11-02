import tempfile
import unittest
from pathlib import Path
from distribution.runtime_files import REQUIRED, validate_runtime


class RuntimeFilesTests(unittest.TestCase):
    def test_missing_window_component_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in REQUIRED:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"fixture")
            validate_runtime(root)
            missing = root / "DLLs/_tkinter.pyd"
            missing.unlink()
            with self.assertRaisesRegex(ValueError, "_tkinter.pyd"):
                validate_runtime(root)
            missing.write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "_tkinter.pyd"):
                validate_runtime(root)

    def test_build_rejects_incomplete_runtime_before_staging(self):
        from unittest.mock import patch
        from distribution.build_preview import build

        with (
            tempfile.TemporaryDirectory() as tmp,
            patch("distribution.build_preview.stage") as stage,
        ):
            with self.assertRaisesRegex(ValueError, "Incomplete Windows runtime"):
                build(None, None, Path(tmp), None, None, None, Path(tmp) / "output")
            stage.assert_not_called()


if __name__ == "__main__":
    unittest.main()
