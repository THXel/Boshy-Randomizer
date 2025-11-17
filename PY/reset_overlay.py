# PY/reset_overlay.py
import time
import threading
import tkinter as tk
from tkinter import BOTH, Canvas

import pygetwindow as gw

from .config import window_title
from .logger import log

# Farben & Stil
BG_COLOR = "#000000"
FG_COLOR = "#FFFFFF"
ACCENT   = "#00D1FF"


def _find_game_window_rect():
    """Sucht das erste Fenster, dessen Titel window_title enthält."""
    try:
        wins = gw.getWindowsWithTitle(window_title)
        if wins:
            w = wins[0]
            if w.width > 100 and w.height > 100 and w.isVisible:
                return (w.left, w.top, w.width, w.height)
    except Exception:
        pass
    return None


def _lower_half_geometry_over_game(w, h, offset_ratio=0.35):
    """
    Positioniert das Overlay in der unteren Bildschirmhälfte
    (etwa ein Drittel über dem unteren Rand).
    offset_ratio bestimmt, wie hoch über dem unteren Rand das Overlay sitzt (0.0–1.0).
    """
    rect = _find_game_window_rect()
    if rect:
        left, top, gw_width, gw_height = rect
        x = left + (gw_width - w) // 2
        y = top + int(gw_height * (1 - offset_ratio)) - h // 2
    else:
        # Fallback → Bildschirmmitte unten
        root_probe = tk.Tk()
        root_probe.withdraw()
        sw, sh = root_probe.winfo_screenwidth(), root_probe.winfo_screenheight()
        root_probe.destroy()
        x = (sw - w) // 2
        y = int(sh * (1 - offset_ratio)) - h // 2
    return x, y


def _top_left_geometry_over_game(w, h, margin=20):
    """
    Positioniert ein kleines Fenster oben links über dem Spiel.
    Fallback: oben links am Bildschirm.
    """
    rect = _find_game_window_rect()
    if rect:
        left, top, gw_width, gw_height = rect
        x = left + margin
        y = top + margin
    else:
        root_probe = tk.Tk()
        root_probe.withdraw()
        x, y = margin, margin
        root_probe.destroy()
    return x, y


def _draw_rounded_rect(canvas, x1, y1, x2, y2, r, fill):
    """Zeichnet eine abgerundete Karte ohne Pillow-Abhängigkeit."""
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")
    canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline="")
    for dx in (0, x2 - 2 * r - x1):
        for dy in (0, y2 - 2 * r - y1):
            canvas.create_oval(
                x1 + dx, y1 + dy,
                x1 + dx + 2 * r, y1 + dy + 2 * r,
                fill=fill, outline=""
            )


