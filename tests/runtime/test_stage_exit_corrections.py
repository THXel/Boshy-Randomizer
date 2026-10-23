"""User-confirmed bypass and split exits, including archived seed rules."""

import sys
import tempfile
import threading
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import native_targets
import native_triggers
from runtime_versions import Rules, repair_stage_exits
from test_kid_icarus import pool
from fast_exit import FastExit
from minibosses import Gate

EXPECTED = {'save2.ini': (6,), 'save9.ini': (23, 53), 'save10.ini': (24,)}


class StageExitCorrections(unittest.TestCase):
    def modules(self):
        raw = (
            ROOT / 'tests/fixtures/native_triggers_before_stage_exits.txt'
        ).read_bytes()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'native_triggers.py'
            path.write_bytes(raw)
            rules = object.__new__(Rules)
            rules.frozen = True
            rules.base = Path(folder)
            rules.modules = {'native_targets': native_targets}
            module = rules.module('native_triggers')
            self.assertEqual(path.read_bytes(), raw)
            before = module.exits_for
            repair_stage_exits('native_triggers', module)
            self.assertIs(before, module.exits_for)
            yield native_triggers
            yield module

    def observe(self, g, spot, frame, **kw):
        return g.observe(
            spot, pool(9)[spot], frame, {}, {}, {'deaths': kw.pop('deaths', 0)}, **kw
        )

    def test_only_confirmed_exits_for_current_and_archived_rules(self):
        for module in self.modules():
            for spot, allowed in EXPECTED.items():
                point = pool(9)[spot]
                self.assertEqual(module.exits_for(spot, point), allowed)
                for frame in range(1, 62):
                    gate = module.CompletionGate()
                    self.observe(gate, spot, point['frame'], tick=100)
                    result = self.observe(gate, spot, frame, tick=110)
                    self.assertEqual(
                        result,
                        'Level-Ausgang' if frame in allowed else None,
                        (spot, frame),
                    )

    def test_cold_arrival_death_and_restart_do_not_complete(self):
        for module in self.modules():
            for spot, allowed in EXPECTED.items():
                for dest in allowed:
                    gate = module.CompletionGate()
                    self.assertIsNone(self.observe(gate, spot, dest))
                    self.assertIsNone(self.observe(gate, spot, dest))
                    for changes in ({'deaths': 1}, {'restart_pressed': True}):
                        gate = module.CompletionGate()
                        self.observe(gate, spot, pool(9)[spot]['frame'], tick=100)
                        self.assertIsNone(
                            self.observe(gate, spot, dest, tick=110, **changes)
                        )

    def test_native_interception_uses_same_corrected_exit_masks(self):
        for module in self.modules():
            for spot, expected in EXPECTED.items():
                point = pool(9)[spot]
                gate = module.CompletionGate()
                self.observe(gate, spot, point['frame'])
                player = SimpleNamespace(
                    m={'options': {'levels': True}, 'pool': {spot: point}},
                    progress=SimpleNamespace(
                        data={'spot': spot, 'pending': None}, gate=gate
                    ),
                    watch=SimpleNamespace(down=False, pressed=threading.Event()),
                    rules=SimpleNamespace(module=lambda name: module),
                )
                self.assertEqual(FastExit(player).allowed(point['frame']), expected)

    def test_unrelated_and_unsplit_legacy_rules_are_preserved(self):
        for module in self.modules():
            for version in (5, 6):
                for spot in ('save9.ini', 'save10.ini'):
                    point = pool(version)[spot]
                    self.assertEqual(module.exits_for(spot, point), (24, 53))
                    self.assertEqual(module.stage_frames(spot, point), (22, 23))
            points = pool(9)
            for spot in (
                'save1.ini',
                'save23.ini',
                'boss2.ini',
                'boss3.ini',
                'save7.ini',
                'boss_kappa',
            ):
                self.assertEqual(
                    module.exits_for(spot, points[spot]),
                    native_triggers.exits_for(spot, points[spot]),
                )

    def test_removed_persisted_exit_candidate_cannot_complete(self):
        for module in self.modules():
            for spot, dest in [('save9.ini', 24), ('save10.ini', 53)]:
                gate = module.CompletionGate()
                point = pool(9)[spot]
                gate.restore(
                    dict(
                        rule_version=3,
                        identity=[spot, point['frame']],
                        seen_origin=True,
                        previous={},
                        candidate='Level-Ausgang',
                        candidate_frame=dest,
                        deaths=0,
                        won=False,
                    )
                )
                self.assertIsNone(self.observe(gate, spot, dest))
                self.assertIsNone(gate.candidate)

    def test_kracko_arena_entry_remains_an_additional_exit(self):
        gate = Gate()
        point = pool(9)['save2.ini']

        def sample(x, tick):
            return dict(
                frame=5,
                tick=tick,
                player_alive=True,
                position=[x, 300],
                hp=20,
                boss_object=42,
                generation=[1, 2],
            )

        self.assertIsNone(gate.observe('save2.ini', 0, point, sample(3190, 100), 0, 0))
        self.assertEqual(
            gate.observe('save2.ini', 0, point, sample(3210, 110), 0, 1),
            'Miniboss-Eingang',
        )


if __name__ == '__main__':
    unittest.main()
