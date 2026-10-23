import unittest
import sys
import tempfile
import json
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from menu_model import Menu
from menu_controls import controls
from run_settings import LEVELS, BOSSES, encode, decode, normalize
from run_extras import SHOT_MODES, EXTRAS


class MenuControls(unittest.TestCase):
    def menu(self):
        with patch(
            'menu_model.summary', return_value={'exists': False, 'completed': False}
        ):
            return Menu(SimpleNamespace(base=ROOT))

    def test_prepared_run_consumes_seed_but_preserves_settings(self):
        m = self.menu()
        m.seed = 'PREVIOUS'
        m.seed_origin = ('shared', 'PREVIOUS', deepcopy(m.options))
        m.seed_text = 'shared'
        before = deepcopy(m.options)
        with patch(
            'menu_model.secrets.token_hex', side_effect=['previous', 'aabbccdd']
        ):
            m.consume_seed()
        self.assertEqual(m.seed, 'AABBCCDD')
        self.assertEqual(m.options, before)
        self.assertIsNone(m.seed_origin)
        self.assertEqual(m.seed_text, '')
        m.page = 'new'
        m.key(27)
        m.key(13)
        self.assertEqual(m.seed, 'AABBCCDD')

    def test_result_copy_hover_does_not_act_and_copies_complete_saved_seed(self):
        from run_settings import decode

        m = self.menu()
        m.page = 'result'
        m.result_manifest = {'seed': 'FINISHED', 'options': deepcopy(m.options)}
        m.clipboard = SimpleNamespace(put=__import__('unittest.mock').mock.Mock())
        rect = dict(controls(m))[2]
        x = (rect[0] + rect[2]) / 2
        y = (rect[1] + rect[3]) / 2
        m.hover(x, y)
        self.assertEqual(m.focus, 2)
        m.clipboard.put.assert_not_called()
        self.assertIsNone(m.action)
        with patch('runtime_versions.Rules', return_value=SimpleNamespace(base=ROOT)):
            m.click(x, y)
            code = m.clipboard.put.call_args.args[0]
            seed, options = decode(code)
            self.assertEqual(seed, 'FINISHED')
            self.assertEqual(options, normalize(m.result_manifest['options']))
            self.assertEqual(m.page, 'result')
            self.assertIsNone(m.action)
            m.focus = 0
            m.key(4099)
            self.assertEqual(m.clipboard.put.call_count, 2)
        m.focus = 2
        m.key(9)
        self.assertEqual(m.focus, 0)
        m.key(9)
        self.assertEqual(m.focus, 1)
        m.key(9)
        self.assertEqual(m.focus, 2)

    def test_advanced_horizontal_navigation_does_not_toggle_pool(self):
        m = self.menu()
        m.open_advanced()
        m.focus = 3
        before = deepcopy(m.options)
        m.key(39)
        self.assertEqual(m.focus, 3 + len(LEVELS))
        self.assertEqual(m.options, before)
        m.key(37)
        self.assertEqual(m.focus, 3)
        self.assertEqual(m.options, before)
        key = next(iter(LEVELS))
        m.key(13)
        self.assertNotIn(key, m.options['level_pool'])
        m.key(13)
        self.assertIn(key, m.options['level_pool'])

    def test_horizontal_navigation_in_single_column_visits_adjacent_options(self):
        m = self.menu()
        m.page = 'new'
        m.focus = 2
        before = deepcopy(m.options)
        m.key(39)
        self.assertEqual(m.focus, 3)
        m.key(37)
        self.assertEqual(m.focus, 2)
        self.assertEqual(m.options, before)

    def test_hover_only_focuses_and_click_toggles_exactly_once(self):
        m = self.menu()
        m.open_extras()
        before = deepcopy(m.options)
        i, rect = controls(m)[2]
        x = (rect[0] + rect[2]) / 2
        y = (rect[1] + rect[3]) / 2
        for _ in range(100):
            m.event(5, x, y)
        self.assertEqual(m.focus, i)
        self.assertEqual(m.options, before)
        m.event(3, x, y)
        key = EXTRAS[i][0]
        self.assertEqual(m.options['extras'][key], not before['extras'][key])
        changed = deepcopy(m.options)
        m.click(0, 0)
        self.assertEqual(m.options, changed)

    def test_all_visible_controls_are_reachable_by_tab_and_shift_tab(self):
        m = self.menu()
        for setup in (
            lambda: setattr(m, 'page', 'new'),
            m.open_advanced,
            m.open_extras,
            m.open_shots,
            m.open_characters,
        ):
            setup()
            ids = [i for i, _ in controls(m)]
            m.focus = ids[0]
            visited = []
            for _ in ids:
                visited.append(m.focus)
                m.key(9)
            self.assertEqual(visited, ids)
            self.assertEqual(m.focus, ids[0])
            m.key(4096)
            self.assertEqual(m.focus, ids[-1])

    def test_all_arrows_and_hover_are_non_mutating(self):
        m = self.menu()
        for setup in (
            lambda: setattr(m, 'page', 'new'),
            m.open_advanced,
            m.open_extras,
            m.open_shots,
            m.open_characters,
        ):
            setup()
            before = deepcopy(m.options)
            for focus, rect in controls(m):
                for key in (37, 38, 39, 40):
                    m.focus = focus
                    m.key(key)
                m.hover((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)
            self.assertEqual(m.options, before, m.page)

    def test_numeric_choice_requires_confirmation_and_escape_cancels(self):
        m = self.menu()
        m.open_advanced()
        old = m.options['level_count']
        m.key(13)
        self.assertEqual(m.page, 'choice')
        m.key(39)
        self.assertEqual(m.options['level_count'], old)
        m.key(27)
        self.assertEqual(m.options['level_count'], old)
        m.key(13)
        m.focus = 0
        m.key(13)
        self.assertEqual(m.options['level_count'], 0)
        self.assertEqual(m.page, 'advanced')

    def test_shot_modes_are_explicit_and_seed_roundtrip_preserves_each(self):
        m = self.menu()
        m.open_shots()
        for i, mode in enumerate(SHOT_MODES):
            rect = dict(controls(m))[i]
            m.click((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)
            self.assertEqual(m.page, 'shots')
            self.assertEqual(m.options['extras']['shot_mode'], mode)
            _, options = decode(encode('ABCDEF', m.options))
            self.assertEqual(options['extras']['shot_mode'], mode)

    def test_time_limit_separate_from_mode_and_return_to_shot_picker(self):
        m = self.menu()
        m.open_shots()
        m.focus = 5
        m.key(13)
        self.assertEqual(m.page, 'interval')
        before = list(m.interval_fields)
        m.key(39)
        self.assertEqual(m.interval_fields, before)
        m.interval_fields = ['1', '15']
        m.focus = 2
        m.key(13)
        self.assertEqual(m.page, 'shots')
        self.assertEqual(m.options['extras']['shot_interval_seconds'], 75)
        self.assertEqual(m.options['extras']['shot_mode'], 'off')
        m.focus = 1
        m.key(13)
        self.assertEqual(m.options['extras']['shot_mode'], 'random_interval')
        self.assertEqual(m.page, 'shots')

    def test_page_navigation_keeps_boss_column_and_does_not_toggle(self):
        m = self.menu()
        m.open_advanced()
        m.focus = 3 + len(LEVELS)
        before = deepcopy(m.options)
        m.key(34)
        self.assertGreaterEqual(m.focus, 3 + len(LEVELS))
        self.assertEqual(m.advanced_page, 1)
        self.assertEqual(m.options, before)
        m.key(33)
        self.assertEqual(m.advanced_page, 0)

    def test_slot_hover_does_not_switch_and_click_requests_only_selection(self):
        m = self.menu()
        rect = dict(controls(m))[4]
        x = (rect[0] + rect[2]) / 2
        y = (rect[1] + rect[3]) / 2
        m.hover(x, y)
        self.assertEqual(m.slot, 1)
        self.assertIsNone(m.requested_slot)
        m.click(x, y)
        self.assertEqual(m.requested_slot, 2)
        self.assertIsNone(m.action)

    def test_occupied_slot_delete_is_keyboard_reachable_and_confirmed(self):
        m = self.menu()
        m.saves[1] = {'exists': True}
        m.key(38)
        self.assertEqual(m.focus, 2)
        m.key(13)
        self.assertEqual(m.page, 'delete')
        self.assertIsNone(m.action)
        m.key(27)
        self.assertIsNone(m.action)


class ShotModes(unittest.TestCase):
    def test_death_spot_and_combined_change_once_per_observed_event(self):
        from shot_cycle import ShotCycle

        class Bridge:
            payload = bytes(512)

            def read(self, address, size):
                return self.payload[476:488] if size == 12 else self.payload

            def cmd(self, line):
                import struct

                command, address, style, sequence = line.split()
                assert command == 'shots'
                raw = bytearray(self.payload)
                raw[476:488] = struct.pack(
                    '<III', 0x42534531, int(style), int(sequence)
                )
                self.payload = bytes(raw)
                return {'written': True}

        for mode, expected in [
            ('death', [0, 1, 1, 2]),
            ('spot', [0, 0, 1, 2]),
            ('death_and_spot', [0, 1, 2, 3]),
        ]:
            with (
                tempfile.TemporaryDirectory() as d,
                patch('shot_cycle.initial', return_value={'name': 'A', 'frame': 0}),
                patch(
                    'shot_cycle.selection',
                    side_effect=lambda b, s, i, p: {'name': str(i), 'frame': i % 3},
                ),
            ):
                base = Path(d)
                (base / 'run').mkdir()
                m = {
                    'run_id': 'run',
                    'seed': 'seed',
                    'session_binding': 'binding',
                    'options': {'extras': {'shot_mode': mode}},
                }
                cycle = ShotCycle(
                    SimpleNamespace(base=ROOT, root=base), m, clock=lambda: 0
                )
                bridge = Bridge()
                for (deaths, spot), sequence in zip(
                    ((0, 0), (1, 0), (1, 1), (2, 2)), expected
                ):
                    cycle.observe({'deaths': deaths}, spot, bridge, 100)
                    self.assertEqual(cycle.data['sequence'], sequence, mode)
                    cycle.observe({'deaths': deaths}, spot, bridge, 100)
                    self.assertEqual(cycle.data['sequence'], sequence)

    def test_frozen_run_keeps_its_random_functions_with_new_transport(self):
        import types
        import shot_cycle
        from runtime_versions import repair_shot_transport

        frozen = types.ModuleType('frozen_shot')
        frozen.__dict__.update(shot_cycle.__dict__)
        frozen.TRANSPORT_VERSION = 0
        frozen.ShotCycle = type('OldShot', (), {})
        old_interval = lambda *args: 123
        frozen.interval = old_interval
        repair_shot_transport('shot_cycle', frozen)
        self.assertIs(frozen.ShotCycle.observe.__globals__['interval'], old_interval)
        self.assertEqual(frozen.TRANSPORT_VERSION, 1)
        self.assertIsNot(frozen.ShotCycle.observe, shot_cycle.ShotCycle.observe)

    def test_random_time_bounds(self):
        from shot_cycle import interval, ShotCycle

        for maximum in (1, 75, 300, 86400):
            for i in range(30):
                self.assertTrue(1 <= interval('seed', i, maximum) <= maximum)


if __name__ == '__main__':
    unittest.main()
