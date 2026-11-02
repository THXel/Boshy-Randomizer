"""Ensure silence and sample alignment cannot fake continuity evidence."""

import unittest
import numpy as np
from music.continuity import match, match_after


class ContinuityTests(unittest.TestCase):
    def test_truncated_capture_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Insufficient audio"):
            match(np.ones(100), np.array([]))

    def test_silence_is_not_a_match(self):
        rng = np.random.default_rng(913)
        ref = np.r_[rng.normal(size=20000), np.zeros(10000)]
        needle = ref[1500:3705] * 0.01
        result = match(ref, needle)
        self.assertAlmostEqual(result["reference_seconds"], 1500 / 4410)
        self.assertGreater(result["correlation"], 0.99999)
        self.assertEqual(match(ref, np.zeros(2205))["correlation"], 0)

    def test_continuous_music_and_restart_have_distinct_positions(self):
        rng = np.random.default_rng(913)
        ref = rng.normal(size=30000)
        before = match(ref, ref[1000:3205])
        after = match(ref, ref[10000:12205])
        restarted = match(ref, ref[:2205])
        self.assertAlmostEqual(
            after["reference_seconds"] - before["reference_seconds"], 9000 / 4410
        )
        self.assertLess(restarted["reference_seconds"] - before["reference_seconds"], 0)

    def test_repeated_phrases_are_resolved_but_restart_is_rejected(self):
        rng = np.random.default_rng(826)
        phrase = rng.normal(size=12000)
        ref = np.r_[phrase, rng.normal(size=3000), phrase]
        before = dict(reference_seconds=17000 / 4410)
        expected = ref[20000:22205]
        result = match_after(ref, expected, before, 3000 / 4410)
        self.assertAlmostEqual(result["reference_seconds"], 20000 / 4410)
        self.assertGreater(result["correlation"], 0.9999)
        restarted = match_after(ref, ref[:2205], before, 3000 / 4410)
        self.assertLess(restarted["correlation"], 0.3)
        wrapped = np.r_[ref[-1000:], ref[:1205]]
        result = match_after(
            ref, wrapped, dict(reference_seconds=24000 / 4410), 2000 / 4410
        )
        self.assertAlmostEqual(result["reference_seconds"], 26000 / 4410)
        self.assertGreater(result["correlation"], 0.9999)


if __name__ == "__main__":
    unittest.main()
