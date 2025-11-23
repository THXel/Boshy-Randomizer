import time
import threading
import tkinter as tk
from tkinter import BOTH, Canvas, TclError
import pygetwindow as gw

from .config import window_title
from .logger import log

BG_COLOR = "#000000"
FG_COLOR = "#FFFFFF"
ACCENT = "#00D1FF"

_overlay_lock = threading.Lock()


def _find_game_window_rect():
    try:
        wins = gw.getWindowsWithTitle(window_title)
        if wins:
            w = wins[0]
            if w.width > 100 and w.height > 100 and w.isVisible:
                return w.left, w.top, w.width, w.height
    except Exception:
        pass
    return None


def _lower_half_geometry_over_game(w, h, offset_ratio=0.35):
    rect = _find_game_window_rect()
    if rect:
        left, top, gw_width, gw_height = rect
        x = left + (gw_width - w) // 2
        y = top + int(gw_height * (1 - offset_ratio)) - h // 2
    else:
        root_probe = None
        try:
            root_probe = tk.Tk()
            root_probe.withdraw()
            sw, sh = root_probe.winfo_screenwidth(), root_probe.winfo_screenheight()
        except Exception:
            sw, sh = 1920, 1080
        finally:
            if root_probe is not None:
                try:
                    root_probe.destroy()
                except Exception:
                    pass
        x = (sw - w) // 2
        y = int(sh * (1 - offset_ratio)) - h // 2
    return x, y


def _top_left_geometry_over_game(w, h, margin=20):
    rect = _find_game_window_rect()
    if rect:
        left, top, gw_width, gw_height = rect
        x = left + margin
        y = top + margin
    else:
        root_probe = None
        try:
            root_probe = tk.Tk()
            root_probe.withdraw()
            x, y = margin, margin
        except Exception:
            x, y = margin, margin
        finally:
            if root_probe is not None:
                try:
                    root_probe.destroy()
                except Exception:
                    pass
    return x, y


def _draw_rounded_rect(canvas, x1, y1, x2, y2, r, fill):
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")
    canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline="")
    for dx in (0, x2 - 2 * r - x1):
        for dy in (0, y2 - 2 * r - y1):
            canvas.create_oval(
                x1 + dx,
                y1 + dy,
                x1 + dx + 2 * r,
                y1 + dy + 2 * r,
                fill=fill,
                outline="",
            )


