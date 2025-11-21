import time, ctypes
from ctypes import wintypes
try:
    from PY.logger import log
except ModuleNotFoundError:
    from logger import log
def _enum_windows_for_pid(target_pid):
    EnumWindows = ctypes.windll.user32.EnumWindows
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    result_hwnd = ctypes.c_void_p(0)
    def callback(hwnd, lParam):
        nonlocal result_hwnd
        pid = wintypes.DWORD(0)
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == target_pid and IsWindowVisible(hwnd):
            result_hwnd = ctypes.c_void_p(hwnd)
            return False
        return True
    EnumWindows(EnumWindowsProc(callback), 0)
    return result_hwnd.value or None
def find_game_hwnd_by_pid(pid: int, timeout_s: float = 15.0, poll: float = 0.1):
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        hwnd = _enum_windows_for_pid(pid)
        if hwnd:
            return hwnd
        time.sleep(poll)
    return None
def is_hwnd_valid(hwnd) -> bool:
    if not hwnd:
        return False
    IsWindow = ctypes.windll.user32.IsWindow
    IsWindowVisible = ctypes.windll.user32.IsWindowVisible
    IsIconic = ctypes.windll.user32.IsIconic
    try:
        return bool(IsWindow(hwnd)) and bool(IsWindowVisible(hwnd)) and not bool(IsIconic(hwnd))
    except Exception:
        return False
def focus_hwnd(hwnd):
    try:
        ctypes.windll.user32.SetForegroundWindow(hwnd)
    except Exception:
        pass
def send_virtual_key(vk_code, down_up_sleep=0.05):
    KEYEVENTF_KEYUP = 0x0002
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    time.sleep(down_up_sleep)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)
def send_ctrl_s():
    VK_CONTROL = 0x11
    VK_S = 0x53
    ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0, 0)
    time.sleep(0.03)
    ctypes.windll.user32.keybd_event(VK_S, 0, 0, 0)
    time.sleep(0.03)
    ctypes.windll.user32.keybd_event(VK_S, 0, 0x0002, 0)
    time.sleep(0.02)
    ctypes.windll.user32.keybd_event(VK_CONTROL, 0, 0x0002, 0)
    log("⌨️ Sent Ctrl+S (press only)")
def send_esc():
    VK_ESCAPE = 0x1B
    send_virtual_key(VK_ESCAPE, down_up_sleep=0.03)
    log("⎋ Esc pressed")
def send_key_R():
    VK_R = 0x52
    send_virtual_key(VK_R, down_up_sleep=0.03)
    log("🔁 R pressed")
def terminate_proc_tree(proc, name="subprocess", wait_s=0.8):
    try:
        if proc and proc.poll() is None:
            proc.terminate()
            t0 = time.time()
            while proc.poll() is None and (time.time() - t0) < wait_s:
                time.sleep(0.05)
            if proc.poll() is None:
                try:
                    import subprocess as _sp
                    _sp.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                            capture_output=True, check=False)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            log(f"{name} terminated.")
    except Exception as e:
        log(f"⚠️ Failed to terminate {name}: {e}")
