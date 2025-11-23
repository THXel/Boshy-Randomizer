import os
import time
import threading

try:
    import pygetwindow as gw
except Exception:
    gw = None

from .logger import log
from .config import window_title, window_title_variants, ini_folder

try:
    from .config import overlays_enabled
except Exception:
    overlays_enabled = True

import tkinter as tk


def _find_game_window_rect():
    try:
        if gw is None:
            return None
        try:
            wins = gw.getWindowsWithTitle(window_title)
            if wins:
                w = wins[0]
                if int(w.width) > 100 and int(w.height) > 100 and getattr(
                    w,
                    "isVisible",
                    True,
                ):
                    return int(w.left), int(w.top), int(w.width), int(w.height)
        except Exception:
            pass
        try:
            titles = gw.getAllTitles()
        except Exception:
            titles = []
        for t in titles:
            low = (t or "").lower()
            for v in (window_title_variants or []):
                if not v:
                    continue
                if v.lower() in low:
                    try:
                        ws = gw.getWindowsWithTitle(t)
                        if ws:
                            w = ws[0]
                            if int(w.width) > 100 and int(w.height) > 100 and getattr(
                                w,
                                "isVisible",
                                True,
                            ):
                                return int(w.left), int(w.top), int(w.width), int(
                                    w.height
                                )
                    except Exception:
                        continue
    except Exception:
        pass
    return None


def _center_rect_over(width, height):
    rect = _find_game_window_rect()
    if rect:
        left, top, gw_w, gw_h = rect
        x = left + (gw_w - width) // 2
        y = top + (gw_h - height) // 2
        return x, y, width, height
    try:
        root = tk.Tk()
        root.withdraw()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.destroy()
    except Exception:
        sw, sh = 1920, 1080
    x = (sw - width) // 2
    y = (sh - height) // 2
    return x, y, width, height


def _full_game_rect():
    rect = _find_game_window_rect()
    if rect:
        l, t, w, h = rect
        return l, t, w, h
    try:
        root = tk.Tk()
        root.withdraw()
        sw = root.winfo_screenwidth()
        sh = root.winfo_screenheight()
        root.destroy()
    except Exception:
        sw, sh = 1920, 1080
    return 0, 0, sw, sh


_overlay_thread = None
_overlay_stop_event = None
_overlay_external_stop_event = None
_overlay_lock = threading.Lock()
_overlay_active = False


