"""Own the menu, save transactions, game process and loading-cover lifecycle.

Gameplay polling lives in menu_gameplay; rule selection remains in the existing
session/rules modules. Ownership transfers from MenuGame to Player only after
start succeeds, and transfers back only after Player releases its bridge.
"""

import os
import subprocess
import time
import traceback

from debug_runtime import DebugRuntime
from game_focus import activate_game
from host_platform import child_options, python_command
from intro_cast import prepare as prepare_intro
from live_session import LiveSession
from loading_destination import for_frame, for_selection
from loading_screen import LoadingScreen
from menu_gameplay import MENU_POLL_SECONDS, run_gameplay
from menu_model import Menu
from menu_navigation import load_slot, select_requested_slot
from menu_render import Renderer
from menu_runtime import MenuGame
from native_models import slot_available
from native_player import Player
from native_profiles import activate, finish
from native_tracker import Publisher
from runtime_versions import recover_all
from ui_i18n import tr

MODE_OFFSET = 60
NATIVE_MODE = 0
SLOT_MODE = 1
MODAL_MODE = 2


def start_tracker(base):
    """Launch the separate tracker; the parent does not retain its log handle."""
    command = (
        python_command('tracker_entry.py')
        if os.name == 'nt'
        else [str(base / 'start-live-tracker.sh')]
    )
    with (base / 'evidence/tracker-process.log').open('a', encoding='utf-8') as log:
        subprocess.Popen(
            command,
            cwd=base,
            env={**os.environ, 'BOSHY_TRACKER_HOST': str(os.getpid())},
            stdout=subprocess.DEVNULL,
            stderr=log,
            start_new_session=True,
            **child_options(),
        )


