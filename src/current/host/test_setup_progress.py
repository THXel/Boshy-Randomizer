"""Progress must describe real work and preserve installation failure boundaries."""

import io
import tempfile
import unittest
from pathlib import Path
from distribution import original, transaction
from distribution.identity import sha256
from distribution.progress import Reporter
from distribution.linux.setup_window import progress_detail


class SetupProgressTests(unittest.TestCase):
    def test_protocol_flushes_phase_changes_and_completion_but_throttles_files(self):
        output = io.StringIO()
        reporter = Reporter(output, clock=lambda: 1.0)
        reporter("checking", 0, 20)
        reporter("checking", 1, 20)
        reporter("checking", 20, 20)
        reporter("images")
        self.assertEqual(
            output.getvalue().splitlines(),
            [
                "BOSHY_PROGRESS|checking|0|20",
                "BOSHY_PROGRESS|checking|20|20",
                "BOSHY_PROGRESS|images|0|0",
            ],
        )
        for args in [("bad|stage", 0, 0), ("copying", -1, 4), ("copying", 5, 4)]:
            with self.assertRaises(ValueError):
                reporter(*args)

    def test_unknown_download_has_bytes_but_no_invented_percentage(self):
        tr = lambda de, en: en
        percent, label = progress_detail("winedownload", 1048576, 0, tr)
        self.assertIsNone(percent)
        self.assertEqual(label, "1.0 MiB")
        percent, label = progress_detail("winedownload", 1048576, 2097152, tr)
        self.assertEqual(percent, 50)
        self.assertIn("50 %", label)

    def test_file_counts_follow_committed_work_and_failure_keeps_previous(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            (source / original.ORIGINAL_NAME).write_bytes(b"original")
            (source / "song.ogg").write_bytes(b"music")
            (source / "save.ini").write_bytes(b"private")
            events = []
            progress = lambda *args: events.append(args)
            expected = sha256(source / original.ORIGINAL_NAME)
            patched = root / "patched"
            patched.write_bytes(b"patched")
            target = sha256(patched)
            transaction.install(
                source,
                root / "install",
                "v1",
                target,
                lambda src, dst: dst.write_bytes(b"patched"),
                expected_source=expected,
                progress=progress,
            )
            self.assertIn(("importing", 2, 2), events)
            self.assertIn(("activating",), events)
            before = (root / "install/active.json").read_bytes()
            events.clear()
            with self.assertRaises(ValueError):
                transaction.install(
                    source,
                    root / "install",
                    "v2",
                    target,
                    lambda src, dst: dst.write_bytes(b"broken"),
                    expected_source=expected,
                    progress=progress,
                )
            self.assertEqual((root / "install/active.json").read_bytes(), before)
            self.assertNotIn(("activating",), events)
            self.assertFalse((root / "install/versions/v2").exists())
            events.clear()
            transaction.uninstall(root / "install", progress)
            self.assertTrue(
                any(e[0] == "removing" and len(e) == 3 and e[1] == e[2] for e in events)
            )
            self.assertEqual((source / "save.ini").read_bytes(), b"private")
