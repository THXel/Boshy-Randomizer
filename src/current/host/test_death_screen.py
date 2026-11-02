"""Death presentation preserves gameplay handlers and audited pack timelines."""

import tempfile
import unittest
from pathlib import Path
from visuals import death_screen as death
from gameplay.normal_plan import FRAMES
from transition.events import commands
import recover_boshy_classic as source


class DeathScreenTests(unittest.TestCase):
    def test_all_playable_frames_change_only_the_player_death_row(self):
        for frame in FRAMES:
            payload = next(p for p, n in source.routes.payloads.items() if n == frame)
            before = source.sections(payload)
            after, audit = death.transform(
                frame,
                before,
                source.routes.objects,
                source.routes.frames[frame - 1]["instances"],
            )
            self.assertEqual(len(audit), 1)
            si, ri = audit[0]["section"], audit[0]["row"]
            self.assertEqual(after[:si], before[:si])
            self.assertEqual(after[si + 1 : -1], before[si + 1 :])
            self.assertEqual(after[si][:ri], before[si][:ri])
            self.assertEqual(after[si][ri + 1 + len(death.PACKS) :], before[si][ri + 1 :])
            acts = [c[-1] for c in commands(before[si][ri]) if not c[0]]
            self.assertEqual([c[-1] for c in commands(after[si][ri]) if not c[0]], acts)
            for row in after[si][ri + 1 : ri + 1 + len(death.PACKS)]:
                changed = [c for c in commands(row) if not c[0]]
                preserved = [
                    c[-1]
                    for c in changed
                    if c[3] not in (death.OBJECT, 4401, 4402) and c[1:3] != (-2, 28)
                ]
                self.assertEqual(
                    preserved,
                    [
                        c[-1]
                        for c in commands(before[si][ri])
                        if not c[0] and not death.death_sound(c)
                    ],
                )
                self.assertEqual(sum(c[1:3] == (-2, 28) for c in changed), 1)

    def test_assets_are_exact_timed_and_sound_is_prepared_separately(self):
        assets = death.assets()
        self.assertEqual(set(assets), {"kamilia3", "wannafest22", "undertale"})
        for pack, data in assets.items():
            self.assertTrue(0 <= data["loop"] < len(data["frames"]) <= 512)
            self.assertEqual(set(data["frames"]), set(data["handles"]))
            self.assertTrue(all(im.size == (640, 480) for im in data["images"]))
        with tempfile.TemporaryDirectory() as tmp:
            death.prepare(tmp)
            for pack, data in assets.items():
                self.assertEqual(
                    (Path(tmp) / "native-death" / (pack + ".wav")).read_bytes(),
                    data["audio"],
                )

    def test_no_death_overlay_in_title_options_or_credits(self):
        for frame in (1, 2, 20, 48, 49):
            original = source.routes.frames[frame - 1]
            converted, objects = death.convert_frame(
                frame, original, source.routes.objects
            )
            self.assertIs(converted, original)
            self.assertNotIn(death.OBJECT, objects)


if __name__ == "__main__":
    unittest.main()
