"""Poll an active run and present its ending without owning the menu process.

The controller owns cleanup, profiles and loading covers. This module only
observes play, forwards tracker/debug events, and reports how play ended.
"""

from dataclasses import dataclass
import time

from menu_runtime import EndingDelay, MenuGame
from native_player import poll_delay, transient_read_error

MENU_POLL_SECONDS = 0.035
TRANSIENT_READ_GRACE_SECONDS = 5
RESULT_MODE = 4
NATIVE_MODE = 0
MODE_OFFSET = 60


@dataclass(frozen=True)
class RunExit:
    back_to_menu: bool
    keep_draft: bool = False


def update_result(player, tracker, model, view, renderer, debug):
    """Credits lack gameplay INI objects; retain the already confirmed result."""
    try:
        model.pump()
        if player.bridge.snapshot()['scene'] <= 1:
            # F2 ends presentation, not the durable victory record.
            view.write(MODE_OFFSET, NATIVE_MODE)
            model.page = 'slots'
            model.focus = 0
            model.action = ('result_back', model.slot, None)
            model.dirty = True
            return True
        for event in view.events():
            model.event(*event)
        if model.action is not None:
            view.write(MODE_OFFSET, NATIVE_MODE)
            return True
        if model.dirty:
            renderer.draw(model)
            view.refresh()
        result = player.poll()
        tracker.run(player, result)
        debug.commands()
        debug.tick('finished', player, model)
    except (KeyError, StopIteration, RuntimeError) as error:
        if not transient_read_error(error):
            raise
        return False
    return True


def show_result(player, tracker, model, view, renderer, debug, game_running):
    player.insights.pause()
    if player.shots:
        player.shots.pause()
    model.open_result(player.m)
    model.action = None
    renderer.draw(model)
    view.generation = view.header()[10]
    view.write(MODE_OFFSET, RESULT_MODE)
    view.refresh()
    while game_running() and model.action is None:
        update_result(player, tracker, model, view, renderer, debug)
        time.sleep(MENU_POLL_SECONDS)
    return RunExit(back_to_menu=game_running(), keep_draft=model.page == 'new')


def run_gameplay(player, tracker, model, renderer, debug, game_running):
    """Return on F2, a result-screen action, or closure of the owned game."""
    last_read = time.monotonic()
    ending = EndingDelay()
    while game_running():
        poll_started = time.monotonic()
        model.pump()
        try:
            if player.bridge.snapshot()['scene'] <= 1:
                return RunExit(back_to_menu=True)
            # This view borrows the player's bridge and never closes it.
            view = MenuGame.view(player.bridge, player.metadata['menu'])
            for event in view.events():
                if event[0] == 7:
                    model.event(*event)
            debug.commands(player)
            result = player.poll()
            tracker.run(player, result)
            debug.tick('running', player, model)
            last_read = time.monotonic()
            if result.get('completed') and ending.ready(
                result['frame'], time.monotonic()
            ):
                return show_result(
                    player, tracker, model, view, renderer, debug, game_running
                )
        except (KeyError, StopIteration, RuntimeError) as error:
            if not game_running():
                break
            if (
                transient_read_error(error)
                and time.monotonic() - last_read < TRANSIENT_READ_GRACE_SECONDS
            ):
                time.sleep(0.1)
                continue
            raise
        time.sleep(poll_delay(poll_started))
    return RunExit(back_to_menu=False)
