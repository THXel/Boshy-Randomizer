import ast
import json
import sys
import tempfile
import unittest
import zipfile
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import run_settings as r
import seed_share as share
from run_extras import EXTRAS, SHOT_MODES
from menu_model import Menu
from menu_controls import controls
from menu_help import help_for, preview_rows, HELP
from trigger_explanation import explain


class SeedPolish(unittest.TestCase):
    def menu(self):
        with patch(
            'menu_model.summary', return_value={'exists': False, 'completed': False}
        ):
            return Menu(NS(base=ROOT))

    def test_all_hack_and_shot_combinations_roundtrip(self):
        m = self.menu()
        for mask in range(1 << len(EXTRAS)):
            for i, mode in enumerate(SHOT_MODES):
                o = deepcopy(m.options)
                o['extras'].update(
                    {row[0]: bool(mask & (1 << k)) for k, row in enumerate(EXTRAS)}
                )
                o['extras'].update(
                    shot_mode=mode, shot_interval_seconds=(1, 59, 60, 300, 86400)[i]
                )
                code = share.encode('1234ABCD', o, ROOT)
                self.assertEqual(r.decode(code), ('1234ABCD', r.normalize(o)))
                self.assertEqual(share.compatibility(code, ROOT)['status'], 'matching')
                self.assertLess(len(code), 80)

    def test_imported_identity_and_unknown_rules_are_not_relabelled(self):
        m = self.menu()
        code = share.encode('SHARED', m.options, ROOT)
        m.import_seed(code)
        m.open_seed()
        self.assertEqual(m.seed_text, code)
        self.assertEqual(share.compatibility(code, ROOT)['status'], 'matching')
        with tempfile.TemporaryDirectory() as d:
            self.assertEqual(
                share.compatibility(share.encode('X', m.options, Path(d)), ROOT)[
                    'status'
                ],
                'unknown',
            )

    def test_rule_mismatch_and_corruption(self):
        m = self.menu()
        code = share.encode('X', m.options, ROOT)
        with patch('seed_share.fingerprint', return_value=b'12345678'):
            self.assertEqual(share.compatibility(code, ROOT)['status'], 'different')
        for i in range(4, len(code)):
            with self.assertRaises(ValueError):
                r.decode(code[:i] + ('A' if code[i] != 'A' else 'B') + code[i + 1 :])
        for bad in (code + '=', code[:-1], 'BR5-', 'BR5-' + ('A' * 1100)):
            with self.assertRaises(ValueError):
                r.decode(bad)

    def test_preview_cancel_and_confirm(self):
        m = self.menu()
        old = (m.seed, deepcopy(m.options))
        o = deepcopy(m.options)
        o['difficulty'] = 3
        o['extras']['god_mode'] = True
        m.open_seed()
        m.seed_text = share.encode('IMPORTED', o, ROOT)
        m.focus = 4
        m.key(13)
        self.assertEqual(m.page, 'seed_preview')
        self.assertEqual((m.seed, m.options), old)
        m.key(27)
        self.assertEqual((m.seed, m.options), old)
        m.focus = 4
        m.key(13)
        m.focus = 2
        m.key(13)
        self.assertEqual(m.seed, 'IMPORTED')
        self.assertEqual(m.options, r.normalize(o))
        self.assertEqual(m.page, 'new')

    def test_invalid_paste_and_typed_code_keep_current_settings(self):
        m = self.menu()
        m.open_seed()
        before = (m.seed, deepcopy(m.options), m.seed_text)
        m.clipboard = NS(get=lambda: 'BR5-broken')
        m.paste_seed()
        self.assertEqual((m.seed, m.options, m.seed_text), before)
        m.seed_text = 'BR5-broken'
        m.focus = 4
        m.key(13)
        self.assertEqual(m.page, 'seed')
        self.assertEqual((m.seed, m.options), before[:2])

    def test_preview_shows_equal_count_pool_changes_and_all_hacks(self):
        m = self.menu()
        a = deepcopy(m.options)
        a['level_pool'] = a['level_pool'][:-1]
        b = deepcopy(m.options)
        b['level_pool'] = b['level_pool'][1:]
        rows = preview_rows('X', a, 'X', b)
        self.assertEqual(sum(row[3] for row in rows), 3)
        self.assertGreater(len(preview_rows('X', m.options, 'X', m.options)), 20)

    def test_advanced_discard_nested_changes(self):
        m = self.menu()
        before = deepcopy(m.options)
        m.open_advanced()
        m.focus = 3
        m.key(13)
        m.open_extras()
        m.focus = 3
        m.key(13)
        m.key(27)
        self.assertEqual(m.page, 'advanced')
        m.key(27)
        self.assertEqual(m.page, 'discard')
        m.focus = 1
        m.key(13)
        self.assertEqual(m.options, before)
        self.assertEqual(m.page, 'new')

    def test_advanced_apply_and_continue(self):
        m = self.menu()
        m.open_advanced()
        m.focus = 3
        m.key(13)
        changed = deepcopy(m.options)
        m.key(27)
        m.key(27)
        self.assertEqual(m.page, 'advanced')
        self.assertEqual(m.options, changed)
        m.key(27)
        m.focus = 0
        m.key(13)
        self.assertEqual(m.options, changed)
        self.assertEqual(m.page, 'new')

    def test_target_hacks_discard_and_apply(self):
        m = self.menu()
        m.options['mode'] = 'target'
        before = deepcopy(m.options)
        m.open_advanced()
        self.assertEqual(m.page, 'extras')
        m.focus = 3
        m.key(13)
        m.key(27)
        self.assertEqual(m.page, 'discard')
        m.focus = 1
        m.key(13)
        self.assertEqual(m.options, before)
        m.open_advanced()
        m.focus = 3
        m.key(13)
        m.focus = len(EXTRAS)
        m.key(13)
        self.assertEqual(m.page, 'new')
        self.assertTrue(m.options['extras']['god_mode'])

    def test_invalid_empty_route_cannot_apply(self):
        m = self.menu()
        m.open_advanced()
        m.options.update(level_count=0, route_boss_count=0)
        m.finish_advanced(True)
        self.assertEqual(m.page, 'advanced')
        self.assertTrue(m.message)
        m.key(27)
        m.focus = 1
        m.key(13)
        self.assertEqual(m.page, 'new')
        self.assertEqual(m.options['level_count'], 7)

    def test_mouse_and_keyboard_share_help(self):
        m = self.menu()
        m.page = 'new'
        m.focus = 8
        expected = help_for(m)
        m.focus = 0
        rect = dict(controls(m))[8]
        m.hover((rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2)
        self.assertEqual(help_for(m), expected)

    def test_preview_paging_and_keyboard_reachability(self):
        m = self.menu()
        m.open_seed()
        m.open_preview()
        m.key(34)
        self.assertEqual(m.preview_page, 1)
        m.key(33)
        self.assertEqual(m.preview_page, 0)
        ids = [i for i, _ in controls(m)]
        m.focus = ids[0]
        seen = []
        for _ in ids:
            seen.append(m.focus)
            m.key(9)
        self.assertEqual(ids, seen)

    def player(self, spot='boss23.ini', point=None, observed=None, data=None):
        point = point or dict(frame=60, category='bosses')
        d = dict(spot=spot, completion_gate={'seen_origin': True}, **(data or {}))
        return NS(
            m={'pool': {spot: point}, 'options': {'levels': True}},
            progress=NS(data=d, goals={}),
            debug_sample=observed or {},
            last={},
        )

    def test_diagnostic_priorities_and_evidence(self):
        p = self.player(
            observed={
                'old_sonic': {'hp': 0, 'player_alive': True, 'cooldown_remaining': 2.5},
                'frame': 60,
            }
        )
        s = explain(p)
        self.assertEqual(s['state'], 'death_animation')
        self.assertEqual(s['evidence']['boss']['hp'], 0)
        p.debug_sample['restart_down'] = True
        self.assertEqual(explain(p)['state'], 'reset_guard')
        p.progress.data['pending'] = 'save1.ini'
        self.assertEqual(explain(p)['state'], 'pending')
        p.progress.data['dialog_wait'] = True
        self.assertEqual(explain(p)['state'], 'dialog_wait')
        p.last = {'completed': True}
        self.assertEqual(explain(p)['state'], 'completed')

    def test_diagnostics_do_not_mutate_gates(self):
        p = self.player(
            'boss2.ini',
            dict(frame=5, category='bosses', segment='kracko'),
            data={'miniboss_gate': {'armed': False}},
        )
        before = deepcopy(p.progress.data)
        self.assertEqual(explain(p)['state'], 'arrival_guard')
        self.assertEqual(before, p.progress.data)
        p.progress.data['miniboss_gate']['armed'] = True
        self.assertEqual(explain(p)['state'], 'waiting_miniboss')

    def test_export_has_structured_trigger_evidence(self):
        from debug_data import Recorder

        with tempfile.TemporaryDirectory() as d:
            path = Recorder(d).finish(
                'Test',
                {
                    'sequence': 1,
                    'trigger_explanation': explain(
                        self.player(observed={'restart_down': True})
                    ),
                },
            )
            with zipfile.ZipFile(path) as z:
                self.assertEqual(
                    json.loads(z.read('trigger-evidence.json'))['state'], 'reset_guard'
                )

    def test_new_dynamic_messages_have_all_translations(self):
        import ui_i18n as ui

        keys = {text for pair in HELP.values() for text in pair}
        tree = ast.parse((ROOT / 'trigger_explanation.py').read_text())
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == 'reason' for t in node.targets
                )
                and isinstance(node.value, ast.Constant)
            ):
                keys.add(node.value.value)
        for lang in ui.SUPPORTED:
            for key in keys:
                self.assertIn(key, ui.catalog(lang), (lang, key))


if __name__ == '__main__':
    unittest.main()