class MenuController:
    def __init__(self, store):
        self.store = store
        self.base = store.base
        self.game = None
        self.player = None
        self.cover = None
        self.model = None
        self.debug = None
        self.renderer = Renderer(self.base)
        self.tracker = Publisher(store)
        self.keep_draft = False

    def run(self):
        start_tracker(self.base)
        with self.store.lock():
            self.store._stopped()
            finish(self.store)
            prepare_intro(self.base)
            recover_all(self.store)
            self.model = Menu(self.store)
            self.renderer.draw(self.model)
            self.debug = DebugRuntime(self.store)
            try:
                self._main_loop()
            except Exception as error:
                self.debug.error(error)
                raise
            finally:
                self.close()

    def _main_loop(self):
        while True:
            self._ensure_menu()
            action = self._wait_for_action()
            if action is None:
                return
            name, slot, settings = action
            if name == 'result_back':
                continue
            if name == 'quit':
                self.game.close()
                self.game = None
                return
            self.keep_draft = False
            self._show_action_cover(name, slot, settings)
            try:
                if name == 'delete':
                    self._delete_slot(slot)
                elif name in ('new', 'resume'):
                    if not self._start_or_resume(name, slot, settings):
                        return
            except Exception as error:
                self._recover_action(error)
            self._refresh_menu()

    def _ensure_menu(self):
        if self.game is not None:
            return
        position = self.cover.position if self.cover else None
        self.game = MenuGame(position=position)
        self._close_cover()
        activate_game()

    def _wait_for_action(self):
        self.model.action = None
        while self.store.game_running() and self.model.action is None:
            self.tracker.menu()
            self.model.pump()
            self.debug.commands()
            self.debug.tick('menu', model=self.model)
            for event in self.game.events():
                self.model.event(*event)
            if self.model.requested_slot is not None:
                select_requested_slot(self.game, self.model, self.debug)
            if self.model.dirty:
                self._render_menu()
            time.sleep(MENU_POLL_SECONDS)
        if not self.store.game_running():
            self.game.bridge.close()
            self.game = None
            return None
        return self.model.action

    def _show_action_cover(self, action, slot, settings):
        self.debug.tick('loading', model=self.model, force=True)
        message = (
            tr('Spielstand wird gelöscht …')
            if action == 'delete'
            else tr('Spielstand wird geladen …')
        )
        self.cover = LoadingScreen(
            self.base,
            slot,
            message=message,
            destination=for_selection(self.store, slot, action, settings),
            preserve_audio=action == 'delete',
        )
        self.model.page = 'loading'
        self.model.message = message
        self.renderer.draw(self.model)
        self.game.refresh()
        time.sleep(0.12)
        self.tracker.menu(loading=True)

    def _show_return_cover(self):
        self.cover = LoadingScreen(
            self.base,
            0,
            'Zurück zum Hauptmenü …',
            destination=for_frame(self.base, 2),
        )

    def _close_cover(self):
        if self.cover is not None:
            self.cover.restore_game()
            self.cover.close()
            self.cover = None

    def _delete_slot(self, slot):
        with LiveSession(self.store, self.game).transaction() as live:
            self.store.delete(slot)
            live.reload(slot)
        self.model.message = tr('Speicherplatz {0} gelöscht und gesichert.', slot)
        self._close_cover()

    def _start_or_resume(self, action, slot, settings):
        if action == 'new' and not slot_available(self.store, slot):
            raise ValueError(
                'Dieser Speicherplatz ist belegt. Bitte zuerst im Menü löschen.'
            )
        live = LiveSession(self.store, self.game)
        with live.transaction():
            if action == 'new':
                manifest = self.store.prepare(
                    settings['seed'], slot, settings['options']
                )
                self.model.consume_seed()
            else:
                manifest = self.store.current(slot)
            hot = bool(
                manifest and manifest['status'] == 'ready' and live.compatible(manifest)
            )
            if hot:
                activate(self.store, manifest)
                live.bind(manifest)
            elif not manifest or manifest['status'] != 'ready':
                live.clear()
                live.reload(slot)
        if manifest and manifest['status'] == 'ready':
            continuing = self._run_randomizer(manifest, hot)
        else:
            continuing = self._run_ordinary(slot)
        if continuing:
            self.model.message = 'Lauf gespeichert.'
        return continuing

    def _run_randomizer(self, manifest, hot):
        self.store.validate(manifest)
        self.player = Player(self.store, manifest)
        if hot:
            self.game.write(MODE_OFFSET, NATIVE_MODE)
            time.sleep(0.1)
            self.player.start(game=self.game)
            self.game = None
        else:
            # Archived incompatible payloads retain their audited cold-start path.
            self.game.close()
            self.game = None
            activate(self.store, manifest)
            self.player.start(position=self.cover.position)
        self.player.bridge.cmd(
            f"menu {self.player.metadata['menu']:x} {MODE_OFFSET} {SLOT_MODE}"
        )
        self._close_cover()
        activate_game()
        outcome = run_gameplay(
            self.player,
            self.tracker,
            self.model,
            self.renderer,
            self.debug,
            self.store.game_running,
        )
        self.keep_draft = outcome.keep_draft
        if (
            not outcome.back_to_menu
            and not (self.player.folder / 'summary.json').exists()
        ):
            self.debug.error(
                RuntimeError(
                    'Spiel während eines aktiven Laufs geschlossen; Ursache unbekannt.'
                )
            )
        if outcome.back_to_menu:
            self._show_return_cover()
        self.tracker.menu(loading=True)
        metadata = dict(self.player.metadata)
        self.player.close()
        self.player = None
        if not outcome.back_to_menu:
            finish(self.store)
            return False
        self._return_from_run(metadata)
        return True

    def _return_from_run(self, metadata):
        self.game = MenuGame.attach(metadata)
        self.game.title()
        with LiveSession(self.store, self.game).transaction() as live:
            live.clear()
            finish(self.store)
            live.reload()
        self._close_cover()
        activate_game()

    def _run_ordinary(self, slot):
        """Ordinary saves retain original rules and the original character profile."""
        self.game.write(MODE_OFFSET, NATIVE_MODE)
        time.sleep(0.1)
        load_slot(self.game.bridge, self.game.address, slot)
        self.game.write(MODE_OFFSET, SLOT_MODE)
        self._close_cover()
        activate_game()
        while self.store.game_running() and self.game.bridge.snapshot()['scene'] > 1:
            self.model.pump()
            self.debug.commands()
            self.debug.tick('ordinary', model=self.model)
            time.sleep(0.1)
        if not self.store.game_running():
            self.game.bridge.close()
            self.game = None
            return False
        self._show_return_cover()
        self.game.title()
        self._close_cover()
        activate_game()
        return True

    def _recover_action(self, error):
        self.debug.error(error)
        self.debug.tick('error', model=self.model, force=True)
        traceback.print_exc()
        if self.player is not None:
            self.player.close(close_game=True)
            self.player = None
        if self.game is not None:
            self.game.close()
            self.game = None
        finish(self.store)
        self.model.message = 'Angehalten: ' + str(error)

    def _render_menu(self):
        self.renderer.draw(self.model)
        mode = SLOT_MODE if self.model.page == 'slots' else MODAL_MODE
        self.game.write(MODE_OFFSET, mode)
        self.game.refresh()

    def _refresh_menu(self):
        if not self.keep_draft:
            self.model.page = 'slots'
        self.keep_draft = False
        self.model.reload()
        if self.game is not None:
            self._render_menu()
        else:
            self.renderer.draw(self.model)

    def close(self):
        self.debug.close()
        self.model.close()
        self.tracker.pause()
        if self.player is not None:
            self.player.close(close_game=True)
        if self.game is not None:
            self.game.close()
        finish(self.store)
        self.tracker.stopped()
        if self.cover is not None:
            self.cover.close()
