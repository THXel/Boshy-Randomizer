"""Lifecycle boundaries: lock before mutation, retain ownership until success."""

import contextlib
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import menu_controller as host
from menu_gameplay import RunExit


class ControllerTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.base = Path(folder.name)
        self.store = Mock(base=self.base)
        with patch.object(host, 'Renderer'), patch.object(host, 'Publisher'):
            self.controller = host.MenuController(self.store)
        self.controller.game = Mock()
        self.controller.model = Mock(page='slots')
        self.controller.debug = Mock()
        self.controller.cover = Mock(position='old-position')
        self.events = []
        self.live = Mock()
        self.locked = False

        @contextlib.contextmanager
        def transaction():
            self.assertFalse(self.locked)
            self.locked = True
            self.events.append('lock')
            try:
                yield self.live
            finally:
                self.events.append('unlock')
                self.locked = False

        self.live.transaction.side_effect = transaction
        self.patch_live = patch.object(host, 'LiveSession', return_value=self.live)
        self.patch_live.start()
        self.addCleanup(self.patch_live.stop)

    def guarded(self, name, result=None):
        def action(*args, **kwargs):
            self.assertTrue(self.locked, name)
            self.events.append(name)
            return result

        return action

    def test_delete_keeps_game_and_reloads_inside_the_same_transaction(self):
        game, cover = self.controller.game, self.controller.cover
        self.store.delete.side_effect = self.guarded('delete')
        self.live.reload.side_effect = self.guarded('reload')
        self.controller._delete_slot(3)
        self.assertEqual(self.events, ['lock', 'delete', 'reload', 'unlock'])
        self.store.delete.assert_called_once_with(3)
        self.live.reload.assert_called_once_with(3)
        self.assertIs(self.controller.game, game)
        game.close.assert_not_called()
        self.assertIsNone(self.controller.cover)
        cover.restore_game.assert_called_once()
        cover.close.assert_called_once()

    def test_only_delete_cover_preserves_audio(self):
        with (
            patch.object(host, 'LoadingScreen') as screen,
            patch.object(host, 'for_selection'),
            patch.object(host.time, 'sleep'),
        ):
            for action in ('delete', 'new', 'resume'):
                self.controller._show_action_cover(action, 3, {})
                self.assertEqual(
                    screen.call_args.kwargs['preserve_audio'], action == 'delete'
                )

    def test_new_run_consumes_draft_once_and_binds_only_after_profile_activation(self):
        manifest = {'status': 'ready'}
        settings = {'seed': 'DRAFT', 'options': {'mode': 'randomizer'}}
        self.store.prepare.side_effect = self.guarded('prepare', manifest)
        self.live.compatible.return_value = True
        self.live.bind.side_effect = self.guarded('bind')
        self.controller._run_randomizer = Mock(return_value=True)
        with (
            patch.object(host, 'slot_available', return_value=True),
            patch.object(host, 'activate', side_effect=self.guarded('activate')),
        ):
            self.assertTrue(self.controller._start_or_resume('new', 2, settings))
        self.assertEqual(self.events, ['lock', 'prepare', 'activate', 'bind', 'unlock'])
        self.store.prepare.assert_called_once_with('DRAFT', 2, settings['options'])
        self.controller.model.consume_seed.assert_called_once()
        self.controller._run_randomizer.assert_called_once_with(manifest, True)

    def test_resume_keeps_seed_and_incompatible_archive_uses_cold_start(self):
        manifest = {'status': 'ready', 'seed': 'ARCHIVED'}
        self.store.current.side_effect = self.guarded('current', manifest)
        self.live.compatible.return_value = False
        self.controller._run_randomizer = Mock(return_value=True)
        with patch.object(host, 'activate') as activate:
            self.assertTrue(self.controller._start_or_resume('resume', 1, None))
        self.store.prepare.assert_not_called()
        self.controller.model.consume_seed.assert_not_called()
        activate.assert_not_called()
        self.live.bind.assert_not_called()
        self.live.clear.assert_not_called()
        self.controller._run_randomizer.assert_called_once_with(manifest, False)

    def test_ordinary_save_clears_randomizer_context_and_reloads_in_transaction(self):
        self.store.current.return_value = None
        self.live.clear.side_effect = self.guarded('clear')
        self.live.reload.side_effect = self.guarded('reload')
        self.controller._run_ordinary = Mock(return_value=False)
        self.assertFalse(self.controller._start_or_resume('resume', 1, None))
        self.assertEqual(self.events, ['lock', 'clear', 'reload', 'unlock'])
        self.controller._run_ordinary.assert_called_once_with(1)

    def test_occupied_new_slot_is_rejected_before_any_transaction(self):
        with patch.object(host, 'slot_available', return_value=False):
            with self.assertRaises(ValueError):
                self.controller._start_or_resume('new', 1, {})
        self.live.transaction.assert_not_called()
        self.store.prepare.assert_not_called()

    def player(self):
        return Mock(metadata={'menu': 0x1234}, folder=self.base)

    def test_successful_hot_start_transfers_ownership_then_closes_only_player_bridge(
        self,
    ):
        game, player = self.controller.game, self.player()
        with (
            patch.object(host, 'Player', return_value=player),
            patch.object(host.time, 'sleep'),
            patch.object(host, 'activate_game'),
            patch.object(host, 'finish'),
            patch.object(host, 'run_gameplay', return_value=RunExit(False)),
        ):
            self.assertFalse(self.controller._run_randomizer({'status': 'ready'}, True))
        player.start.assert_called_once_with(game=game)
        game.close.assert_not_called()
        player.close.assert_called_once_with()
        self.assertIsNone(self.controller.game)
        self.assertIsNone(self.controller.player)

    def test_failed_hot_start_retains_references_for_error_cleanup(self):
        game, player = self.controller.game, self.player()
        player.start.side_effect = RuntimeError('start failed')
        with (
            patch.object(host, 'Player', return_value=player),
            patch.object(host.time, 'sleep'),
        ):
            with self.assertRaisesRegex(RuntimeError, 'start failed'):
                self.controller._run_randomizer({'status': 'ready'}, True)
        self.assertIs(self.controller.game, game)
        self.assertIs(self.controller.player, player)

    def test_cold_start_closes_old_process_and_preserves_cover_position(self):
        game, player, cover = self.controller.game, self.player(), self.controller.cover

        def start(**kwargs):
            game.close.assert_called_once()
            self.assertIsNone(self.controller.game)
            cover.close.assert_not_called()

        player.start.side_effect = start
        with (
            patch.object(host, 'Player', return_value=player),
            patch.object(host, 'activate') as activate,
            patch.object(host, 'activate_game'),
            patch.object(host, 'finish'),
            patch.object(host, 'run_gameplay', return_value=RunExit(False)),
        ):
            self.controller._run_randomizer({'status': 'ready'}, False)
        activate.assert_called_once()
        player.start.assert_called_once_with(position='old-position')
        cover.close.assert_called_once()

    def test_return_restores_profile_inside_lock_before_dismissing_cover(self):
        self.live.clear.side_effect = self.guarded('clear')
        self.live.reload.side_effect = self.guarded('reload')
        with (
            patch.object(host.MenuGame, 'attach', return_value=self.controller.game),
            patch.object(host, 'finish', side_effect=self.guarded('finish')),
            patch.object(host, 'activate_game'),
        ):
            self.controller._return_from_run({'menu': 1})
        self.assertEqual(self.events, ['lock', 'clear', 'finish', 'reload', 'unlock'])
        self.controller.game.title.assert_called_once()
        self.assertIsNone(self.controller.cover)

    def test_result_new_run_draft_is_preserved_for_one_menu_refresh(self):
        self.controller.keep_draft = True
        self.controller.model.page = 'new'
        self.controller._refresh_menu()
        self.assertEqual(self.controller.model.page, 'new')
        self.assertFalse(self.controller.keep_draft)
        self.controller.game.write.assert_called_with(60, 2)
        self.controller._refresh_menu()
        self.assertEqual(self.controller.model.page, 'slots')
        self.controller.game.write.assert_called_with(60, 1)

    def test_action_error_closes_owned_handles_and_restores_profile(self):
        player, game = self.player(), self.controller.game
        self.controller.player = player
        error = ValueError('invalid save')
        with (
            patch.object(host, 'finish') as finish,
            patch.object(host.traceback, 'print_exc'),
        ):
            self.controller._recover_action(error)
        player.close.assert_called_once_with(close_game=True)
        game.close.assert_called_once()
        finish.assert_called_once_with(self.store)
        self.assertIsNone(self.controller.game)
        self.assertIsNone(self.controller.player)
        self.controller.debug.error.assert_called_once_with(error)

    def test_tracker_parent_log_handle_is_closed_after_launch(self):
        (self.base / 'evidence').mkdir()
        with patch.object(host.subprocess, 'Popen') as spawn:
            host.start_tracker(self.base)
        self.assertTrue(spawn.call_args.kwargs['stderr'].closed)


if __name__ == '__main__':
    unittest.main()
