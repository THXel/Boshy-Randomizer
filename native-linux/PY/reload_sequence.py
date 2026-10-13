import ctypes
import time

from PY import platform_windows as gw

from .logger import log
from .config import window_title


def send_reload_sequence():
    from PY.window_utils import send_virtual_key
    VK_R = 0x52
    KEYUP = 0x0002

    wins = gw.getWindowsWithTitle(window_title)
    if wins:
        w = wins[0]
        try:
            if not w.isActive:
                w.activate()
                time.sleep(0.05)
        except Exception:
            pass

    for i in range(2):
        send_virtual_key(VK_R, 0.05)
        if i == 0:
            time.sleep(0.12)

    log("R sequence executed (2x R with short pause)")
