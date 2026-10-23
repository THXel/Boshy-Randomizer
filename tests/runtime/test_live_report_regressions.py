"""Regressions from the 2026-10-22 stream and Windows 11 startup report."""

import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from menu_model import Menu
from menu_controls import controls
from run_settings import BOSSES, LEVELS, ADVANCED_PAGES
from run_extras import EXTRAS
import game_focus
import ui_i18n
from lab import Bridge


class SettingsEdits(unittest.TestCase):
    def menu(self):
        with patch(
            'menu_model.summary', return_value={'exists': False, 'completed': False}
        ):
            return Menu(NS(base=ROOT))

    def changed(self, menu, action):
        before = menu.seed
        action()
        self.assertNotEqual(menu.seed, before)
        self.assertIsNone(menu.seed_origin)
        self.assertEqual(menu.seed_text, '')

    def test_every_gameplay_control_renews_seed(self):
        m = self.menu()
        m.page = 'new'
        for focus in (3, 4, 5):
            m.focus = focus
            self.changed(m, lambda: m.key(13))
        for name, value in [('difficulty', 3), ('mode', 'target')]:
            m.open_choice(name, [(value, str(value))], name)
            self.changed(m, lambda: m.key(13))
        m.open_extras()
        for i, (name, *_rest) in enumerate(EXTRAS):
            if name in ('sprite_scenery', 'music'):
                continue
            m.page = 'extras'
            m.focus = i
            self.changed(m, lambda: m.key(13))
        for focus in range(6):
            m.page = 'graphics'
            m.focus = focus
            self.changed(m, lambda: m.key(13))
        m.page = 'shots'
        m.focus = 2
        self.changed(m, lambda: m.key(13))
        m.open_interval()
        m.interval_fields = ['1', '23']
        m.focus = 2
        self.changed(m, lambda: m.key(13))

    def test_pool_character_preset_and_mouse_edits(self):
        m = self.menu()
        m.open_advanced()
        m.focus = 3
        self.changed(m, lambda: m.key(13))
        m.focus = 3 + len(LEVELS)
        self.changed(m, lambda: m.key(13))
        m.page = 'characters'
        m.character_names = ['Mario']
        m.focus = 0
        self.changed(m, lambda: m.key(13))
        m.page = 'presets'
        m.focus = 2
        self.changed(m, lambda: m.key(13))
        m.page = 'new'
        rect = dict(controls(m))[4]
        self.changed(m, lambda: m.click(rect[0] + 2, rect[1] + 2))

    def test_navigation_and_same_value_do_not_reroll(self):
        m = self.menu()
        before = m.seed
        m.page = 'new'
        m.key(9)
        m.key(40)
        m.hover(500, 400)
        m.open_choice('Schwierigkeit', [(1, 'Average')], 'difficulty')
        m.key(13)
        self.assertEqual(m.seed, before)

    def test_imported_seed_survives_apply_but_not_edit(self):
        from seed_share import encode

        m = self.menu()
        options = copy.deepcopy(m.options)
        options['difficulty'] = 3
        code = encode(m.seed, options, ROOT)
        m.open_seed()
        m.seed_text = code
        m.open_preview()
        m.focus = 2
        before = m.seed
        m.key(13)
        self.assertEqual(m.seed, before)
        self.assertEqual(m.options['difficulty'], 3)
        m.focus = 4
        self.changed(m, lambda: m.key(13))

    def test_all_bosses_including_gravitron_have_reachable_controls(self):
        for mode in ('randomizer', 'boss_rush'):
            m = self.menu()
            m.change_mode(mode)
            m.open_advanced()
            seen = set()
            for page in range(ADVANCED_PAGES):
                m.advanced_page = page
                seen.update(
                    i - 3 - len(LEVELS)
                    for i, _ in controls(m)
                    if 3 + len(LEVELS) <= i < 3 + len(LEVELS) + len(BOSSES)
                )
            self.assertEqual(seen, set(range(len(BOSSES))))
            self.assertIn(list(BOSSES).index('gravitron'), seen)


class RouteCommit(unittest.TestCase):
    def test_captured_exit_commits_before_scene_request(self):
        from native_player import Player
        from contextlib import nullcontext

        calls = []
        point = {'frame': 27, 'x': 777, 'y': 6607}
        p = Player.__new__(Player)
        p.bridge = object()
        p.metadata = {'menu': 123}
        p.characters = None
        p.m = {'pool': {}}
        p.save_name = 'SaveFile3.ini'
        p.progress = NS(
            destination=lambda d: point, arrive=lambda *a: calls.append('arrive')
        )
        p.fast_exit = NS(
            release=lambda frame, committed: calls.append(('release', frame, committed))
        )
        p.transition_timings = NS(complete=lambda: calls.append('complete'))
        p.watch = NS(pressed=Mock(), ready=Mock())
        with (
            patch('native_player.protect', return_value=nullcontext()),
            patch(
                'native_player.move', side_effect=lambda *a, **k: calls.append('move')
            ),
        ):
            p.commit_destination('boss_kid_icarus', 33, captured=29)
        self.assertEqual(calls, [('release', 33, True), 'move', 'arrive', 'complete'])


