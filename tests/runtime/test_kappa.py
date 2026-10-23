import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from test_kid_icarus import options, pool
from minibosses import Gate
from native_triggers import exits_for
import run_settings as r
import seed_share


def sample(
    hp=50,
    boss=42,
    intro=False,
    tick=100,
    position=(2175, 1864),
    alive=True,
    generation=(1, 2),
):
    return dict(
        frame=37,
        tick=tick,
        hp=hp,
        boss_object=boss,
        intro_active=intro,
        player_alive=alive,
        position=position,
        generation=generation,
    )


class Kappa(unittest.TestCase):
    def test_confirmed_spawns_and_separate_boss_seed(self):
        p = pool(8)
        self.assertEqual((p['boss_kappa']['x'], p['boss_kappa']['y']), (2175, 1864))
        self.assertEqual(
            (p['boss_kid_icarus']['x'], p['boss_kid_icarus']['y']), (777, 6607)
        )
        self.assertEqual((p['boss21.ini']['x'], p['boss21.ini']['y']), (213, 447))
        self.assertEqual(exits_for('save17.ini', p['save17.ini']), ())
        self.assertEqual(exits_for('boss_kappa', p['boss_kappa']), (29,))
        self.assertEqual(exits_for('save17.ini', pool(7)['save17.ini']), (29,))
        o = options(9)
        o.update(level_count=0, boss_pool=['kappa'], route_boss_count=1)
        code = seed_share.encode('1234ABCD', o, ROOT)
        seed, decoded = r.decode(code)
        self.assertEqual(decoded, o)
        self.assertEqual(r.route(seed, decoded)[0], 'boss_kappa')

    def test_target_desert_does_not_reuse_checkpoint_outside_start_hole(self):
        import tempfile
        from types import SimpleNamespace
        from native_progress import Progress

        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'run').mkdir()
            o = options(8, 'target')
            m = dict(
                run_id='run',
                session_binding='test',
                seed='DESERT',
                options=o,
                pool=pool(8),
            )
            store = SimpleNamespace(base=ROOT, root=root)
            p = Progress(store, m)
            p.m['pool'] = {
                'save15.ini': m['pool']['save15.ini'],
                'boss_kappa': m['pool']['boss_kappa'],
            }
            p.data['spot'] = 'boss_kappa'
            p.data['checkpoints'] = {'35': [800, 900]}
            p.request({}, 37, 'Kappa besiegt', {})
            self.assertEqual(
                (p.destination('save15.ini')['x'], p.destination('save15.ini')['y']),
                (50, 447),
            )

    def test_screen_crossing_not_spawn(self):
        p = pool(8)['save17.ini']
        g = Gate()
        self.assertIsNone(g.observe('save17.ini', 0, p, sample(), 0, 0))
        self.assertIsNone(
            g.observe('save17.ini', 0, p, sample(position=(1900, 1864), tick=110), 0, 1)
        )
        self.assertEqual(
            g.observe('save17.ini', 0, p, sample(tick=120), 0, 2), 'Miniboss-Eingang'
        )

    def test_native_death_animation_and_reward_screen_do_not_finish_stage(self):
        p = pool(8)['boss_kappa']
        g = Gate()
        for now, s in enumerate(
            (
                sample(hp=None, boss=None),
                sample(intro=True, tick=110),
                sample(tick=120),
                sample(hp=0, tick=130),
                sample(hp=-1, tick=140),
                sample(hp=-1, tick=200),
            )
        ):
            self.assertIsNone(g.observe('boss_kappa', 0, p, s, 0, now))
        self.assertIsNone(
            g.observe('boss_kappa', 0, p, sample(hp=None, boss=None, tick=210), 0, 6)
        )
        self.assertIsNone(
            g.observe(
                'boss_kappa',
                0,
                p,
                sample(hp=None, boss=None, tick=220, position=(2900, 1850)),
                0,
                30,
            )
        )

    def test_reset_death_and_generation_never_award(self):
        p = pool(8)['boss_kappa']
        for changes, deaths in [
            ({'tick': 1}, 0),
            ({}, 1),
            ({'alive': False}, 0),
            ({'generation': (3, 4)}, 0),
        ]:
            g = Gate()
            g.observe('boss_kappa', 0, p, sample(), 0, 0)
            g.observe('boss_kappa', 0, p, sample(hp=-1, tick=110), 0, 1)
            self.assertIsNone(
                g.observe(
                    'boss_kappa', 0, p, sample(hp=None, boss=None, **changes), deaths, 4
                )
            )

    def test_reward_room_waits_for_portal_in_both_modes(self):
        import tempfile
        from types import SimpleNamespace
        from unittest.mock import Mock
        from native_progress import Progress

        for mode in ('randomizer', 'target'):
            with tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / 'run').mkdir()
                o = options(8, mode)
                m = dict(
                    run_id='run',
                    session_binding='test',
                    seed='KAPPA',
                    options=o,
                    pool=pool(8),
                )
                store = SimpleNamespace(base=ROOT, root=root)
                p = Progress(store, m)
                p.data['spot'] = 'boss_kappa'
                p.goals = {'items': ['scouter'], 'bosses': ['kappa']}
                p.request = Mock(return_value='NEXT')

                def observe(frame, tick, mini=None):
                    return p.observe(
                        frame=frame,
                        position=(2930, 1850),
                        collectables={},
                        disk_collectables={},
                        achievements={},
                        disk_achievements={},
                        stats={'deaths': 0},
                        scene_tick=tick,
                        mini_sample=mini,
                    )

                for tick, hp, boss in [
                    (100, 50, 42),
                    (110, -1, 42),
                    (120, None, None),
                    (2000, None, None),
                ]:
                    self.assertIsNone(
                        observe(37, tick, sample(hp=hp, boss=boss, tick=tick))
                    )
                p.request.assert_not_called()
                self.assertNotIn('kappa', p.data.get('stage_bosses', {}))
                self.assertEqual(observe(29, 1), 'NEXT')
                self.assertEqual(p.data['stage_bosses']['kappa']['frame'], 29)
                self.assertEqual(p.request.call_args.args[2], 'Boss-Ausgang')

    def test_saved_kappa_rules_are_corrected_without_affecting_other_minibosses(self):
        from types import SimpleNamespace
        from unittest.mock import Mock
        from runtime_versions import repair_kappa_exit

        class OldGate:
            observe = Mock(return_value='old victory')
            reset = Mock()

        frozen = SimpleNamespace(Gate=OldGate)
        triggers = SimpleNamespace(exits_for=lambda spot, point: ())
        repair_kappa_exit('minibosses', frozen)
        repair_kappa_exit('native_triggers', triggers)
        point = pool(8)['boss_kappa']
        g = OldGate()
        self.assertIsNone(g.observe('boss_kappa', 0, point, sample(hp=-1), 0, 99))
        g.reset.assert_called_once()
        self.assertEqual(triggers.exits_for('boss_kappa', point), (29,))
        self.assertEqual(
            g.observe('boss2.ini', 0, pool(8)['boss2.ini'], sample(), 0, 99),
            'old victory',
        )
        self.assertEqual(triggers.exits_for('boss2.ini', pool(8)['boss2.ini']), ())
