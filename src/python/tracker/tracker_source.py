"""The desktop tracker belongs exclusively to one Randomizer host."""

import json
import os
import time
import threading
from pathlib import Path

BASE = Path(__file__).resolve().parent


def host_alive(pid):
    try:
        import psutil

        p = psutil.Process(int(pid))
        return (
            p.is_running()
            and p.status() != psutil.STATUS_ZOMBIE
            and Path(p.cwd()).resolve() == BASE
            and (
                any(
                    Path(x).name in ('native_menu_host.py', 'windows_entry.py')
                    for x in p.cmdline()
                )
                or os.name == 'nt'
                and Path(p.exe()).name.casefold() == 'boshyrandomizer.exe'
                and p.environ().get('BOSHY_DATA_HOME') == str(BASE)
            )
        )
    except Exception:
        return False


class Source:
    def __init__(self):
        self.lock = threading.Lock()
        self.state = {}
        self.stop = threading.Event()
        self.finished = False
        self.host = int(os.environ.get('BOSHY_TRACKER_HOST', '0'))
        self.started = time.monotonic()
        self.thread = threading.Thread(target=self.loop, daemon=True)
        self.thread.start()

    def loop(self):
        while not self.stop.is_set():
            state = None
            try:
                native = json.loads(
                    (BASE / 'INI/native-live.json').read_text(encoding='utf-8')
                )
                if not self.host and host_alive(native.get('host_pid')):
                    self.host = int(native['host_pid'])
                if self.host and host_alive(self.host):
                    if (
                        native.get('host_pid') == self.host
                        and native.get('schema') == 1
                        and native.get('mode') in ('menu', 'target', 'randomizer')
                    ):
                        state = native
                elif self.host or time.monotonic() - self.started > 3:
                    self.finished = True
            except (OSError, ValueError, TypeError):
                if (self.host and not host_alive(self.host)) or (
                    not self.host and time.monotonic() - self.started > 3
                ):
                    self.finished = True
            if state is not None:
                with self.lock:
                    self.state = state
            if self.finished:
                return
            self.stop.wait(0.25)

    def read(self):
        with self.lock:
            return dict(self.state)
