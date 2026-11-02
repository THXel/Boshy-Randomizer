"""Own one native Fusion title window; normal close and read-only observation."""

import os, subprocess, time
from menu_host.runtime import WINE, windows, Reader
from menu_host.store import digest
from menu_host.processes import games
from build_profiles import PREFIX


def wait_for_window(process, folder, timeout):
    """Wait for the owned window, allowing a slow first start on fresh Windows."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        owned = games()
        matches = [r for r in windows() if owned.get(int(r[2])) == folder]
        if len(matches) == 1:
            return matches[0]
        if len(matches) > 1:
            raise RuntimeError("Duplicate native menu windows")
        code = process.poll()
        if code is not None:
            raise RuntimeError(f"The game ended before its window opened (exit {code})")
        time.sleep(0.15)
    raise TimeoutError("The game did not open its window in time")


class Window:
    def __init__(self, folder):
        self.folder = folder.resolve()
        self.window = None
        self.pid = None
        self.proc = None
        self.reader = None
        self.log = None

    def owned(self):
        if not self.pid:
            return False
        if os.name == "nt" and self.reader:
            from tracker.windows_process import inspect

            from platform_support.windows_api import owns_window

            return inspect(self.pid) == self.reader.identity and owns_window(self.window, self.pid)
        return games().get(self.pid) == self.folder and any(
            r[0] == self.window and r[2] == str(self.pid) for r in windows()
        )

    def launch(self):
        if games() or windows():
            raise RuntimeError("Please close the running Boshy game first")
        self.log = (self.folder / "native-menu-runtime.log").open("a")
        self.proc = subprocess.Popen(
            (
                [str(self.folder / "Boshy.exe")]
                if os.name == "nt"
                else [WINE, str(self.folder / "Boshy.exe")]
            ),
            cwd=self.folder,
            env={**os.environ, "WINEPREFIX": str(PREFIX), "WINEDEBUG": "-all"},
            stdout=self.log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            row = wait_for_window(self.proc, self.folder, 90 if os.name == "nt" else 25)
            self.window, self.pid = row[0], int(row[2])
            self.reader = Reader(self.folder, digest(self.folder / "Boshy.exe"))
        except BaseException:
            self.close()
            raise

    def key(self, key):
        if not self.owned():
            raise RuntimeError("Owned native menu disappeared")
        if os.name == "nt":
            from platform_support.windows_api import key as send_key

            return send_key(self.window, key)
        subprocess.run(["wmctrl", "-ia", self.window], check=True)
        subprocess.run(["xdotool", "keydown", key], check=True)
        try:
            time.sleep(0.13)
        finally:
            subprocess.run(["xdotool", "keyup", key], check=True)

    def close(self):
        from native_menu.display_window import release

        release(self)
        from native_menu.shutdown import close_owned

        def request(row, retry):
            if os.name == "nt":
                from platform_support.windows_api import close_window, owns_window
                from tracker.windows_process import inspect

                pid = int(row[2])
                if self.reader and (
                    pid != self.pid or inspect(pid) != self.reader.identity
                ):
                    return
                if owns_window(row[0], pid):
                    close_window(row[0])
            else:
                subprocess.run(["wmctrl", "-ic", row[0]], check=True)

        if self.proc and not self.window and self.proc.poll() is None:
            self.proc.terminate()
        close_owned(self.folder, games, windows, request)
        if self.reader:
            self.reader.close()
            self.reader = None
        if self.log:
            self.log.close()
            self.log = None
        self.window = None
        self.pid = None
        self.proc = None
