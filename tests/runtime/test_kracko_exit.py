"""Real pre-fix rules and current rules must agree on Kracko's validated exit."""

import json
import time
import types
import unittest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import minibosses
from runtime_versions import repair_kracko_animation, repair_kracko_exit

POINT = dict(frame=5, segment='kracko', category='bosses')


def sample(t, hp=0, obj=42, position=(3400, 327), **changes):
    return dict(
        frame=5,
        tick=int(t * 100),
        hp=hp,
        boss_object=obj,
        position=position,
        player_alive=True,
        generation=[1, 2],
        **changes,
    )


def frozen():
    module = types.ModuleType('legacy_minibosses')
    path = Path(__file__).parent / 'fixtures/minibosses_before_kracko_exit.txt'
    exec(compile(path.read_text(), str(path), 'exec'), module.__dict__)
    return module


def modules():
    old = frozen()
    repair_kracko_animation('minibosses', old)
    repair_kracko_exit('minibosses', old)
    repair_kracko_exit('minibosses', old)
    return (minibosses, old)


class KrackoExit(unittest.TestCase):
    def observe(self, g, t, hp=0, obj=42, position=(3400, 327), deaths=0, **changes):
        s = sample(t, hp, obj, position)
        s.update(changes)
        return g.observe('boss2.ini', 0, POINT, s, deaths, t)

    def arm(self, g):
        self.assertIsNone(self.observe(g, 0, hp=20))
        self.assertIsNone(self.observe(g, 1, hp=-50))

    def test_original_bug_is_reproduced(self):
        g = frozen().Gate()
        self.arm(g)
        self.assertIsNone(self.observe(g, 9, hp=None, obj=None, position=(3992, 359)))
        self.assertIsNone(g.candidate)

    def test_exit_preserves_defeat_and_full_animation(self):
        for module in modules():
            for x in (3839, 3840, 3992, 4479):
                g = module.Gate()
                self.arm(g)
                self.assertIsNone(self.observe(g, 2, position=(x, 359), hp=-50))
                self.assertIsNone(
                    self.observe(g, 4.999, position=(x, 359), hp=None, obj=None)
                )
                self.assertEqual(
                    self.observe(g, 5, position=(x, 359), hp=None, obj=None),
                    'Kracko besiegt',
                )

    def test_delayed_poll_and_first_zero_sample_in_exit(self):
        for module in modules():
            g = module.Gate()
            self.arm(g)
            self.assertEqual(
                self.observe(g, 9, hp=None, obj=None, position=(3992, 359)),
                'Kracko besiegt',
            )
            g = module.Gate()
            self.observe(g, 0, hp=1)
            self.assertIsNone(self.observe(g, 1, hp=-50, position=(3992, 359)))
            self.assertEqual(
                self.observe(g, 5, hp=None, obj=None, position=(3992, 359)),
                'Kracko besiegt',
            )

    def test_other_screens_cannot_preserve_or_rearm_defeat(self):
        for module in modules():
            for position in ((3199, 327), (4480, 327), (3992, -1), (3992, 480)):
                g = module.Gate()
                self.arm(g)
                self.assertIsNone(self.observe(g, 2, position=position))
                self.assertIsNone(self.observe(g, 9, hp=-50, position=(3992, 359)))

    def test_cold_load_or_absent_boss_is_not_victory(self):
        for module in modules():
            for position in ((3400, 327), (3992, 359)):
                g = module.Gate()
                self.assertIsNone(self.observe(g, 1, position=position))
                self.assertIsNone(
                    self.observe(g, 9, hp=None, obj=None, position=position)
                )
            g = module.Gate()
            self.observe(g, 0, hp=20)
            self.assertIsNone(
                self.observe(g, 9, hp=None, obj=None, position=(3992, 359))
            )
            g = module.Gate()
            self.observe(g, 0, hp=20, position=(3992, 359))
            self.assertIsNone(self.observe(g, 1, position=(3992, 359)))
            self.assertIsNone(self.observe(g, 9, position=(3992, 359)))

    def test_death_restart_generation_and_replaced_boss_cancel(self):
        for module in modules():
            for changes in (
                {'deaths': 1},
                {'tick': 1},
                {'player_alive': False},
                {'generation': [3, 4]},
                {'obj': 99},
            ):
                g = module.Gate()
                self.arm(g)
                self.assertIsNone(self.observe(g, 8, position=(3992, 359), **changes))
                self.assertIsNone(
                    self.observe(g, 15, hp=None, obj=None, position=(3992, 359))
                )

    def test_revived_same_object_restarts_four_second_timer(self):
        for module in modules():
            g = module.Gate()
            self.arm(g)
            self.assertIsNone(self.observe(g, 4, hp=20))
            self.assertIsNone(self.observe(g, 5, hp=-50))
            self.assertIsNone(self.observe(g, 8.9, hp=None, obj=None))
            self.assertEqual(self.observe(g, 9, hp=None, obj=None), 'Kracko besiegt')

    def test_saved_observation_cannot_complete_in_new_generation(self):
        for module in modules():
            g = module.Gate()
            self.arm(g)
            data = g.snapshot()
            g = module.Gate()
            g.restore(data)
            self.assertIsNone(
                self.observe(
                    g,
                    time.monotonic() + 10,
                    hp=None,
                    obj=None,
                    position=(3992, 359),
                    generation=[3, 4],
                )
            )

    def test_frozen_adapter_delegates_other_stages_and_reader_validation(self):
        old = frozen()
        observe = Mock(return_value='frozen result')
        reader = Mock(return_value={'frame': 5})
        old.Gate.observe = observe
        old.Reader.sample = reader
        repair_kracko_exit('minibosses', old)
        repair_kracko_exit('minibosses', old)
        gate = old.Gate()
        other = dict(frame=31, segment='ninja_ryu')
        self.assertEqual(
            gate.observe('boss16.ini', 3, other, None, 0, 2), 'frozen result'
        )
        observe.assert_called_once_with(gate, 'boss16.ini', 3, other, None, 0, 2)
        r = old.Reader()
        bridge = object()
        snap = dict(scene=4, run=100, object_list=200)
        self.assertEqual(r.sample(bridge, snap), dict(frame=5, generation=[100, 200]))
        reader.assert_called_once_with(r, bridge, snap)
        reader.side_effect = RuntimeError('Unbekannte Kracko-Todesbedingung.')
        with self.assertRaisesRegex(RuntimeError, 'Kracko'):
            r.sample(bridge, snap)

    def test_progress_requests_only_one_destination_after_crossing(self):
        from test_kid_icarus import options, pool
        from native_progress import Progress

        for module in modules():
            with tempfile.TemporaryDirectory() as folder:
                root = Path(folder)
                (root / 'run').mkdir()
                m = dict(
                    run_id='run',
                    session_binding='test',
                    seed='KRACKO',
                    options=options(9),
                    pool=pool(9),
                )
                p = Progress(
                    types.SimpleNamespace(
                        base=Path(minibosses.__file__).parent, root=root
                    ),
                    m,
                )
                p.data['spot'] = 'boss2.ini'
                p.mini_gate = module.Gate()

                def observe(t, hp, obj, position):
                    with patch.object(module.time, 'monotonic', return_value=t):
                        return p.observe(
                            frame=5,
                            position=(3400, 300),
                            collectables={},
                            achievements={},
                            disk_achievements={},
                            stats={'deaths': 0},
                            scene_tick=int(t * 100),
                            mini_sample=sample(t, hp, obj, position),
                        )

                self.assertIsNone(observe(0, 20, 42, (3400, 327)))
                self.assertIsNone(observe(1, -50, 42, (3400, 327)))
                dest = observe(9, None, None, (3992, 359))
                self.assertIsNotNone(dest)
                self.assertEqual(observe(10, None, None, (3992, 359)), dest)
                requests = [
                    r
                    for r in p.data['transition_trace']
                    if r['event'] == 'transition-requested'
                ]
                self.assertEqual(len(requests), 1)
                self.assertEqual(requests[0]['reason'], 'Kracko besiegt')


if __name__ == '__main__':
    unittest.main()