def _overlay_loop(text, step_info, blackout, max_duration_s, route_code=None):
    global _overlay_stop_event, _overlay_external_stop_event, _overlay_active
    try:
        root = tk.Tk()
    except Exception as e:
        log(f"⚠️ Tkinter overlay init failed: {e}")
        return
    _overlay_active = True
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    if blackout:
        x, y, w, h = _full_game_rect()
        bg = "black"
    else:
        w, h = 520, 220
        x, y, w, h = _center_rect_over(w, h)
        bg = "#101010"
    try:
        root.geometry(f"{w}x{h}+{x}+{y}")
    except Exception:
        pass
    root.configure(bg=bg)
    logo_img = None
    try:
        project_root = os.path.dirname(ini_folder)
        img_path = os.path.join(project_root, "Custom", "boshy_randomizer.png")
        if os.path.exists(img_path):
            logo_img = tk.PhotoImage(file=img_path)
        else:
            log(f"ℹ️ boshy_randomizer.png not found at: {img_path}")
    except Exception as e:
        log(f"⚠️ Failed to load boshy_randomizer.png: {e}")
        logo_img = None
    frame = tk.Frame(root, bg=bg)
    frame.pack(expand=True, fill="both")
    if logo_img is not None:
        logo_label = tk.Label(frame, image=logo_img, bg=bg)
        logo_label.image = logo_img
        logo_label.pack(pady=(10, 5))
    if route_code:
        try:
            seed_label = tk.Label(
                frame,
                text=f"Seed: {route_code}",
                fg="#FFFFFF",
                bg=bg,
                font=("Consolas", 16, "bold"),
            )
            seed_label.place(relx=1.0, x=-16, y=10, anchor="ne")
        except Exception as e:
            log(f"⚠️ Failed to draw seed label: {e}")
    lbl_main = tk.Label(
        frame,
        text=text or "Loading next stage...",
        fg="#00D1FF",
        bg=bg,
        font=("Consolas", 20, "bold"),
    )
    lbl_main.pack(expand=True)
    if step_info:
        lbl_step = tk.Label(
            frame,
            text=step_info,
            fg="#AAAAAA",
            bg=bg,
            font=("Consolas", 11, "italic"),
        )
        lbl_step.pack(pady=(0, 10))
    try:
        root.attributes("-alpha", 0.0)
        steps = 6
        for i in range(steps + 1):
            alpha = i / steps
            root.attributes("-alpha", alpha)
            root.update_idletasks()
            root.update()
            time.sleep(0.02)
    except Exception:
        pass
    start_t = time.time()
    while True:
        try:
            root.update_idletasks()
            root.update()
        except tk.TclError:
            break
        if _overlay_stop_event is not None and _overlay_stop_event.is_set():
            break
        if _overlay_external_stop_event is not None and _overlay_external_stop_event.is_set():
            break
        if max_duration_s is not None and max_duration_s > 0:
            if time.time() - start_t > max_duration_s:
                break
        time.sleep(0.01)
    try:
        steps = 6
        for i in range(steps, -1, -1):
            alpha = i / steps
            root.attributes("-alpha", alpha)
            root.update_idletasks()
            root.update()
            time.sleep(0.02)
    except Exception:
        pass
    try:
        root.destroy()
    except tk.TclError:
        pass
    _overlay_active = False


def show_loading_overlay(
    stop_event=None,
    duration=0.3,
    text="Loading next stage...",
    step_info=None,
    blackout=False,
    route_code=None,
):
    if not overlays_enabled:
        return
    global _overlay_external_stop_event
    old_ext = _overlay_external_stop_event
    _overlay_external_stop_event = stop_event
    try:
        _overlay_loop(
            text=text,
            step_info=step_info,
            blackout=blackout,
            max_duration_s=float(duration),
            route_code=route_code,
        )
    except Exception as e:
        log(f"⚠️ show_loading_overlay (Tk) error: {e}")
    finally:
        _overlay_external_stop_event = old_ext


def begin_loading_overlay(
    stop_event=None,
    text="Loading next stage...",
    step_info=None,
    max_duration_s=2.0,
    blackout=False,
    route_code=None,
):
    if not overlays_enabled:
        return
    global _overlay_thread, _overlay_stop_event, _overlay_external_stop_event
    with _overlay_lock:
        if _overlay_thread is not None and _overlay_thread.is_alive():
            return
        _overlay_stop_event = threading.Event()
        _overlay_external_stop_event = stop_event

        def runner():
            try:
                _overlay_loop(
                    text=text,
                    step_info=step_info,
                    blackout=blackout,
                    max_duration_s=float(max_duration_s),
                    route_code=route_code,
                )
            except Exception as e:
                log(f"⚠️ begin_loading_overlay runner error: {e}")
            finally:
                global _overlay_thread, _overlay_stop_event, _overlay_external_stop_event
                with _overlay_lock:
                    _overlay_thread = None
                    _overlay_stop_event = None
                    _overlay_external_stop_event = None

        _overlay_thread = threading.Thread(target=runner, daemon=True)
        _overlay_thread.start()


def end_loading_overlay():
    if not overlays_enabled:
        return
    global _overlay_thread, _overlay_stop_event
    with _overlay_lock:
        if _overlay_thread is None:
            return
        if _overlay_stop_event is not None:
            _overlay_stop_event.set()
    try:
        _overlay_thread.join(timeout=0.5)
    except Exception:
        pass


def is_loading_overlay_active():
    return _overlay_active
