"""Regression for the recorded Old Sonic victory followed by Endless (60 -> 61)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import native_targets
from native_triggers import CompletionGate, BOSS_EXITS
from runtime_versions import Rules, correct_known_exits
from native_progress import Progress

POINT = {'frame': 60, 'x': 100, 'y': 100, 'category': 'bosses'}


def observe(g, frame, now, won=2, deaths=0, tick=100, restart=False):
    with patch('native_triggers.time.monotonic', return_value=now):
        return g.observe(
            'boss23.ini',
            POINT,
            frame,
            {'sonic': won},
            {'sonic': won},
            {'deaths': deaths},
            tick,
            restart,
        )


class OldSonicExit(unittest.TestCase):
    def test_recorded_victory_advances_at_real_exit_not_on_shared_flag(self):
        g = CompletionGate()
        for frame, t, flag in [(60, 0, 0), (60, 6.51, 1), (60, 8.49, 2)]:
            self.assertIsNone(observe(g, frame, t, flag))
        self.assertEqual(observe(g, 61, 11.95), 'Boss-Ausgang')

    def test_wrong_normal_sonic_exit_does_not_complete_old_sonic(self):
        g = CompletionGate()
        observe(g, 60, 0)
        self.assertIsNone(observe(g, 15, 1))
        self.assertIsNone(observe(g, 15, 5))
        self.assertEqual(BOSS_EXITS[14], (15,))
        self.assertEqual(BOSS_EXITS[60], (61,))

    def test_arrival_death_and_reset_alone_do_not_complete(self):
        for label, sequence in [
            ('arrival', [(61, 0, 0, 100, False), (61, 4, 0, 200, False)]),
            (
                'death',
                [(60, 0, 0, 100, False), (61, 1, 1, 10, False), (61, 4, 1, 100, False)],
            ),
            (
                'reset',
                [(60, 0, 0, 100, False), (60, 1, 0, 1, True), (60, 4, 0, 100, False)],
            ),
            (
                'stale shared achievement',
                [(60, 0, 0, 100, False), (60, 4, 0, 200, False)],
            ),
        ]:
            with self.subTest(label=label):
                g = CompletionGate()
                for f, t, d, tick, r in sequence:
                    self.assertIsNone(
                        observe(
                            g,
                            f,
                            t,
                            won=0 if label == 'death' else 2,
                            deaths=d,
                            tick=tick,
                            restart=r,
                        )
                    )

    def test_death_in_exit_room_does_not_erase_confirmed_victory(self):
        g = CompletionGate()
        observe(g, 60, 0, won=0)
        observe(g, 60, 1, won=2)
        self.assertEqual(observe(g, 61, 2, won=2, deaths=1), 'Boss-Ausgang')

    def test_exit_without_both_saved_victory_flags_cannot_award(self):
        g = CompletionGate()
        observe(g, 60, 0, won=0)
        self.assertIsNone(observe(g, 61, 1, won=0))
        self.assertIsNone(observe(g, 61, 5, won=0))

    def test_saved_win_without_observed_exit_does_not_finish_on_resume(self):
        g = CompletionGate()
        observe(g, 60, 0)
        fresh = CompletionGate()
        fresh.restore(g.snapshot())
        self.assertIsNone(observe(fresh, 61, 10))
        self.assertIsNone(observe(fresh, 61, 14))

    def test_saved_rule_module_corrected_without_changing_bundle_bytes(self):
        # Use a real frozen-module import with the old, incorrect exit table.
        raw = (ROOT / 'tests/fixtures/native_triggers_old_sonic.txt').read_bytes()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'native_triggers.py'
            p.write_bytes(raw)
            rules = object.__new__(Rules)
            rules.frozen = True
            rules.base = Path(d)
            rules.modules = {'native_targets': native_targets}
            mod = rules.module('native_triggers')
            self.assertEqual(mod.BOSS_EXITS[60], (61,))
            self.assertEqual(p.read_bytes(), raw)
            self.assertEqual(mod.BOSS_EXITS, {**BOSS_EXITS})
            self.assertIs(rules.module('native_triggers'), mod)
            g = mod.CompletionGate()
            with patch('time.monotonic', return_value=0):
                g.observe('boss23.ini', POINT, 60, {}, {}, {})
            with patch('time.monotonic', return_value=1):
                self.assertEqual(
                    g.observe(
                        'boss23.ini',
                        POINT,
                        61,
                        {'sonic': 2},
                        {'sonic': 2},
                        {'deaths': 1},
                    ),
                    'Boss-Ausgang',
                )

    def test_compatibility_only_changes_known_erroneous_exit(self):
        for name, exits in [
            ('other', {60: (15,)}),
            ('native_triggers', {60: (99,)}),
            ('native_triggers', {}),
        ]:
            module = SimpleNamespace(BOSS_EXITS=dict(exits))
            correct_known_exits(name, module)
            self.assertEqual(module.BOSS_EXITS, exits)

    def test_route_and_target_mode_both_credit_old_sonic_without_adding_endless(self):
        for mode in ('randomizer', 'target'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / 'run').mkdir()
                pool = {
                    'boss23.ini': POINT,
                    'save1.ini': {'frame': 3, 'x': 30, 'y': 40, 'category': 'rooms'},
                    'boss_solgryn.ini': {
                        'frame': 46,
                        'x': 100,
                        'y': 100,
                        'category': 'bosses',
                    },
                }
                options = {'levels': True, 'route_version': 5, 'mode': mode}
                m = {
                    'run_id': 'run',
                    'session_binding': 'binding',
                    'seed': '1234ABCD',
                    'options': options,
                    'pool': pool,
                }
                with (
                    patch(
                        'native_progress.goals',
                        return_value={'items': [], 'bosses': ['oldsonic']},
                    ),
                    patch('run_settings.route', return_value=list(pool)),
                ):
                    progress = Progress(SimpleNamespace(root=root, base=ROOT), m)
                for f, t, flag in [(60, 0, 0), (60, 1, 2), (61, 2, 2), (61, 4.1, 2)]:
                    with patch('native_triggers.time.monotonic', return_value=t):
                        target = progress.observe(
                            frame=f,
                            position=(100, 100),
                            collectables={},
                            achievements={'sonic': flag},
                            disk_achievements={'sonic': flag},
                            stats={},
                        )
                self.assertEqual(
                    target, 'boss_solgryn.ini' if mode == 'target' else 'save1.ini'
                )
                self.assertIn('oldsonic', progress.data['stage_bosses'])
                self.assertNotIn('sonic', progress.data['stage_bosses'])
                self.assertNotEqual(progress.destination(target)['frame'], 61)
        from native_level_route import catalogue

        pool = catalogue(json.loads((ROOT / 'INI/positions.json').read_text()))
        self.assertNotIn(61, [p['frame'] for p in pool.values()])


if __name__ == '__main__':
    unittest.main()
