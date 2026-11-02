import struct, unittest
from recover_boshy_routes import payloads, original_sections
from recovery.gameplay_rules import beta_damage_guards
from transition.events import commands, event
from transition.boss_exits import split


class BetaGuardTests(unittest.TestCase):
    def test_only_two_damage_comparisons_change_per_boss(self):
        for frame in [44, 45]:
            original = original_sections(
                next(p for p, n in payloads.items() if n == frame)
            )
            result, audit = beta_damage_guards(frame, original)
            self.assertEqual(len(audit), 2)
            changed = []
            for si, rows in enumerate(original):
                for ri, row in enumerate(rows):
                    if row == result[si][ri]:
                        continue
                    changed.append((si, ri))
                    a, b = commands(row), commands(result[si][ri])
                    self.assertEqual(
                        [c for c in a if not c[0]], [c for c in b if not c[0]]
                    )
                    diffs = [(x, y) for x, y in zip(a, b) if x != y]
                    self.assertEqual(len(diffs), 1)
                    old, new = diffs[0]
                    self.assertEqual(old[-1][:38], new[-1][:38])
                    self.assertEqual(old[-1][42:], new[-1][42:])
                    self.assertEqual(struct.unpack_from("<I", old[-1], 38)[0], 400)
                    self.assertEqual(struct.unpack_from("<I", new[-1], 38)[0], 779)
            self.assertEqual(changed, [(18, 1), (18, 2)])

    def test_unknown_source_threshold_fails_closed(self):
        ss = original_sections(next(p for p, n in payloads.items() if n == 44))
        cs, actions = split(ss[18][1])
        c = bytearray(cs[1])
        struct.pack_into("<I", c, 38, 450)
        cs[1] = bytes(c)
        ss[18][1] = event(ss[18][1], cs, actions)
        with self.assertRaises(AssertionError):
            beta_damage_guards(44, ss)

    def test_other_frames_untouched(self):
        sample = [[b"unchanged"]]
        self.assertIs(beta_damage_guards(10, sample)[0], sample)


if __name__ == "__main__":
    unittest.main()