def show_reset_overlay(stop_event, duration=4.0, route_code=None, route_code_duration=15.0):
    """
    Kurzes HINT-Overlay direkt über dem IWBTB-Fenster.

    - Hauptoverlay: unten im Game-Fenster (wie vorher, aber hart ans Game „geklebt“)
    - Route-Code-Fenster: oben links im Game-Fenster mit Copy-Button
    - Beide Fenster werden über dem Boshy-Fenster positioniert und fokussiert.
    """
    def _run():
        from .logger import log  # falls direkt getestet wird

        try:
            # --- Hauptoverlay (unten im Game-Fenster) ---
            w, h = 640, 160
            x, y = _lower_half_geometry_over_game(w, h, offset_ratio=0.35)

            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            try:
                root.attributes("-alpha", 0.0)
            except Exception:
                pass
            root.configure(bg=BG_COLOR)
            root.geometry(f"{w}x{h}+{x}+{y}")
            root.focus_force()
            root.lift()

            canvas = Canvas(root, width=w, height=h, highlightthickness=0, bg=BG_COLOR)
            canvas.pack(fill=BOTH, expand=True)

            # Karte
            margin = 10
            _draw_rounded_rect(
                canvas,
                margin, margin,
                w - margin, h - margin,
                r=16,
                fill="#202020"
            )

            # Text-Inhalt
            title = "HINT"
            lines = [
                "only SaveFile 1 is available",
                "Press multiple times Ctrl+R to reset and create a new seed",
            ]
            canvas.create_text(
                w // 2, 40,
                text=title,
                fill=ACCENT,
                font=("Segoe UI", 18, "bold")
            )
            canvas.create_text(
                w // 2, 90,
                text="\n".join(lines),
                fill=FG_COLOR,
                font=("Segoe UI", 13),
                justify="center"
            )

            # --- Route-Code-Fenster (oben links im Game-Fenster) ---
            code_win = None
            if route_code:
                cw, ch = 260, 90
                cx, cy = _top_left_geometry_over_game(cw, ch, margin=20)
                code_win = tk.Toplevel(root)
                code_win.overrideredirect(True)
                code_win.attributes("-topmost", True)
                try:
                    code_win.attributes("-alpha", 0.0)
                except Exception:
                    pass
                code_win.configure(bg=BG_COLOR)
                code_win.geometry(f"{cw}x{ch}+{cx}+{cy}")
                code_win.lift()

                frame = tk.Frame(code_win, bg="#181818", bd=0)
                frame.pack(fill="both", expand=True)

                lbl_title = tk.Label(
                    frame,
                    text="Route Code",
                    bg="#181818",
                    fg=ACCENT,
                    font=("Segoe UI", 11, "bold"),
                    anchor="w"
                )
                lbl_title.pack(fill="x", padx=10, pady=(6, 0))

                lbl_code = tk.Label(
                    frame,
                    text=str(route_code),
                    bg="#181818",
                    fg=FG_COLOR,
                    font=("Consolas", 11),
                    anchor="w"
                )
                lbl_code.pack(fill="x", padx=10, pady=(2, 4))

                feedback_var = tk.StringVar(value="")

                def _copy_code():
                    try:
                        code_win.clipboard_clear()
                        code_win.clipboard_append(str(route_code))
                        feedback_var.set("Copied!")
                    except Exception as e:
                        feedback_var.set("Copy failed")
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

                lbl_feedback = tk.Label(
                    frame,
                    textvariable=feedback_var,
                    bg="#181818",
                    fg="gray70",
                    font=("Segoe UI", 9),
                    anchor="w"
                )
                lbl_feedback.pack(side="left", padx=(0, 10), pady=(0, 8))

            # Fade-In
            for a in range(0, 96, 8):
                if stop_event.is_set():
                    try:
                        root.destroy()
                    except Exception:
                        pass
                    return
                try:
                    root.attributes("-alpha", a / 100.0)
                    if code_win is not None:
                        code_win.attributes("-alpha", a / 100.0)
                except Exception:
                    pass
                root.update()
                if code_win is not None:
                    try:
                        code_win.update()
                    except Exception:
                        pass
                time.sleep(0.02)

            start = time.time()
            hint_end = start + float(duration)
            code_end = start + (float(route_code_duration) if route_code else float(duration))

            hint_hidden = False
            code_hidden = (code_win is None)

            # Gemeinsame Lauf-Schleife
            while not stop_event.is_set():
                now = time.time()

                # Hauptoverlay ausblenden
                if not hint_hidden and now >= hint_end:
                    try:
                        for a in range(96, -1, -8):
                            if stop_event.is_set():
                                break
                            root.attributes("-alpha", a / 100.0)
                            root.update()
                            time.sleep(0.02)
                    except Exception:
                        pass
                    hint_hidden = True
                    try:
                        root.withdraw()
                    except Exception:
                        pass

                # Code-Fenster ausblenden
                if not code_hidden and now >= code_end and code_win is not None:
                    try:
                        for a in range(96, -1, -8):
                            if stop_event.is_set():
                                break
                            code_win.attributes("-alpha", a / 100.0)
                            code_win.update()
                            time.sleep(0.02)
                    except Exception:
                        pass
                    try:
                        code_win.destroy()
                    except Exception:
                        pass
                    code_hidden = True

                if hint_hidden and code_hidden:
                    break

                try:
                    root.update()
                    if code_win is not None and not code_hidden:
                        code_win.update()
                except Exception:
                    break

                time.sleep(0.02)

            try:
                root.destroy()
            except Exception:
                pass

        except Exception as e:
            log(f"⚠️ Reset overlay failed inside thread: {e}")

    # Thread starten (so wie beim end_stats-Overlay)
    threading.Thread(target=_run, daemon=True).start()