class WindowsFocus(unittest.TestCase):
    def test_pygetwindow_error_zero_after_success_is_harmless(self):
        game = Mock()
        game.isActive = False

        def activate():
            game.isActive = True
            raise Exception(
                'Error code from Windows: 0 - The operation completed successfully.'
            )

        game.activate.side_effect = activate
        with (
            patch('lab.game_window', return_value=game),
            patch('game_focus.time.sleep'),
        ):
            self.assertTrue(game_focus.activate_game())

    def test_os_focus_denial_does_not_crash_or_loop_forever(self):
        game = Mock(isActive=False)
        game.activate.side_effect = Exception('focus denied')
        with (
            patch('lab.game_window', return_value=game),
            patch('game_focus.time.sleep'),
        ):
            self.assertFalse(game_focus.activate_game())
        self.assertEqual(game.activate.call_count, 12)

    def test_missing_window_is_bounded_and_nonfatal(self):
        with (
            patch('lab.game_window', side_effect=RuntimeError('not ready')) as lookup,
            patch('game_focus.time.sleep'),
        ):
            self.assertFalse(game_focus.activate_game())
            self.assertEqual(lookup.call_count, 12)


class Cleanup(unittest.TestCase):
    def test_broken_bridge_does_not_mask_original_error(self):
        b = Bridge.__new__(Bridge)
        b.p = process = Mock()
        process.poll.return_value = None
        process.stdin.write.side_effect = BrokenPipeError('closed')
        b.close()
        b.close()
        process.wait.assert_called_once_with(timeout=5)
        process.stdout.close.assert_called_once()
        self.assertIsNone(b.p)

    def test_already_exited_bridge_is_idempotent(self):
        b = Bridge.__new__(Bridge)
        b.p = process = Mock()
        process.poll.return_value = 0
        b.close()
        b.close()
        process.stdin.write.assert_not_called()


class Presentation(unittest.TestCase):
    def test_installer_icon_exists_in_clean_source_checkout(self):
        import re

        script = ROOT.parents[1] / 'packaging/windows/setup.iss'
        name = (
            re.search(r'^SetupIconFile=(.+)$', script.read_text(), re.M)
            .group(1)
            .strip()
        )
        self.assertTrue((script.parent / name.replace(chr(92), '/')).is_file())

    def test_descriptive_boss_label_is_translated(self):
        for lang in ('en', 'es', 'ru', 'ja'):
            self.assertNotIn('Ausweichen', ui_i18n.catalog(lang)['Ryu (Ausweichen)'])

    def test_composed_submenu_labels_are_translated_before_suffix(self):
        from menu_render import Renderer

        for lang in ('en', 'es', 'ru', 'ja'):
            with patch.object(ui_i18n, 'LANGUAGE', lang):
                r = Renderer.__new__(Renderer)
                seen = []
                r.box = Mock()
                r.text = lambda x, y, s, *args: seen.append(str(s))
                r.fit = lambda s, *args: ui_i18n.display(s)
                r.extras(NS(options={'extras': {}}, focus=0, extras_parent='new'))
                for key in ('Musik mischen', 'Sprite-Chaos · Einstellungen'):
                    self.assertIn(str(ui_i18n.tr(key)) + '  ›', seen)
                    self.assertNotIn(key + '  ›', seen)

    def test_all_stage_labels_translate_in_every_language(self):
        from minibosses import prepare_pool

        pool = {
            key: {'frame': 3}
            for key in (
                'save2.ini',
                'boss2.ini',
                'save23.ini',
                'save13.ini',
                'boss16.ini',
                'save22.ini',
                'save4.ini',
                'boss7.ini',
                'save12.ini',
                'save17.ini',
            )
        }
        labels = {
            v['label']
            for v in prepare_pool(pool, {'route_version': 9}).values()
            if 'label' in v
        }
        for language in ui_i18n.SUPPORTED:
            for label in labels:
                if ' · ' in label:
                    self.assertIn(label, ui_i18n.catalog(language), (language, label))


if __name__ == '__main__':
    unittest.main()
