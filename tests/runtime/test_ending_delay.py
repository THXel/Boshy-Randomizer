import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from menu_runtime import EndingDelay


class EndingDelayTests(unittest.TestCase):
    def test_credits_get_fifteen_more_seconds_without_restarting_deadline(self):
        delay = EndingDelay()
        self.assertFalse(delay.ready(46, 100))
        self.assertFalse(delay.ready(47, 102))
        self.assertFalse(delay.ready(47, 116.99))
        self.assertTrue(delay.ready(47, 117))

    def test_fallback_is_twenty_seconds_after_confirmed_victory(self):
        delay = EndingDelay()
        self.assertFalse(delay.ready(46, 100))
        self.assertFalse(delay.ready(46, 119.99))
        self.assertTrue(delay.ready(46, 120))

    def test_late_credits_do_not_extend_fallback(self):
        delay = EndingDelay()
        delay.ready(46, 100)
        self.assertFalse(delay.ready(47, 118))
        self.assertTrue(delay.ready(47, 120))

    def test_credits_at_confirmation_and_scene_changes_keep_deadline(self):
        delay = EndingDelay()
        self.assertFalse(delay.ready(47, 100))
        self.assertFalse(delay.ready(48, 114.99))
        self.assertTrue(delay.ready(48, 115))


if __name__ == '__main__':
    unittest.main()