def show_reset_overlay(stop_event, duration=4.0, route_code=None, route_code_duration=15.0):
    def _run():
        if stop_event.is_set():
            return

        with _overlay_lock:
            if stop_event.is_set():
                return

            root = None
            code_win = None
            try:
                w, h = 640, 160
                x, y = _lower_half_geometry_over_game(w, h, offset_ratio=0.35)

                try:
                    root = tk.Tk()
                except Exception as e:
                    log(f"⚠️ Failed to create Tk root for reset overlay: {e}")
                    return

                try:
                    root.overrideredirect(True)
                except TclError:
                    pass

                try:
                    root.attributes("-topmost", True)
                except TclError:
                    pass

                try:
                    root.attributes("-alpha", 0.0)
                except TclError:
                    pass

                try:
                    root.configure(bg=BG_COLOR)
                except TclError:
                    pass

                try:
                    root.geometry(f"{w}x{h}+{x}+{y}")
                except TclError:
                    pass

                try:
                    root.focus_force()
                    root.lift()
                except TclError:
                    pass

                try:
                    canvas = Canvas(root, width=w, height=h, highlightthickness=0, bg=BG_COLOR)
                    canvas.pack(fill=BOTH, expand=True)
                except TclError as e:
                    log(f"⚠️ Failed to create canvas for reset overlay: {e}")
                    return

                margin = 10
                try:
                    _draw_rounded_rect(
                        canvas,
                        margin,
                        margin,
                        w - margin,
                        h - margin,
                        r=16,
                        fill="#202020",
                    )
                except TclError:
                    pass

                title = "HINT"
                lines = [
                    "only SaveFile 1 works, dont delete it. just play",
                    "Press Ctrl+R to reset and create a new seed",
                ]

                try:
                    canvas.create_text(
                        w // 2,
                        40,
                        text=title,
                        fill=ACCENT,
                        font=("Segoe UI", 18, "bold"),
                    )
                    canvas.create_text(
                        w // 2,
                        90,
                        text="\n".join(lines),
                        fill=FG_COLOR,
                        font=("Segoe UI", 13),
                        justify="center",
                    )
                except TclError:
                    pass

                if route_code:
                    cw, ch = 260, 90
                    cx, cy = _top_left_geometry_over_game(cw, ch, margin=20)
                    try:
                        code_win = tk.Toplevel(root)
                    except Exception as e:
                        log(f"⚠️ Failed to create Toplevel for route code: {e}")
                        code_win = None

                    if code_win is not None:
                        try:
                            code_win.overrideredirect(True)
                            code_win.attributes("-topmost", True)
                        except TclError:
                            pass
                        try:
                            code_win.attributes("-alpha", 0.0)
                        except TclError:
                            pass
                        try:
                            code_win.configure(bg=BG_COLOR)
                        except TclError:
                            pass
                        try:
                            code_win.geometry(f"{cw}x{ch}+{cx}+{cy}")
                            code_win.lift()
                        except TclError:
                            pass

                        try:
                            frame = tk.Frame(code_win, bg="#181818", bd=0)
                            frame.pack(fill="both", expand=True)

                            lbl_title = tk.Label(
                                frame,
                                text="Route Code",
                                bg="#181818",
                                fg=ACCENT,
                                font=("Segoe UI", 11, "bold"),
                                anchor="w",
                            )
                            lbl_title.pack(fill="x", padx=10, pady=(6, 0))

                            lbl_code = tk.Label(
                                frame,
                                text=str(route_code),
                                bg="#181818",
                                fg=FG_COLOR,
                                font=("Consolas", 11),
                                anchor="w",
                            )
                            lbl_code.pack(fill="x", padx=10, pady=(2, 4))

                            lbl_feedback = tk.Label(
                                frame,
                                text="",
                                bg="#181818",
                                fg="gray70",
                                font=("Segoe UI", 9),
                                anchor="w",
                            )

                            def _copy_code():
                                try:
                                    code_win.clipboard_clear()
                                    code_win.clipboard_append(str(route_code))
                                    lbl_feedback.config(text="Copied!")
                                except Exception as e:
                                    lbl_feedback.config(text="Copy failed")
                                    log(f"⚠️ Failed to copy route code: {e}")

                            btn = tk.Button(
                                frame,
                                text="Copy",
                                command=_copy_code,
                                bg=ACCENT,
                                fg="#000000",
                                relief="flat",
                                padx=8,
                                pady=2,
                                font=("Segoe UI", 10, "bold"),
                                cursor="hand2",
                            )
                            btn.pack(side="left", padx=(10, 6), pady=(0, 8))

                            lbl_feedback.pack(side="left", padx=(0, 10), pady=(0, 8))
                        except TclError as e:
                            log(f"⚠️ Failed to build route code UI: {e}")
                            try:
                                code_win.destroy()
                            except Exception:
                                pass
                            code_win = None

                for a in range(0, 96, 8):
                    if stop_event.is_set():
                        break
                    try:
                        root.attributes("-alpha", a / 100.0)
                        root.update()
                    except TclError:
                        break

                    if code_win is not None:
                        try:
                            code_win.attributes("-alpha", a / 100.0)
                            code_win.update()
                        except TclError:
                            code_win = None
                            break

                    time.sleep(0.02)

                if stop_event.is_set():
                    return

                start = time.time()
                hint_end = start + float(duration)
                code_end = start + (float(route_code_duration) if route_code else float(duration))

                hint_hidden = False
                code_hidden = code_win is None

                while not stop_event.is_set():
                    now = time.time()

                    if not hint_hidden and now >= hint_end:
                        try:
                            for a in range(96, -1, -8):
                                if stop_event.is_set():
                                    break
                                root.attributes("-alpha", a / 100.0)
                                root.update()
                                time.sleep(0.02)
                        except TclError:
                            pass
                        hint_hidden = True
                        try:
                            root.withdraw()
                        except TclError:
                            pass

                    if not code_hidden and now >= code_end and code_win is not None:
                        try:
                            for a in range(96, -1, -8):
                                if stop_event.is_set():
                                    break
                                code_win.attributes("-alpha", a / 100.0)
                                code_win.update()
                                time.sleep(0.02)
                        except TclError:
                            pass
                        try:
                            code_win.destroy()
                        except Exception:
                            pass
                        code_hidden = True

                    if hint_hidden and code_hidden:
                        break

                    try:
                        if root is not None:
                            root.update()
                    except TclError:
                        break

                    if code_win is not None and not code_hidden:
                        try:
                            code_win.update()
                        except TclError:
                            code_win = None
                            code_hidden = True

                    time.sleep(0.02)

            except Exception as e:
                log(f"⚠️ Reset overlay failed inside thread: {e}")
            finally:
                try:
                    if code_win is not None:
                        code_win.destroy()
                except Exception:
                    pass
                try:
                    if root is not None:
                        root.destroy()
                except Exception:
                    pass

    threading.Thread(target=_run, daemon=True).start()
