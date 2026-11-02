"""One owned Wine process; read-only frame observation, normal window/key controls.

No old runtime hooks, injected code or memory writes. This private Linux adapter
uses the existing path-restricted lab bridge for reads only.
"""

import hashlib, json, os, selectors, struct, subprocess, time
from pathlib import Path
from build_profiles import LAB, PREFIX
from menu_host.store import RUNS, digest, atomic
from menu_host.processes import games

from app_paths import WINE

TEXT_SHA = "d3ea604cfedac000b9b6b6ec01ad6ff966efa9a2aa7ca2abef84b3624f9947a4"
OPEN_TIMEOUT = 25
CLOSE_TIMEOUT = 8
MENU_FRAMES = {"JAE Intro", "Title Screen"}
from platform_support.observer import FrameObserver, FRAME_NAMES


def verify_engine(path, expected):
    if digest(path) != expected:
        raise ValueError("Executable identity")
    d = Path(path).read_bytes()
    pe = struct.unpack_from("<I", d, 60)[0]
    if d[pe : pe + 4] != b"PE\0\0":
        raise ValueError("PE header")
    count = struct.unpack_from("<H", d, pe + 6)[0]
    optional = struct.unpack_from("<H", d, pe + 20)[0]
    table = pe + 24 + optional
    sections = []
    for i in range(count):
        h = d[table + i * 40 : table + (i + 1) * 40]
        if h[:8].rstrip(b"\0") == b".text":
            size, offset = struct.unpack_from("<II", h, 16)
            sections.append(d[offset : offset + size])
    if len(sections) != 1 or hashlib.sha256(sections[0]).hexdigest() != TEXT_SHA:
        raise ValueError("Unsupported Fusion engine layout")


def windows():
    if os.name == "nt":
        from platform_support.windows_api import windows as native_windows

        return native_windows()
    # X11 windows can disappear between listing IDs and reading properties.
    # Discard a partial listing and retry only this specific transient failure.
    for attempt in range(3):
        result = subprocess.run(
            ["wmctrl", "-lp"], text=True, capture_output=True, timeout=3
        )
        if result.returncode == 0:
            return [
                r.split(None, 4)
                for r in result.stdout.splitlines()
                if r.endswith(" I Wanna Be The Boshy")
            ]
        if "BadWindow (invalid Window parameter)" not in result.stderr or attempt == 2:
            result.check_returncode()
        time.sleep(0.03)


class Reader(FrameObserver):
    def __init__(self, folder, expected):
        folder = Path(folder).resolve()
        if folder.parent != RUNS.resolve() or not folder.name.startswith(
            "rebuilt-menu-"
        ):
            raise ValueError("Observer boundary")
        verify_engine(folder / "Boshy.exe", expected)
        env = {**os.environ, "WINEPREFIX": str(PREFIX), "WINEDEBUG": "-all"}
        self.p = subprocess.Popen(
            [
                WINE,
                str(LAB / "phase_bridge.exe"),
                "C:\\BoshySceneTests\\" + folder.name + "\\Boshy.exe",
            ],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
            env=env,
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.p.stdout, selectors.EVENT_READ)
        try:
            self.base = self.line()["base"]
        except BaseException:
            self.close()
            raise

    def line(self):
        if not self.selector.select(3):
            raise TimeoutError("Frame observer timeout")
        line = self.p.stdout.readline()
        if not line:
            raise RuntimeError("Frame observer exited")
        return json.loads(line)

    def read(self, address, size):
        if not 4 <= size <= 256:
            raise ValueError("Observer read size")
        self.p.stdin.write(f"read {address:x} {size}\n")
        self.p.stdin.flush()
        r = self.line()
        if "hex" not in r:
            raise RuntimeError("Frame loading")
        return bytes.fromhex(r["hex"])

    def close(self):
        if getattr(self, "p", None) and self.p.poll() is None:
            try:
                self.p.communicate("quit\n", timeout=4)
            except (BrokenPipeError, subprocess.TimeoutExpired):
                self.p.terminate()
                self.p.wait(timeout=4)
        if getattr(self, "selector", None):
            self.selector.close()


