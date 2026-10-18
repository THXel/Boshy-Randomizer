"""Linux X11 input and Wine lifecycle. Windows retains the original behavior."""
import os
import signal
import shutil
import subprocess
import time
from pathlib import Path

_TARGET = None
_GAME_PID = None
_GAME_CWD = None
_GAME_PROCESS = None
_BASE = Path(__file__).resolve().parent.parent

def _settings():
    import json
    path = _BASE / 'linux-settings.json'
    return json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}

def preflight():
    if os.name == 'nt':
        return
    if not os.environ.get('DISPLAY') or os.environ.get('XDG_SESSION_TYPE') == 'wayland':
        raise RuntimeError('Boshy Randomizer needs an X11 desktop session (Linux Mint Cinnamon X11).')
    from PY.platform_windows import connection
    connection()
    if not shutil.which('xdotool'):
        raise RuntimeError('Please install xdotool.')
    wine = _settings().get('wine', 'wine')
    if not shutil.which(wine):
        raise RuntimeError(f'Wine runner not found: {wine}')
    from PY.config import game_exe
    if not Path(game_exe).is_file():
        raise RuntimeError(f'Game executable not found: {game_exe}')
    from PY.platform_windows import getWindowsWithTitle
    from PY.config import window_title
    if getWindowsWithTitle(window_title):
        raise RuntimeError('Please close the other Boshy game before starting the randomizer.')

def launch_game(exe, cwd):
    global _GAME_PID, _GAME_CWD
    _GAME_CWD = str(Path(cwd).resolve())
    if os.name == 'nt':
        return subprocess.Popen([exe], cwd=cwd)
    settings = _settings()
    env = os.environ.copy()
    env['WINEPREFIX'] = str(_BASE / 'wineprefix')
    env['WINEDEBUG'] = '-all'
    env['WINEDLLOVERRIDES'] = 'mscoree,mshtml='
    env['WINEESYNC'] = '0'
    env['WINEFSYNC'] = '0'
    proc = subprocess.Popen([settings.get('wine', 'wine'), exe], cwd=cwd, env=env, start_new_session=True)
    _GAME_PID = proc.pid
    return proc

def _belongs_to_game(w, pid):
    if not w.pid:
        return False
    import psutil
    try:
        process = psutil.Process(w.pid)
        if w.pid == pid or any(p.pid == pid for p in process.parents()):
            return True
        # Wine reparents PE processes to init; confirm BOTH dedicated prefix and game cwd.
        return (bool(_GAME_CWD) and process.cwd() == _GAME_CWD
                and process.environ().get("WINEPREFIX") == str(_BASE / "wineprefix"))
    except psutil.Error:
        return False

def find_game_hwnd_by_pid(pid, timeout_s=15.0, poll=0.1):
    global _TARGET, _GAME_PROCESS
    from PY.platform_windows import getWindowsWithTitle
    from PY.config import window_title
    end = time.monotonic() + timeout_s
    while True:
        for w in getWindowsWithTitle(window_title):
            if _belongs_to_game(w, pid):
                import psutil
                _TARGET = w._hWnd
                _GAME_PROCESS = psutil.Process(w.pid)
                _apply_key_grabs()
                return _TARGET
        if time.monotonic() >= end:
            return None
        time.sleep(max(poll, 0.01))

def is_hwnd_valid(hwnd):
    from PY.platform_windows import Window
    try:
        if not hwnd:
            return False
        # Minimized windows still exist and must not terminate a run.
        Window(hwnd)._window.get_attributes()
        return True
    except Exception:
        return False

def game_is_active():
    from PY.platform_windows import getWindowsWithTitle, Window
    from PY.config import window_title
    try:
        if _TARGET:
            return Window(_TARGET).isActive
        return any(w.isActive for w in getWindowsWithTitle(window_title))
    except Exception:
        return False

def focus_hwnd(hwnd):
    global _TARGET
    if not is_hwnd_valid(hwnd):
        raise RuntimeError('Game window is unavailable; input was not sent.')
    from PY.platform_windows import Window
    if not Window(hwnd).isActive:
        subprocess.run(['xdotool', 'windowactivate', '--sync', str(hwnd)], check=True, timeout=2)
    if not Window(hwnd).isActive:
        raise RuntimeError('Game focus could not be verified; input was not sent.')
    _TARGET = hwnd

_VK = {0x11:'Control_L', 0x1b:'Escape', 0x52:'r', 0x53:'s', 0x71:'F2', 0x72:'F3'}

