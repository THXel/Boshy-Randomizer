import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import lab
from native_player import poll_delay


class TransitionTiming(unittest.TestCase):
    def test_poll_work_counts_towards_deadline_without_busy_spin(self):
        self.assertAlmostEqual(poll_delay(10, 10.03), 0.05)
        self.assertAlmostEqual(poll_delay(10, 10.08), 0.005)
        self.assertAlmostEqual(poll_delay(10, 10.2), 0.005)

    def test_transition_confirms_spawn_without_focus_wait(self):
        b = SimpleNamespace(
            snapshot=Mock(return_value={'scene': 3, 'next': 0, 'frame_count': 2}),
            cmd=Mock(return_value={'requested': True}),
        )
        positions = {
            k: {'value': str(v)}
            for k, v in [('frame', 4), ('xpos', 100), ('ypos', 200)]
        }
        with (
            patch('lab.game_window') as window,
            patch('lab.time.sleep') as sleep,
            patch(
                'PY.file_utils.smart_read',
                return_value=('[Positions]\nframe=3\n', None),
            ),
            patch('PY.ini_utils.apply_values_in_section', return_value='prepared'),
            patch('PY.save_utils.encrypt_save_atomic', return_value=True),
            patch('lab.ini_object_ids', return_value={'Ini++': 109}),
            patch('lab.ini_items', return_value=positions),
        ):
            lab.transition(b, 4, 100, 200)
        window.assert_not_called()
        self.assertTrue(all(c.args[0] <= 0.005 for c in sleep.call_args_list))
        b.cmd.assert_called_once_with('scene 3 3')

    def test_bad_slot_never_writes_or_transitions(self):
        b = Mock()
        with self.assertRaises(ValueError):
            lab.transition(b, 4, 100, 200, '../SaveFile1.ini')
        b.cmd.assert_not_called()
