"""Load exactly the selected original slot, waiting for native menu acknowledgements."""

from host_platform import close_window, press
import time
import struct
import subprocess
from lab import key, game_window


def dismiss_startup_notice():
    """Close only Boshy's obsolete informational character notice, never other apps."""
    from PY.platform_windows import getAllWindows

    try:
        game = game_window()
    except RuntimeError:
        return False
    closed = False
    for window in getAllWindows():
        if (
            window.pid == game.pid
            and window.title == 'Playable characters'
            and window.isVisible
        ):
            close_window(window)
            closed = True
    return closed


def header(bridge, address):
    h = struct.unpack('<16I', bridge.read(address, 64))
    if h[0] != 0x424D4E31 or h[12]:
        raise RuntimeError('Spielmenü konnte nicht bestätigt werden.')
    return h


def load_slot(bridge, address, slot, cancel=None):
    if slot not in (1, 2, 3):
        raise ValueError('Ungültiger Speicherplatz.')

    def wait(predicate, timeout=12, retry=None):
        next_key = time.monotonic() + 0.7
        last = None
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            if cancel and cancel.is_set():
                raise RuntimeError('Start abgebrochen.')
            try:
                if dismiss_startup_notice():
                    time.sleep(0.05)
                    continue
                snap = bridge.snapshot()
                h = header(bridge, address)
                last = (snap.get('scene'), h[7], h[9])
                if predicate(snap, h):
                    return snap, h
                if retry and time.monotonic() >= next_key:
                    send(retry)
                    next_key = time.monotonic() + 0.7
            except RuntimeError as e:
                if not (
                    e.args
                    and isinstance(e.args[0], dict)
                    and e.args[0].get('error') in ('state unavailable', 'read failed')
                ):
                    raise
            time.sleep(0.04)
        raise RuntimeError(
            f'Spielmenü hat die Auswahl nicht bestätigt (Szene/Menü/Slot: {last}). Kein anderer Slot wird geladen.'
        )

    def send(name):
        try:
            key(name)
        except RuntimeError as e:
            if 'focus' not in str(e):
                raise

    snap, h = wait(
        lambda s, h: s['scene'] == 1
        and h[2] == 2
        and h[7] in (0xFFFFFFFE, 0xFFFFFFFF, 0),
        25,
    )
    for _ in range(3):
        layer = h[7]
        if layer == 0:
            break
        send('Return')
        snap, h = wait(
            lambda s, h: s['scene'] == 1
            and h[7] != layer
            and h[7] in (0xFFFFFFFE, 0xFFFFFFFF, 0),
            retry='Return',
        )
    else:
        raise RuntimeError('Speicherplatzauswahl nicht erreicht.')
    # Every arrow is acknowledged in the game's own selection state before the next.
    for _ in range(3):
        if h[9] == slot:
            break
        before = h[9]
        arrow = 'Right' if slot > before else 'Left'
        send(arrow)
        snap, h = wait(
            lambda s, h: s['scene'] == 1 and h[7] == 0 and h[9] != before, retry=arrow
        )
    if h[9] != slot:
        raise RuntimeError('Gewählter Speicherplatz wurde nicht bestätigt.')
    send('Return')
    return wait(lambda s, h: s['scene'] > 1, retry='Return')[0]


def select_requested_slot(game, model, debug):
    """Recover a missed slot acknowledgement without closing or loading a game."""
    from menu_runtime import SlotSelectionError
    from ui_i18n import tr

    selected = model.requested_slot
    model.requested_slot = None
    try:
        game.select_slot(selected)
    except SlotSelectionError as error:
        debug.error(error)
        header = game.header()
        if header[7] == 0 and header[9] in (1, 2, 3):
            model.select(header[9])
        model.message = tr(
            'Speicherplatzauswahl nicht bestätigt. Bitte erneut auswählen.'
        )
        model.action = None
        model.focus = 0
        model.dirty = True
        return False
    model.select(selected)
    model.message = ''
    model.focus = 0
    model.dirty = True
    return True
