import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from types import SimpleNamespace as NS

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from menu_runtime import MenuGame, SlotSelectionError
from menu_navigation import select_requested_slot


class SlotSelection(unittest.TestCase):
    def test_every_pair_on_original_non_wrapping_menu(self):
        for start in (1, 2, 3):
            for target in (1, 2, 3):
                g = MenuGame.__new__(MenuGame)
                h = [0] * 16
                h[7] = 0
                h[9] = start
                h[15] = 1
                g.header = lambda: h[:]
                keys = []

                def key(name):
                    keys.append(name)
                    h[9] = min(3, max(1, h[9] + (1 if name == 'Right' else -1)))

                with patch('lab.key', side_effect=key):
                    g.select_slot(target)
                self.assertEqual(h[9], target)
                self.assertEqual(len(keys), abs(target - start))

    def test_missed_input_retries_then_stays_in_menu(self):
        g = MenuGame.__new__(MenuGame)
        h = [0] * 16
        h[9] = 1
        h[15] = 1
        g.header = lambda: h[:]
        with (
            patch('lab.key') as key,
            patch('menu_runtime.time.monotonic', side_effect=range(100)),
            patch('menu_runtime.time.sleep'),
        ):
            with self.assertRaises(SlotSelectionError):
                g.select_slot(3)
        self.assertEqual(key.call_count, 4)
        self.assertEqual(h[9], 1)

    def test_recovery_keeps_game_open_and_resyncs_actual_slot(self):
        h = [0] * 16
        h[9] = 2
        h[15] = 1
        g = Mock()
        g.select_slot.side_effect = SlotSelectionError('missed')
        g.header.return_value = h
        m = Mock(requested_slot=3)
        debug = Mock()
        self.assertFalse(select_requested_slot(g, m, debug))
        g.close.assert_not_called()
        m.select.assert_called_once_with(2)
        self.assertIsNone(m.requested_slot)
        self.assertIsNone(m.action)
        self.assertTrue(m.dirty)
        self.assertTrue(m.message)
        debug.error.assert_called_once()

    def test_success_selects_only_requested_slot(self):
        g = Mock()
        m = Mock(requested_slot=3)
        debug = Mock()
        self.assertTrue(select_requested_slot(g, m, debug))
        m.select.assert_called_once_with(3)
        g.close.assert_not_called()
        debug.error.assert_not_called()


if __name__ == '__main__':
    unittest.main()
