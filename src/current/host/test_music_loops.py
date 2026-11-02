"""Every background track repeats; scene triggers and one-shot SFX survive."""

import unittest
from music import loops, runtime, title
from transition.events import commands, expression, integer
from transition.router import params
import recover_boshy_routes as source


class MusicLoopTests(unittest.TestCase):
    def test_all_original_music_loops_and_every_other_action_is_identical(self):
        seen = set()
        for payload, frame in source.payloads.items():
            before = source.original_sections(payload)
            after, _ = loops.transform(frame, before)
            self.assertEqual(len(before), len(after))
            for oldrows, newrows in zip(before, after):
                self.assertEqual(len(oldrows), len(newrows))
                for row, patched in zip(oldrows, newrows):
                    aa, bb = commands(row), commands(patched)
                    self.assertEqual(len(aa), len(bb))
                    for a, b in zip(aa, bb):
                        if loops.is_music(a):
                            ps = params(a[-1])
                            seen.add(ps[0][1][8:].split(b"\0", 1)[0].decode("latin1"))
                            self.assertIn(b[2], (4, 12))
                            self.assertEqual(
                                params(b[-1])[-1], (27, expression(integer(0), 27))
                            )
                            self.assertEqual(
                                params(b[-1])[:-1], ps[:-1] if a[2] in (4, 12) else ps
                            )
                        else:
                            self.assertEqual(a, b)
        self.assertTrue(set(runtime.NAMES) <= seen)
        self.assertTrue({title.CUE, "Boshy Credits", "loludied"} <= seen)
        self.assertNotIn("MEGAMANbeat-final-boss (2)", seen)
        self.assertNotIn("Solgryn_roar", seen)

    def test_replacement_music_keeps_its_channel_and_loops(self):
        for payload, frame in source.payloads.items():
            before = source.original_sections(payload)
            if frame == 2:
                before, _ = title.transform(frame, before)
            else:
                before, _ = runtime.transform(
                    frame, before, source.objects, source.frames[frame - 1]["instances"]
                )
            after, _ = loops.transform(frame, before)
            for oldrows, newrows in zip(before, after):
                for old, new in zip(oldrows, newrows):
                    for a, b in zip(commands(old), commands(new)):
                        if not a[0] and a[2] in (28, 29) and loops.is_music(a):
                            self.assertEqual(b[2], 29)
                            self.assertEqual(params(a[-1])[:2], params(b[-1])[:2])
                            self.assertEqual(
                                params(b[-1])[-1], (27, expression(integer(0), 27))
                            )
