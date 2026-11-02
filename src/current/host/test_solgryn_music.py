"""Replacement tracks must survive Solgryn's intro and second phase."""

import unittest
from music import runtime, solgryn
from gameplay import intro_skip
from transition.events import commands, expression, integer
from transition.router import params
import recover_boshy_routes as source


class SolgrynMusicTests(unittest.TestCase):
    def test_loop_and_phase_controls_with_manual_and_automatic_skip(self):
        payload = next(p for p, frame in source.payloads.items() if frame == 46)
        original = source.original_sections(payload)
        for auto in (False, True):
            with self.subTest(automatic_skip=auto):
                before = intro_skip.transform(46, original)[0] if auto else original
                before = runtime.transform(
                    46, before, source.objects, source.frames[45]["instances"]
                )[0]
                after, audit = solgryn.transform(
                    46, before, source.objects, source.frames[45]["instances"]
                )
                self.assertEqual(
                    audit[0]["original_only_music_seeks"], 4 if auto else 3
                )
                plays = [
                    c
                    for rows in after
                    for row in rows
                    for c in commands(row)
                    if not c[0] and c[1] == -2 and b"Cue03\0" in c[-1]
                ]
                self.assertEqual(len(plays), 1)
                self.assertEqual(plays[0][2], 29)
                self.assertEqual(
                    params(plays[0][-1])[-2:],
                    [(22, expression(integer(2))), (27, expression(integer(0), 27))],
                )
                for oldrows, newrows in zip(before, after):
                    it = iter(newrows)
                    for row in oldrows:
                        cs = commands(row)
                        first = next(it)
                        old_actions = [c[-1] for c in cs if not c[0]]
                        if any(solgryn.original_seek(c) for c in cs):
                            # The original branch retains ALL original actions.
                            self.assertEqual(
                                [c[-1] for c in commands(first) if not c[0]],
                                old_actions,
                            )
                            self.assertIn(b"Enabled\0", first)
                            replacement = [
                                c[-1]
                                for c in cs
                                if not c[0] and not solgryn.original_seek(c)
                            ]
                            if replacement:
                                second = next(it)
                                self.assertIn(b"Enabled\0", second)
                                self.assertEqual(
                                    [c[-1] for c in commands(second) if not c[0]],
                                    replacement,
                                )
                        elif not any(
                            c[1:3] == (-2, 28) and b"Cue03\0" in c[-1] for c in cs
                        ):
                            # Includes reset position restore, volume, pauses,
                            # resumes, death sounds and all gameplay actions.
                            self.assertEqual(first, row)
                    self.assertEqual(list(it), [])

    def test_other_frames_are_untouched(self):
        for payload, frame in source.payloads.items():
            if frame == 46:
                continue
            original = source.original_sections(payload)
            after, audit = solgryn.transform(
                frame, original, source.objects, source.frames[frame - 1]["instances"]
            )
            self.assertIs(after, original)
            self.assertEqual(audit, [])
