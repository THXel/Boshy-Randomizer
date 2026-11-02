"""Title soundtrack follows global preferences, never a run's shuffle or seed."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from music import title
from app_paths import SOUNDPACKS
from transition.events import commands
from transition.router import params
import recover_boshy_dynamic as source

class TitleMusicTests(unittest.TestCase):
    def test_exact_old_opening_tracks_and_original_reset(self):
        with tempfile.TemporaryDirectory() as tmp:
            for pack, (_, expected) in title.TRACKS.items():
                cfg = title.prepare(tmp, pack, SOUNDPACKS / pack)
                path = Path(tmp) / cfg['Opening'].replace('\\', '/')
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
                modified = path.stat().st_mtime_ns
                self.assertEqual(title.prepare(tmp, pack, SOUNDPACKS / pack), cfg)
                self.assertEqual(path.stat().st_mtime_ns, modified)
                path.write_bytes(b'broken cache')
                title.prepare(tmp, pack, SOUNDPACKS / pack)
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
            self.assertEqual(title.prepare(tmp, 'original', None), dict(Enabled=0, Opening=''))
            with self.assertRaises(ValueError):title.prepare(tmp, 'invalid', SOUNDPACKS)

    def test_unrelated_frames_are_untouched(self):
        for no in (1, 3, 20, 23, 45):
            sections = [[b'unrelated event']]
            result, audit = title.transform(no, sections)
            self.assertIs(result, sections)
            self.assertEqual(audit, [])

    def test_only_title_playback_is_replaced_with_original_channel(self):
        payload = next(p for p, no in source.routes.payloads.items() if no == 2)
        before = source.classic.sections(payload)
        after, audit = title.transform(2, before)
        original = next(c for rows in before for row in rows for c in commands(row) if title.is_title(c))
        replacement = [c for rows in after for row in rows for c in commands(row) if not c[0] and c[1] == -2 and c[2] == 28 and b'TitleMusicV1' in c[-1]]
        self.assertEqual(len(replacement), 1)
        self.assertEqual(params(original[-1])[1:], params(replacement[0][-1])[1:])
        flattened = [row for rows in after for row in rows]
        for rows in before:
            for row in rows:
                if not any(title.is_title(c) for c in commands(row)):
                    self.assertIn(row, flattened)
        self.assertEqual(audit[0]['title_music'], 1)

    def test_global_view_is_loaded_before_title_playback(self):
        payload = next(p for p, no in source.routes.payloads.items() if no == 2)
        rows = [r for section in source.sections(payload) for r in section]
        load = next(i for i, r in enumerate(rows) if b'presentation-view.ini' in r)
        music = next(i for i, r in enumerate(rows) if b'TitleMusicV1' in r)
        self.assertLess(load, music)
