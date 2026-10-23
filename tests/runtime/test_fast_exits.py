"""Fast exits still require natural room evidence, including in frozen rules."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import native_targets
import native_triggers
from runtime_versions import Rules, apply_room_exit_timing


class FastExits(unittest.TestCase):
    def modules(self):
        # Recreate the previous two-second gate as a frozen module; do not alter it.
        raw = (ROOT / 'tests/fixtures/native_triggers_delayed.txt').read_bytes()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'native_triggers.py'
            path.write_bytes(raw)
            rules = object.__new__(Rules)
            rules.frozen = True
            rules.base = Path(d)
            rules.modules = {'native_targets': native_targets}
            mod = rules.module('native_triggers')
            self.assertEqual(path.read_bytes(), raw)
            before = mod.CompletionGate.observe
            apply_room_exit_timing('native_triggers', mod)
            self.assertIs(before, mod.CompletionGate.observe)
            yield native_triggers
            yield mod

    def call(
        self,
        g,
        point,
        frame,
        *,
        spot='save10.ini',
        tick=50,
        death=0,
        restart=False,
        pos=None,
    ):
        with patch('time.monotonic', return_value=0):
            return g.observe(
                spot,
                point,
                frame,
                {},
                {},
                {'deaths': death},
                tick,
                restart,
                position=pos,
            )

    def test_zero_elapsed_time_is_enough_for_valid_room_edge(self):
        for mod in self.modules():
            for point, origin, dest, spot, reason in [
                (
                    {'frame': 23, 'category': 'rooms'},
                    23,
                    24,
                    'save10.ini',
                    'Level-Ausgang',
                ),
                (
                    {'frame': 22, 'category': 'rooms'},
                    23,
                    24,
                    'save9.ini',
                    'Level-Ausgang',
                ),
                ({'frame': 7, 'category': 'bosses'}, 7, 8, 'boss4.ini', 'Boss-Ausgang'),
            ]:
                g = mod.CompletionGate()
                self.assertIsNone(self.call(g, point, origin, spot=spot))
                self.assertEqual(self.call(g, point, dest, spot=spot, tick=1), reason)

    def test_arrival_wrong_room_death_and_reset_cannot_award(self):
        p = {'frame': 23, 'category': 'rooms'}
        for mod in self.modules():
            for kind in ('arrival', 'wrong', 'death', 'reset'):
                with self.subTest(module=mod.__file__, kind=kind):
                    g = mod.CompletionGate()
                    self.call(g, p, 24 if kind == 'arrival' else 23)
                    args = (
                        {'death': 1}
                        if kind == 'death'
                        else {'restart': True} if kind == 'reset' else {}
                    )
                    self.assertIsNone(
                        self.call(g, p, 14 if kind == 'wrong' else 24, **args)
                    )
                    self.assertIsNone(
                        self.call(g, p, 24, death=1 if kind == 'death' else 0)
                    )

    def test_tower_door_edge_is_independent_of_arrival_coordinates(self):
        p = {'frame': 51, 'category': 'rooms'}
        for mod in self.modules():
            for position, expected in [
                ((535, 200), 'Level-Ausgang'),
                ((7871, 553), 'Level-Ausgang'),
                ((7871, 559), 'Level-Ausgang'),
                (None, 'Level-Ausgang'),
            ]:
                g = mod.CompletionGate()
                self.call(g, p, 51, spot='save20.ini')
                self.assertEqual(
                    self.call(g, p, 35, spot='save20.ini', pos=position), expected
                )

    def test_resume_does_not_invent_a_room_transition(self):
        p = {'frame': 23, 'category': 'rooms'}
        for mod in self.modules():
            g = mod.CompletionGate()
            self.call(g, p, 23)
            restored = mod.CompletionGate()
            restored.restore(g.snapshot())
            self.assertIsNone(self.call(restored, p, 24))
            self.assertIsNone(self.call(restored, p, 24, tick=100))

    def test_same_room_reset_and_repeated_poll_are_not_exits(self):
        p = {'frame': 23, 'category': 'rooms'}
        for mod in self.modules():
            g = mod.CompletionGate()
            for tick in (100, 110, 1, 20):
                self.assertIsNone(self.call(g, p, 23, tick=tick))

    def test_old_sonic_and_miniboss_delays_remain_separate(self):
        from old_sonic import Gate
        from test_old_sonic_hp import sample

        g = Gate()
        self.assertFalse(g.observe('boss23.ini', 0, sample(1, 100), 0, 0))
        self.assertFalse(g.observe('boss23.ini', 0, sample(0, 101), 0, 0.1))
        self.assertFalse(g.observe('boss23.ini', 0, sample(0, 102), 0, 6.09))
        self.assertTrue(g.observe('boss23.ini', 0, sample(0, 103), 0, 6.1))
        from test_kid_icarus import pool

        for mod in self.modules():
            self.assertEqual(
                mod.exits_for('boss_kid_icarus', pool()['boss_kid_icarus']), ()
            )


if __name__ == '__main__':
    unittest.main()
