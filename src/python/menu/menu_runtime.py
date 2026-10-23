"""Transport for native owned dialogs in the Boshy process."""

from host_platform import close_window, press
from ui_i18n import tr
from pathlib import Path
import json
import struct
import subprocess
import os
import time
from lab import BASE, RUNNER, Bridge, game_window
from runtime_paths import command, environment
from mixed_rewards import CONTEXT_SIZE
from native_session import atomic
from window_position import wait_for_game

MENU_SIZE = 2160


class EndingDelay:
    """Keep the original reveal point plus fifteen seconds for the ending animation."""

    def __init__(self):
        self.deadline = None

    def ready(self, frame, now):
        if self.deadline is None:
            self.deadline = now + 20
        if frame == 47:
            self.deadline = min(self.deadline, now + 15)
        return now >= self.deadline


class SlotSelectionError(RuntimeError):
    """Recoverable failure to select a slot; never close or load the game."""


class MenuGame:
    def __init__(self, enabled=True, position=None):
        from soundpacks import prepare_menu

        prepare_menu(BASE)
        folder = BASE / 'native-runs' / ('0' * 32)
        folder.mkdir(parents=True, exist_ok=True)
        blob = bytearray((BASE / 'slot_reward_extras.bin').read_bytes())
        off = (
            json.loads(
                (BASE / 'slot_reward_extras_symbols.json').read_text(encoding='utf-8')
            )['context_offset']
            + CONTEXT_SIZE
        )
        struct.pack_into('<I', blob, off + 60, int(enabled))
        struct.pack_into('<I', blob, off + 40, 1)
        payload = folder / 'reward_hook.bin'
        atomic(
            payload,
            __import__("intro_guard").attach(
                BASE, blob, context_offset=off - CONTEXT_SIZE, extras=True
            ),
        )
        log = folder / 'launch.log'
        with log.open('w') as f:
            ret = subprocess.run(
                command('slot_reward_launcher.exe', payload.relative_to(BASE)),
                cwd=BASE,
                env=environment(),
                stdout=f,
                stderr=f,
                timeout=45,
                **__import__('host_platform').child_options(),
            )
        if ret.returncode:
            raise RuntimeError(log.read_text(encoding='utf-8')[-1000:])
        meta = json.loads(
            next(
                x
                for x in log.read_text(encoding='utf-8').splitlines()
                if x.startswith('{')
            )
        )
        self.address = meta['hook'] + off
        self.metadata = {
            **meta,
            'menu': self.address,
            'context': self.address - CONTEXT_SIZE,
        }
        self.bridge = None
        try:
            wait_for_game(position, process_id=meta["pid"])
            self.bridge = Bridge()
            self.generation = 1
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                try:
                    self.header()
                    break
                except RuntimeError as e:
                    if not (
                        e.args
                        and isinstance(e.args[0], dict)
                        and e.args[0].get('error') == 'state unavailable'
                    ):
                        raise
                    time.sleep(0.1)
            else:
                raise RuntimeError('Natives Menü wurde nicht initialisiert.')
            if position:
                position.restore()
        except Exception:
            self.close()
            raise

    @classmethod
    def view(cls, bridge, address):
        """Borrow a player's bridge for events/rendering; the caller retains ownership."""
        game = cls.__new__(cls)
        game.bridge = bridge
        game.address = address
        return game

    @classmethod
    def attach(cls, metadata):
        game = cls.__new__(cls)
        game.metadata = dict(metadata)
        game.address = metadata['menu']
        game.bridge = Bridge()
        game.generation = game.header()[10]
        return game

    def title(self):
        from lab import key

        self.write(60, 0)
        end = time.monotonic() + 15
        sent = False
        while time.monotonic() < end:
            try:
                snap = self.bridge.snapshot()
                if snap['scene'] == 1 and self.header()[2] == 2:
                    return
                if snap['scene'] > 1 and not sent:
                    key('F2')
                    sent = True
            except RuntimeError as error:
                if not (
                    error.args
                    and isinstance(error.args[0], dict)
                    and error.args[0].get('error')
                    in ('state unavailable', 'read failed')
                ):
                    raise
            time.sleep(0.05)
        raise RuntimeError(tr('Hauptmenü wurde nicht bestätigt.'))

    def header(self):
        return struct.unpack('<16I', self.bridge.read(self.address, 64))

    def write(self, off, value):
        self.bridge.cmd(f'menu {self.address:x} {off} {int(value)}')

    def select_slot(self, slot):
        if slot not in (1, 2, 3):
            raise ValueError('Ungültiger Speicherplatz.')
        from lab import key

        for _ in range(4):
            h = self.header()
            if h[7] != 0 or h[15] != 1 or h[9] not in (1, 2, 3):
                raise SlotSelectionError('Speicherplatzauswahl ist nicht geöffnet.')
            if h[9] == slot:
                return
            before = h[9]
            # Original selection stops at slots 1 and 3; it does not wrap around.
            try:
                key('Right' if slot > before else 'Left')
            except RuntimeError as error:
                raise SlotSelectionError(
                    'Speicherplatzauswahl konnte nicht fokussiert werden.'
                ) from error
            end = time.monotonic() + 1.2
            while time.monotonic() < end:
                h = self.header()
                if h[7] != 0 or h[15] != 1:
                    raise SlotSelectionError('Speicherplatzauswahl hat sich geändert.')
                if h[9] == slot:
                    return
                if h[9] != before:
                    break
                time.sleep(0.025)
        raise SlotSelectionError('Gewählter Speicherplatz wurde nicht bestätigt.')

    def events(self):
        from menu_navigation import dismiss_startup_notice

        if dismiss_startup_notice():
            return []
        try:
            h = self.header()
        except RuntimeError as e:
            if (
                e.args
                and isinstance(e.args[0], dict)
                and e.args[0].get('error') == 'state unavailable'
            ):
                return []
            raise
        end, ack = h[5:7]
        if h[12]:
            raise RuntimeError(f'Natives Menü meldet Fehler {h[12]}')
        if end - ack > 64:
            raise RuntimeError('Menüeingaben übergelaufen')
        events = []
        for n in range(ack, end):
            events.append(
                struct.unpack(
                    '<4I', self.bridge.read(self.address + 324 + 16 * (n % 64), 16)
                )[:3]
            )
        if end != ack:
            self.write(24, end)
        return events

    def refresh(self):
        self.generation += 1
        self.write(40, self.generation)

    def close(self):
        if self.bridge:
            self.bridge.close()
            self.bridge = None
        import psutil

        try:
            w = game_window()
        except RuntimeError as e:
            if str(e) == 'Expected one laboratory window: 0':
                return
            raise
        p = psutil.Process(w.pid)
        close_window(w)
        p.wait(timeout=15)
