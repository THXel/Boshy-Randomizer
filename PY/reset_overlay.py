# PY/reset_overlay.py
import os
import time
import threading
import tkinter as tk
from tkinter import BOTH, Canvas
import pygetwindow as gw

from .config import window_title, custom_folder
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
        root_probe = tk.Tk()
        root_probe.withdraw()
        sw, sh = root_probe.winfo_screenwidth(), root_probe.winfo_screenheight()
        root_probe.destroy()
        x = (sw - w) // 2
        y = int(sh * (1 - offset_ratio)) - h // 2
    return f"{w}x{h}+{int(x)}+{int(y)}"


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


def show_reset_overlay(stop_event, duration=4.0):
    """Kurzes HINT-Overlay in der unteren Bildschirmhälfte."""
    def _run():
        try:
            w, h = 640, 160
            geom = _lower_half_geometry_over_game(w, h, offset_ratio=0.35)

            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.attributes("-alpha", 0.0)
            root.configure(bg=BG_COLOR)
            root.geometry(geom)

            c = Canvas(root, bg=BG_COLOR, highlightthickness=0)
            c.pack(fill=BOTH, expand=True)
            _draw_rounded_rect(c, 14, 14, w - 14, h - 14, 20, fill=BG_COLOR)

            # --- Titel ---
            c.create_text(
                w // 2, 40,
                text="HINT",
                fill=ACCENT,
                font=("Consolas", 22, "bold")
            )

            # --- Hinweise ---
            texts = [
                c.create_text(w // 2, 85, text="Press Ctrl + R to reset and roll a new route..",
                              fill=FG_COLOR, font=("Consolas", 12), state="hidden"),
                c.create_text(w // 2, 105, text="Only SaveFile1 is active — other slots are disabled.",
                              fill=FG_COLOR, font=("Consolas", 12), state="hidden"),
                c.create_text(w // 2, 125, text="When you close the Game, the Run is Dead.",
                              fill="#AAAAAA", font=("Consolas", 11, "italic"), state="hidden"),
            ]

            # --- Fade-In ---
            for a in range(0, 95, 8):
                if stop_event.is_set():
                    root.destroy()
                    return
                root.attributes("-alpha", a / 100.0)
                root.update()
                time.sleep(0.02)

            # --- Texte nacheinander einblenden ---
            for t in texts:
                if stop_event.is_set():
                    root.destroy()
                    return
                c.itemconfigure(t, state="normal")
                root.update()
                time.sleep(0.25)

            # --- Sichtbar bleiben ---
            t_end = time.time() + duration
            while time.time() < t_end and not stop_event.is_set():
                root.update()
                time.sleep(0.02)

            # --- Fade-Out ---
            for a in range(92, -1, -8):
                if stop_event.is_set():
                    root.destroy()
                    return
                root.attributes("-alpha", a / 100.0)
                root.update()
                time.sleep(0.02)

            root.destroy()

        except Exception as e:
            log(f"⚠️ Reset overlay failed inside thread: {e}")

    threading.Thread(target=_run, daemon=True).start()