class Runtime:
    def __init__(self, store):
        self.store = store
        self.reader = None
        self.window = None
        self.pid = None
        self.folder = None
        self.events = []
        self.started = False
        self.log = None
        self.last_read = 0
        self.proc = None

    def owned(self):
        if not self.window or not self.pid or not self.folder:
            return False
        if os.name == "nt":
            return games().get(self.pid) == self.folder and any(
                r[0] == self.window and r[2] == str(self.pid) for r in windows()
            )
        try:
            return Path(
                os.readlink("/proc/" + str(self.pid) + "/cwd")
            ).resolve() == self.folder and any(
                r[0] == self.window and r[2] == str(self.pid) for r in windows()
            )
        except FileNotFoundError:
            return False

    def key(self, key):
        if not self.owned():
            raise RuntimeError("Owned game window disappeared")
        if os.name == "nt":
            from platform_support.windows_api import key as send_key

            return send_key(self.window, key)
        subprocess.run(["wmctrl", "-ia", self.window], check=True, timeout=3)
        subprocess.run(["xdotool", "mousemove", "1910", "1040"], check=True, timeout=3)
        # Fusion polls keys at 50 Hz; a short X key tap can fall between frames.
        time.sleep(0.1)
        subprocess.run(["xdotool", "keydown", key], check=True, timeout=3)
        try:
            time.sleep(0.12)
        finally:
            subprocess.run(["xdotool", "keyup", key], check=True, timeout=3)

    def start(self, slot):
        if self.store.active or windows() or games():
            raise RuntimeError("Bitte zuerst das laufende Boshy-Spiel schließen.")
        folder, plan, c = self.store.resume(slot)
        verify_engine(folder / "Boshy.exe", plan["game_sha256"])
        self.folder = folder.resolve()
        self.slot = slot
        self.started = False
        before = self.store.summary(slot)
        self.events = [dict(event="launch", save=before)]
        self.window = self.pid = None
        self.proc = None
        self.store.active = slot
        try:
            self.log = (folder / "host-runtime.log").open("a")
            self.proc = subprocess.Popen(
                (
                    [str(folder / "Boshy.exe")]
                    if os.name == "nt"
                    else [WINE, str(folder / "Boshy.exe")]
                ),
                cwd=folder,
                env={**os.environ, "WINEPREFIX": str(PREFIX), "WINEDEBUG": "-all"},
                stdout=self.log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            deadline = time.monotonic() + OPEN_TIMEOUT
            while time.monotonic() < deadline:
                matches = []
                for r in windows():
                    try:
                        if (
                            games().get(int(r[2]))
                            if os.name == "nt"
                            else Path(os.readlink("/proc/" + r[2] + "/cwd")).resolve()
                        ) == self.folder:
                            matches.append(r)
                    except FileNotFoundError:
                        pass
                if len(matches) == 1:
                    self.window, self.pid = matches[0][0], int(matches[0][2])
                    break
                if len(matches) > 1:
                    raise RuntimeError("Duplicate owned game")
                if self.proc.poll() not in (None, 0) and not self.running():
                    raise RuntimeError("Game exited during startup")
                time.sleep(0.2)
            else:
                raise RuntimeError("Game did not open")
            self.reader = Reader(folder, plan["game_sha256"])
            deadline = time.monotonic() + 35
            last_key = 0
            while time.monotonic() < deadline:
                try:
                    frame = self.reader.frame()
                except RuntimeError:
                    time.sleep(0.15)
                    continue
                if frame not in MENU_FRAMES:
                    self.started = True
                    self.last_read = time.monotonic()
                    self.events.append(
                        dict(event="gameplay", frame=frame, pid=self.pid)
                    )
                    return frame
                if time.monotonic() - last_key > 1.3:
                    self.key("Return")
                    last_key = time.monotonic()
                time.sleep(0.15)
            raise RuntimeError("Could not leave original slot menu")
        except BaseException:
            self.close("startup-error")
            raise

    def poll(self):
        if not self.store.active:
            return "idle"
        if not self.owned():
            self.close("window-closed")
            return "menu"
        try:
            frame = self.reader.frame()
        except RuntimeError:
            if time.monotonic() - self.last_read > 10:
                self.close("observer-error")
                raise
            return "loading"
        except (TimeoutError, OSError, ValueError, StopIteration):
            self.close("observer-error")
            raise
        self.last_read = time.monotonic()
        if self.started and frame in MENU_FRAMES:
            self.close("F2")
            return "menu"
        return "playing"

    def running(self):
        """Reap our launcher and account for any Wine handoff to another PID."""
        launcher = self.proc is not None and self.proc.poll() is None
        return launcher or self.folder in games().values()

    def game_windows(self):
        result = []
        for row in windows():
            try:
                cwd = (
                    games().get(int(row[2]))
                    if os.name == "nt"
                    else Path(os.readlink("/proc/" + row[2] + "/cwd")).resolve()
                )
            except (FileNotFoundError, ProcessLookupError):
                continue
            if cwd == self.folder:
                result.append(row[0])
        return result

    def close(self, reason="menu-button"):
        if not self.store.active:
            return
        # Find windows again: startup may fail before self.window was assigned.
        closing = self.game_windows()
        for window in closing:
            if os.name == "nt":
                from platform_support.windows_api import close_window

                close_window(window)
            else:
                subprocess.run(["wmctrl", "-ic", window], check=True, timeout=3)
        if reason == "startup-error" and not closing and self.proc is not None:
            # Only our exact child, never wineserver or the shared Fusion editor.
            if self.proc.poll() is None:
                self.proc.terminate()
        end = time.monotonic() + CLOSE_TIMEOUT
        while self.running() and time.monotonic() < end:
            time.sleep(0.1)
        if self.running() or self.game_windows():
            raise RuntimeError(
                "Spielprozess läuft noch; Speicherplatz bleibt gesperrt."
            )
        if self.reader:
            self.reader.close()
            self.reader = None
        if self.log:
            self.log.close()
            self.log = None
        self.store.active = None
        self.store.resume(self.slot)  # native disk save must still match its run
        self.events.append(
            dict(event="return", reason=reason, save=self.store.summary(self.slot))
        )
        atomic(
            self.folder / "host-session.json",
            (json.dumps(self.events, indent=2) + "\n").encode(),
        )
        self.window = None
        self.pid = None
        self.proc = None


if os.name == "nt":
    from platform_support.windows_reader import WindowsReader as Reader
