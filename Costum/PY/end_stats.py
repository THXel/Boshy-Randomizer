# PY/end_stats.py
import os
import time
import json
import threading
import tkinter as tk
from tkinter import BOTH, Canvas
from PIL import Image, ImageDraw, ImageTk, ImageFont
import pygetwindow as gw

from PY.logger import log
from PY.config import json_path, window_title

# Farben & Style
BG_COLOR = "#000000"
FG_COLOR = "#FFFFFF"
ACCENT   = "#00D1FF"
TEXT_DIM = "#AAAAAA"

def _find_game_window_rect():
    """Findet das Spiel-Fenster anhand des Titels."""
    try:
        wins = gw.getWindowsWithTitle(window_title)
        if wins:
            w = wins[0]
            if w.width > 100 and w.height > 100 and w.isVisible:
                return (w.left, w.top, w.width, w.height)
    except Exception:
        pass
    return None


def _centered_geometry_over_game(w, h):
    """Berechnet Geometry-String, zentriert über Spiel oder Bildschirm."""
    rect = _find_game_window_rect()
    if rect:
        left, top, gw_width, gw_height = rect
        x = left + (gw_width - w) // 2
        y = top + (gw_height - h) // 2
        return f"{w}x{h}+{int(x)}+{int(y)}"
    else:
        root_probe = tk.Tk()
        root_probe.withdraw()
        sw = root_probe.winfo_screenwidth()
        sh = root_probe.winfo_screenheight()
        root_probe.destroy()
        x = (sw - w) // 2
        y = (sh - h) // 2
        return f"{w}x{h}+{int(x)}+{int(y)}"


def _draw_rounded_rect(canvas, x1, y1, x2, y2, r, fill):
    """Zeichnet einen abgerundeten Hintergrund."""
    canvas.create_rectangle(x1 + r, y1, x2 - r, y2, fill=fill, outline="")
    canvas.create_rectangle(x1, y1 + r, x2, y2 - r, fill=fill, outline="")
    for dx in (0, x2 - 2 * r - x1):
        for dy in (0, y2 - 2 * r - y1):
            canvas.create_oval(x1 + dx, y1 + dy, x1 + dx + 2 * r, y1 + dy + 2 * r, fill=fill, outline="")


def show_end_stats(stop_event):
    """
    Zentriertes Overlay mit Fade, Logo, Statistiken & ESC zum Schließen.
    """

    def _run():
        try:
            # JSON lesen
            stats_data = {}
            if os.path.exists(json_path):
                with open(json_path, "r", encoding="utf-8") as f:
                    stats_data = json.load(f)
            save = stats_data.get("savefile", {})
            stats = save.get("stats", {})

            # Stats auswerten
            deaths = int(stats.get("deaths", 0)) if str(stats.get("deaths", "")).isdigit() else "N/A"
            diff_raw = str(stats.get("difficulty", "N/A"))
            timesec = int(stats.get("timeseconds", 0)) if str(stats.get("timeseconds", "")).isdigit() else 0

            diff_map = {
                "0": "Ez-Mode",
                "1": "Totally Average-Mode",
                "2": "Hardon-Mode",
                "3": "You're gonna rage-Mode"
            }
            difficulty = diff_map.get(diff_raw, diff_raw)
            h = timesec // 3600
            m = (timesec % 3600) // 60
            s = timesec % 60
            time_str = f"{h:02d}:{m:02d}:{s:02d}"

            collectables = list(save.get("collectables", {}).keys())
            unlockables = list(stats_data.get("license", {}).get("unlockables", {}).keys())
            achievements = list(save.get("achievements", {}).keys())
            boss_deaths = {k: v for k, v in save.get("bosses", {}).items() if str(v).isdigit() and int(v) > 0}

            # Fensterposition
            w, h = 900, 620
            geom = _centered_geometry_over_game(w, h)

            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.attributes("-alpha", 0.0)
            root.geometry(geom)
            root.configure(bg=BG_COLOR)

            # Canvas & Hintergrund
            canvas = Canvas(root, bg=BG_COLOR, highlightthickness=0)
            canvas.pack(fill=BOTH, expand=True)
            _draw_rounded_rect(canvas, 10, 10, w - 10, h - 10, 25, fill=BG_COLOR)

            # Text & Layout
            pad_y = 30
            canvas.create_text(w//2, pad_y + 10, text="🏁 RUN COMPLETE!", fill=ACCENT, font=("Consolas", 26, "bold"))
            pad_y += 50
            canvas.create_text(w//2, pad_y, text=f"💀 Deaths: {deaths}", fill=FG_COLOR, font=("Consolas", 16))
            pad_y += 25
            canvas.create_text(w//2, pad_y, text=f"⚙️ Difficulty: {difficulty}", fill=FG_COLOR, font=("Consolas", 16))
            pad_y += 25
            canvas.create_text(w//2, pad_y, text=f"⏱️ Time Played: {time_str}", fill=FG_COLOR, font=("Consolas", 16))
            pad_y += 25
            canvas.create_text(w//2, pad_y, text=f"🎁 Collectables: {len(collectables)}", fill=FG_COLOR, font=("Consolas", 16))
            pad_y += 25
            canvas.create_text(w//2, pad_y, text=f"👾 Unlockables: {len(unlockables)}", fill=FG_COLOR, font=("Consolas", 16))
            pad_y += 25
            canvas.create_text(w//2, pad_y, text=f"🏆 Achievements: {len(achievements)}", fill=FG_COLOR, font=("Consolas", 16))
            pad_y += 25
            canvas.create_text(w//2, pad_y, text=f"☠️ Boss Deaths: {len(boss_deaths)}", fill=FG_COLOR, font=("Consolas", 16))
            pad_y += 40
            canvas.create_text(w//2, pad_y, text="Press ESC to close • Auto-closes in 30s",
                               fill=TEXT_DIM, font=("Consolas", 12, "italic"))

            # ESC schließt Overlay + Trigger
            def close_event(event=None):
                try:
                    for a in range(95, -1, -10):
                        if stop_event.is_set():
                            break
                        root.attributes("-alpha", a / 100)
                        root.update()
                        time.sleep(0.02)
                    root.destroy()

                    # Trigger end.ini
                    from PY.save_utils import copy_dest
                    from PY.reload_sequence import send_reload_sequence

                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    ini_folder = os.path.join(base_dir, "..", "INI")
                    iwbtb_folder = os.path.join(base_dir, "..", "IWBTB")

                    end_path = os.path.join(ini_folder, "end.ini")
                    dest_path = os.path.join(iwbtb_folder, "SaveFile1.ini")

                    if os.path.exists(end_path) and os.path.exists(dest_path):
                        copy_dest(end_path, dest_path)
                        log("🎯 End-Stats ESC trigger: end.ini → SaveFile1.ini")
                        send_reload_sequence()
                    else:
                        log("⚠️ End-Stats ESC trigger failed (missing end.ini or SaveFile1.ini)")
                except Exception as e:
                    log(f"⚠️ End-Stats ESC trigger error: {e}")

            root.bind("<Escape>", close_event)

            # Fade-In
            for a in range(0, 95, 10):
                if stop_event.is_set():
                    root.destroy()
                    return
                root.attributes("-alpha", a / 100)
                root.update()
                time.sleep(0.03)

            # Offen halten (bis ESC oder Timeout)
            t_end = time.time() + 30
            while time.time() < t_end and not stop_event.is_set():
                root.update()
                time.sleep(0.05)

            close_event()

        except Exception as e:
            log(f"⚠️ Failed to display end screen: {e}")

    threading.Thread(target=_run, daemon=True).start()
