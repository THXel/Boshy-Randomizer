"""Verify original victory effects and native completion gates survive routing."""

import unittest
from recover_boshy_boss_exits import patches, original_sections
from transition.boss_exits import split, commands, GROUP, TARGETS


class BossExitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frames = {
            frame: (original_sections(payload), fn(original_sections(payload))[0])
            for payload, (frame, fn) in patches.items()
        }

    def test_only_intended_sections_change(self):
        for frame, sections in [(5, [88]), (10, [25]), (54, [101])]:
            old, new = self.frames[frame]
            self.assertEqual(
                [i for i, (a, b) in enumerate(zip(old, new)) if a != b], sections
            )

    def test_mario_fallback_retains_every_original_action(self):
        old, new = self.frames[10]
        self.assertEqual(split(old[25][2])[1], split(new[25][2])[1])

    def test_mario_victory_and_gravity_actions_precede_route_save(self):
        old, new = self.frames[10]
        cond, acts = split(old[25][2])
        for row in new[25][3:6]:
            c, a = split(row)
            self.assertEqual(c[: len(cond)], cond)
            self.assertEqual(a[:3], acts[2:5])
            self.assertIn(b'save\0', a[-2])
            self.assertEqual(commands(row)[-1][1:3], (-3, 2))

    def test_kracko_requires_original_death_event(self):
        old, new = self.frames[5]
        c, a = split(old[88][35])
        nc, na = split(new[88][36])
        self.assertEqual(c, nc)
        self.assertEqual(a, na[:-1])
        self.assertIn(b'KrackoVictory', na[-1])

    def test_kracko_restart_and_rectangle_gate(self):
        old, new = self.frames[5]
        self.assertEqual(split(new[88][0])[0], split(old[88][3])[0])
        self.assertIn(b'KrackoVictory', split(new[88][0])[1][0])
        for row in new[88][-3:]:
            cond, acts = split(row)
            self.assertEqual(len(cond), 6)
            self.assertEqual([c[2] for c in commands(row)[:4]], [-17, -17, -16, -16])
            self.assertIn(b'KrackoVictory', cond[-2])
            self.assertIn(b'KrackoRoute', cond[-1])
            self.assertIn(b'save\0', acts[-2])
            self.assertEqual(commands(row)[-1][1:3], (-3, 2))

    def test_seed_adapter_matches_compiled_interface(self):
        import sys
        from pathlib import Path

        sys.path.insert(
            0,
            str(
                Path(__file__).resolve().parents[1]
                / 'Boshy-Randomizer/src/python/rules'
            ),
        )
        import fusion_route as f

        self.assertEqual(f.GROUP, GROUP)
        for spot, p in f.TARGETS.items():
            self.assertEqual(
                TARGETS[p['code']],
                dict(spot=spot, **{k: p[k] for k in ('x', 'y', 'frame')}),
            )


if __name__ == '__main__':
    unittest.main()