def get_async_key_state(vk):
    if os.name == 'nt':
        import ctypes
        return ctypes.windll.user32.GetAsyncKeyState(vk)
    from Xlib import XK
    from PY.platform_windows import connection
    d = connection()
    keys = d.query_keymap()
    names = ['Control_L', 'Control_R'] if vk == 0x11 else [_VK[vk]]
    for name in names:
        code = d.keysym_to_keycode(XK.string_to_keysym(name))
        if code and keys[code//8] & (1 << (code%8)):
            return 0x8000
    return 0

def _send(names, delay):
    from Xlib import X, XK
    from Xlib.ext import xtest
    from PY.platform_windows import connection
    if not _TARGET:
        raise RuntimeError('No verified game window; input was not sent.')
    focus_hwnd(_TARGET)
    d = connection()
    codes = [d.keysym_to_keycode(XK.string_to_keysym(name)) for name in names]
    pressed = []
    locked = _FULL_LOCK
    if locked:
        _apply_key_grabs(full=False)
        d.ungrab_keyboard(0)
        d.sync()
    try:
        for code in codes:
            xtest.fake_input(d, X.KeyPress, code)
            pressed.append(code)
        d.sync()
        time.sleep(delay)
    finally:
        for code in reversed(pressed):
            xtest.fake_input(d, X.KeyRelease, code)
        d.sync()
        if locked:
            _apply_key_grabs()

def send_virtual_key(vk_code, down_up_sleep=0.05):
    _send([_VK[vk_code]], down_up_sleep)

def send_ctrl_s():
    _send(['Control_L', 's'], 0.05)

def send_esc():
    send_virtual_key(0x1b, 0.03)

def send_key_R():
    send_virtual_key(0x52, 0.03)

def terminate_proc_tree(proc, name='subprocess', wait_s=0.8):
    if proc is None:
        return
    import psutil
    targets = {}
    def add(process):
        try:
            targets[process.pid] = process
            for child in process.children(recursive=True):
                targets[child.pid] = child
        except psutil.NoSuchProcess:
            pass
    if proc.pid == _GAME_PID:
        if _GAME_PROCESS is not None:
            add(_GAME_PROCESS)
        elif _GAME_CWD:
            for process in psutil.process_iter(['pid', 'cwd']):
                try:
                    if (process.info['cwd'] == _GAME_CWD and
                            process.environ().get('WINEPREFIX') == str(_BASE / 'wineprefix')):
                        add(process)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
    try:
        add(psutil.Process(proc.pid))
    except psutil.NoSuchProcess:
        pass
    for process in targets.values():
        try: process.terminate()
        except psutil.NoSuchProcess: pass
    _, alive = psutil.wait_procs(list(targets.values()), timeout=wait_s)
    for process in alive:
        try: process.kill()
        except psutil.NoSuchProcess: pass
    if alive:
        psutil.wait_procs(alive, timeout=wait_s)


def release_input_locks():
    global _CHARACTER_LOCK, _FULL_LOCK
    _CHARACTER_LOCK = _FULL_LOCK = False
    try:
        _apply_key_grabs()
        from PY.platform_windows import connection
        d = connection()
        d.ungrab_keyboard(0)
        d.sync()
    except Exception:
        pass


def play_sound(path):
    if Path(path).is_file() and shutil.which('paplay'):
        subprocess.Popen(['paplay', str(path)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


_CHARACTER_LOCK = False
_FULL_LOCK = False

def _apply_key_grabs(full=None):
    if not _TARGET or not is_hwnd_valid(_TARGET):
        return
    from Xlib import X, XK
    from PY.platform_windows import connection, Window
    d = connection()
    w = Window(_TARGET)._window
    w.ungrab_key(X.AnyKey, X.AnyModifier)
    lock_all = _FULL_LOCK if full is None else full
    if lock_all:
        w.grab_key(X.AnyKey, X.AnyModifier, False, X.GrabModeAsync, X.GrabModeAsync)
    elif _CHARACTER_LOCK:
        code = d.keysym_to_keycode(XK.string_to_keysym('F3'))
        w.grab_key(code, X.AnyModifier, False, X.GrabModeAsync, X.GrabModeAsync)
    d.sync()
    while d.pending_events():
        d.next_event()

def enable_character_lock():
    global _CHARACTER_LOCK
    _CHARACTER_LOCK = True
    _apply_key_grabs()

def disable_character_lock():
    global _CHARACTER_LOCK
    _CHARACTER_LOCK = False
    _apply_key_grabs()

def enable_full_keyboard_lock():
    global _FULL_LOCK
    _FULL_LOCK = True
    _apply_key_grabs()

def disable_full_keyboard_lock():
    global _FULL_LOCK
    _FULL_LOCK = False
    _apply_key_grabs()

if os.name=='nt':
    def is_hwnd_valid(hwnd):
        from windows_api import user
        return bool(hwnd and user.IsWindow(hwnd))
    def game_is_active():
        from lab import game_window
        try:return game_window().isActive
        except RuntimeError:return False
    def focus_hwnd(hwnd):
        from PY.platform_windows import Window
        if not is_hwnd_valid(hwnd):raise RuntimeError('Game window unavailable')
        Window(hwnd).activate()
    def play_sound(path):
        import winsound
        if Path(path).is_file():winsound.PlaySound(str(path),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
