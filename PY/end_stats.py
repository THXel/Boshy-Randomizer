# ======================================================
# end_stats.py
#  - Endscreen-Overlay nach Solgryn (10s Delay)
#  - Liest INI/live_tracker_state.json (state_exporter)
#  - Logo + Boshy-Font, 4-Spalten-Layout, Typewriter-Effekt
#  - Scrollbar, wenn Inhalt zu groß ist
#  - Schließen: Esc, Ctrl+S, F2 oder stop_event
# ======================================================
from __future__ import annotations

import os
import re
import time
import json
import threading
import tkinter as tk
import tkinter.font as tkfont
from tkinter import BOTH, Canvas

from PIL import Image, ImageTk
import pygetwindow as gw
import traceback


# ---- Dependencies & Config ---------------------------------------------------
def _import_deps():
    log = None
    cfg = None
    try:
        from PY.logger import log as _log          # type: ignore
        from PY import config as _cfg              # type: ignore
        log = _log
        cfg = _cfg
    except Exception:
        try:
            from logger import log as _log         # type: ignore
        except Exception:
            def _log(msg: str):
                print(msg, flush=True)
        log = _log
        try:
            import config as _cfg                  # type: ignore
            cfg = _cfg
        except Exception:
            class _Dummy:
                ini_folder = os.path.join(os.getcwd(), "INI")
                window_title = "I Wanna Be The Boshy"
                custom_logo_path = os.path.join(os.getcwd(), "Custom", "boshy_randomizer.png")
            cfg = _Dummy()
    return log, cfg


log, _cfg = _import_deps()

INI_FOLDER = getattr(_cfg, "ini_folder", os.path.join(os.getcwd(), "INI"))
WINDOW_TITLE = getattr(_cfg, "window_title", "I Wanna Be The Boshy")
CUSTOM_LOGO = getattr(
    _cfg,
    "custom_logo_path",
    os.path.join(os.getcwd(), "Custom", "boshy_randomizer.png"),
)
LEGACY_JSON_PATH = getattr(_cfg, "json_path", None)

STATE_JSON = os.path.join(INI_FOLDER, "live_tracker_state.json")

# Farben & Style
BG_COLOR = "#000000"   # Fenster-Hintergrund
CARD_BG = "#000000"    # Innenkarte (Alpha über Fenster)
FG_COLOR = "#FFFFFF"
ACCENT = "#00D1FF"
TEXT_DIM = "#AAAAAA"
LINE_DIM = "#30343A"


# ---------------------------------------------------------------------------

def _find_game_window_rect():
    """Findet das Spiel-Fenster anhand des Titels."""
    try:
        wins = gw.getWindowsWithTitle(WINDOW_TITLE)
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
            canvas.create_oval(
                x1 + dx,
                y1 + dy,
                x1 + dx + 2 * r,
                y1 + dy + 2 * r,
                fill=fill,
                outline="",
            )


# ---- Font-Helfer -----------------------------------------------------------

def _register_private_font(ttf_path: str) -> None:
    """Registriert eine TTF temporär in Windows (für Boshy-Font)."""
    try:
        if not os.path.exists(ttf_path):
            return
        FR_PRIVATE = 0x10
        import ctypes

        AddFontResourceEx = ctypes.windll.gdi32.AddFontResourceExW
        res = AddFontResourceEx(ttf_path, FR_PRIVATE, 0)
        if res > 0:
            HWND_BROADCAST = 0xFFFF
            WM_FONTCHANGE = 0x001D
            ctypes.windll.user32.SendNotifyMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
    except Exception as e:
        log(f"[end_stats] font registration failed: {e}")


def _choose_boshy_font(root: tk.Tk, fallback: str = "Consolas") -> str:
    """Sucht nach 'It's Boshy Time!' Font, ansonsten Fallback."""
    try:
        custom_dir = os.path.dirname(CUSTOM_LOGO)
        ttf_candidate = os.path.join(custom_dir, "fonts", "its-boshy-time.ttf")
        _register_private_font(ttf_candidate)

        fams = set(str(f) for f in tkfont.families(root))
        for name in ("It's Boshy Time!", "Its Boshy Time!", "It’s Boshy Time!", "It s Boshy Time!"):
            if name in fams:
                return name
    except Exception as e:
        log(f"[end_stats] choose_boshy_font failed: {e}")
    return fallback


# ---- JSON-Parsing ----------------------------------------------------------

def _load_stats_from_json():
    """
    Lädt Statistik aus live_tracker_state.json (state_exporter Format).
    Fallback: altes json_path-Format.
    """
    data = {}

    path = STATE_JSON if os.path.exists(STATE_JSON) else None
    if not path and LEGACY_JSON_PATH and os.path.exists(LEGACY_JSON_PATH):
        path = LEGACY_JSON_PATH

    if not path:
        log("[end_stats] no stats JSON found.")
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception as e:
        log(f"[end_stats] failed to read JSON: {e}")
        return {}

    save_sections = {}
    lic_sections = {}

    if "save" in data and isinstance(data.get("save"), dict):
        save_sections = (data.get("save") or {}).get("sections") or {}
        lic_sections = (data.get("license") or {}).get("sections") or {}

        stats = save_sections.get("stats", {}) or save_sections.get("Stats", {}) or {}
        ach = save_sections.get("achievements", {}) or save_sections.get("Achievements", {}) or {}
        col = save_sections.get("collectables", {}) or save_sections.get("Collectables", {}) or {}
        bosses = save_sections.get("bosses", {}) or save_sections.get("Bosses", {}) or {}

        unlocks = {}
        for sec_name, sec_dict in lic_sections.items():
            if sec_name.lower() == "unlockables":
                unlocks = sec_dict or {}
                break
    else:
        save = data.get("savefile", {}) or {}
        stats = save.get("stats", {}) or {}
        ach = save.get("achievements", {}) or {}
        col = save.get("collectables", {}) or {}
        bosses = save.get("bosses", {}) or {}
        unlocks = (data.get("license", {}) or {}).get("unlockables", {}) or {}

        save_sections = save
        lic_sections = data.get("license", {}) or {}

    def _ci(d, key, default="0"):
        if key in d:
            return d[key]
        lk = key.lower()
        for kk, vv in d.items():
            if kk.lower() == lk:
                return vv
        return default

    deaths_raw = str(_ci(stats, "Deaths", "0"))
    try:
        deaths = int(deaths_raw) if deaths_raw.strip().isdigit() else 0
    except Exception:
        deaths = 0

    diff_raw = str(_ci(stats, "Difficulty", "N/A"))
    time_raw = str(_ci(stats, "TimeSeconds", "0"))
    try:
        timesec = int(time_raw) if time_raw.strip().isdigit() else 0
    except Exception:
        timesec = 0

    diff_map = {
        "0": "Ez Mode",
        "1": "Totally Average Mode",
        "2": "Hardon Mode",
        "3": "Youre Gonna Rage Mode",
    }
    difficulty_label = diff_map.get(diff_raw, diff_raw)

    h = timesec // 3600
    m = (timesec % 3600) // 60
    s = timesec % 60
    time_str = f"{h:02d}:{m:02d}:{s:02d}"

    achievements = {k: v for k, v in ach.items() if str(v).strip() not in ("", "0")}
    collectables = {k: v for k, v in col.items() if str(v).strip() not in ("", "0")}
    unlockables = {k: v for k, v in unlocks.items() if str(v).strip() not in ("", "0")}

    worlds_clear = 0
    worlds_pro = 0
    for k, v in achievements.items():
        if str(v).strip() in ("", "0"):
            continue
        kl = k.lower()
        if re.match(r"world\d+clear$", kl):
            worlds_clear += 1
        elif re.match(r"world\d+promode$", kl):
            worlds_pro += 1

    boss_deaths = {
        k: int(v)
        for k, v in bosses.items()
        if str(v).isdigit() and int(v) > 0
    }

    return {
        "summary": {
            "deaths": deaths,
            "difficulty_label": difficulty_label,
            "time_str": time_str,
            "achievements_count": len(achievements),
            "collectables_count": len(collectables),
            "unlockables_count": len(unlockables),
            "worlds_clear": worlds_clear,
            "worlds_pro": worlds_pro,
            "boss_deaths": boss_deaths,
        },
        "save_sections": save_sections,
        "license_sections": lic_sections,
    }


# ---------------------------------------------------------------------------

def show_end_stats(stop_event, route_code: str | None = None):
    """
    Zeigt ein zentriertes Endscreen-Overlay mit Logo & Statistik.
    - 10s Delay nach Solgryn
    - 4 Spalten, linksbündig, Typwriter pro Spalte
    - Scrollbar, wenn zu viel Inhalt
    - Oben rechts: Seed/Route-Code mit Klick-zu-kopieren
    """
    def _run():
        try:
            # 10s Delay nach Solgryn
            delay = 10.0
            t_end_delay = time.time() + delay
            while time.time() < t_end_delay:
                if stop_event.is_set():
                    return
                time.sleep(0.1)

            # Stats aus JSON lesen
            data = _load_stats_from_json()
            if not data:
                log("[end_stats] no stats data, aborting overlay.")
                return

            summary = data["summary"]
            save_sections = data.get("save_sections", {}) or {}
            license_sections = data.get("license_sections", {}) or {}

            # Fenstergröße + Position über dem Spiel
            w, h = 960, 640
            geom = _centered_geometry_over_game(w, h)

            root = tk.Tk()
            root.overrideredirect(True)
            root.attributes("-topmost", True)
            root.attributes("-alpha", 0.0)
            root.configure(bg=BG_COLOR)
            root.geometry(geom)
            root.focus_force()

            boshy_font = _choose_boshy_font(root, fallback="Consolas")
            base_font = ("Consolas", 11)
            big_font = (boshy_font, 15, "bold")
            section_font = (boshy_font, 11, "bold")
            small_dim = ("Consolas", 10, "italic")

            # Container + Canvas + Scrollbar
            container = tk.Frame(root, bg=BG_COLOR)
            container.pack(fill=BOTH, expand=True)

            v_scroll = tk.Scrollbar(container, orient="vertical")
            v_scroll.pack(side="right", fill="y")

            canvas = Canvas(
                container,
                bg=BG_COLOR,
                highlightthickness=0,
                yscrollcommand=v_scroll.set,
            )
            canvas.pack(side="left", fill="both", expand=True)
            v_scroll.config(command=canvas.yview)

            # Mausrad-Scroll
            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

            root.bind_all("<MouseWheel>", _on_mousewheel)

            # Hintergrundkarte
            _draw_rounded_rect(canvas, 12, 12, w - 12, h - 12, 26, fill=CARD_BG)

            pad_top = 26

            # Logo
            logo_y = pad_top + 60
            try:
                if os.path.exists(CUSTOM_LOGO):
                    img = Image.open(CUSTOM_LOGO)
                    img.thumbnail((380, 90))
                    root._logo_img = ImageTk.PhotoImage(img, master=root)
                    canvas.create_image(w // 2, logo_y, image=root._logo_img)
                    pad_top = logo_y + 72  # extra Abstand
                else:
                    pad_top += 72
            except Exception as e:
                log(f"[end_stats] logo load failed: {e}")
                pad_top += 72

            # ----------------- Titel + Seed/Route-Code + Header -----------------
            title_y = pad_top

            # Holder für Canvas-IDs (für visuelles Feedback)
            seed_id_holder = {"id": None}
            copy_status = {"id": None}

            # Statuszeile unten ein/ausblenden
            def _set_copy_status(msg: str, duration_ms: int = 2000):
                # alten Status entfernen
                if copy_status["id"] is not None:
                    try:
                        canvas.delete(copy_status["id"])
                    except Exception:
                        pass
                    copy_status["id"] = None

                if not msg:
                    return

                try:
                    copy_status["id"] = canvas.create_text(
                        w // 2,
                        h - 28,
                        text=msg,
                        fill=TEXT_DIM,
                        font=("Consolas", 10, "italic"),
                    )
                except Exception:
                    return

                def _clear():
                    if copy_status["id"] is not None:
                        try:
                            canvas.delete(copy_status["id"])
                        except Exception:
                            pass
                        copy_status["id"] = None

                root.after(duration_ms, _clear)

            # Helper-Funktion zum Kopieren des Route-Codes
            def _copy_route_code(event=None, code: str | None = None):
                if not code:
                    return
                try:
                    root.clipboard_clear()
                    root.clipboard_append(code)
                    log(f"[end_stats] route code copied to clipboard: {code}")
                    _set_copy_status("Seed copied to clipboard!", 2500)

                    # Seed-Text kurz hervorheben
                    if seed_id_holder["id"] is not None:
                        try:
                            canvas.itemconfigure(seed_id_holder["id"], fill="#FFFFFF")
                        except Exception:
                            pass

                        def _reset_color():
                            try:
                                if seed_id_holder["id"] is not None:
                                    canvas.itemconfigure(
                                        seed_id_holder["id"], fill=TEXT_DIM
                                    )
                            except Exception:
                                pass

                        root.after(800, _reset_color)

                except Exception as e:
                    log(f"[end_stats] clipboard copy failed: {e}")
                    _set_copy_status("Copy failed :(", 2500)

            def draw_title_and_headers():
                # Haupttitel in der Mitte
                canvas.create_text(
                    w // 2,
                    title_y,
                    text="RUN COMPLETE",
                    fill=ACCENT,
                    font=big_font,
                )
                
                # Kleiner Hinweis direkt unter dem Seed
                canvas.create_text(
                    w - 32,
                    title_y + 14,
                    text="(click to copy)",
                    fill=TEXT_DIM,
                    font=("Consolas", 9),
                    anchor="ne",
                )

                # 🔢 Seed/Route-Code rechtsbündig neben dem Titel
                if route_code:
                    seed_label = f"Seed: {route_code}"
                    seed_id_holder["id"] = canvas.create_text(
                        w - 32,              # Abstand vom rechten Rand
                        title_y,             # gleiche Y-Position wie RUN COMPLETE
                        text=seed_label,
                        fill=TEXT_DIM,
                        font=("Consolas", 10, "italic"),
                        anchor="ne",
                        tags=("route_seed",),
                    )

                    # Klick auf den Seed-Text kopiert ihn in die Zwischenablage
                    canvas.tag_bind(
                        "route_seed",
                        "<Button-1>",
                        lambda e, code=route_code: _copy_route_code(e, code),
                    )

                # Linie unter dem Titel
                line_y = title_y + 24
                canvas.create_line(60, line_y, w - 60, line_y, fill=LINE_DIM)

                headers_y = line_y + 18

                inner_left = 70
                inner_right = w - 70
                col_width = (inner_right - inner_left) / 4.0
                col_left = [inner_left + i * col_width for i in range(4)]

                header_texts = ["RUN", "ACHIEVEMENTS", "PROGRESS", "PROFILE"]

                for i in range(4):
                    canvas.create_text(
                        col_left[i],
                        headers_y,
                        text=header_texts[i],
                        fill=ACCENT,
                        font=section_font,
                        anchor="nw",
                    )

                lines_start_y = headers_y + 24
                _start_typewriter(
                    canvas,
                    root,
                    stop_event,
                    col_left,
                    col_width,
                    lines_start_y,
                    base_font,
                    small_dim,
                    section_font,
                    summary,
                    save_sections,
                    license_sections,
                )

            # Erst Inhalt zeichnen …
            draw_title_and_headers()

            # … dann weich einblenden
            def fade_in(step=0, max_alpha=0.88):
                if stop_event.is_set():
                    try:
                        root.destroy()
                    except Exception:
                        pass
                    return
                alpha = max_alpha * (step / 10.0)
                root.attributes("-alpha", alpha)
                if step < 10:
                    root.after(30, fade_in, step + 1, max_alpha)

            fade_in(0)

            # Schließen + end.ini Rücksprung
            def close_event(event=None):
                try:
                    for a in range(88, -1, -12):
                        if stop_event.is_set():
                            break
                        root.attributes("-alpha", a / 100.0)
                        root.update()
                        time.sleep(0.02)
                    root.destroy()

                    try:
                        from PY.save_utils import copy_dest      # type: ignore
                        from PY.reload_sequence import send_reload_sequence  # type: ignore

                        base_dir = os.path.dirname(os.path.abspath(__file__))
                        ini_folder = os.path.join(base_dir, "..", "INI")
                        iwbtb_folder = os.path.join(base_dir, "..", "IWBTB")

                        end_path = os.path.join(ini_folder, "end.ini")
                        dest_path = os.path.join(iwbtb_folder, "SaveFile1.ini")

                        if os.path.exists(end_path) and os.path.exists(dest_path):
                            copy_dest(end_path, dest_path)
                            log("End stats trigger: end.ini -> SaveFile1.ini")
                            send_reload_sequence()
                        else:
                            log("End stats trigger skipped (missing end.ini or SaveFile1.ini)")
                    except Exception as e2:
                        log(f"[end_stats] end.ini trigger error: {e2}")
                except Exception:
                    try:
                        root.destroy()
                    except Exception:
                        pass

            root.bind("<Escape>", close_event)
            root.bind("<Control-s>", close_event)
            root.bind("<F2>", close_event)

            # Mainloop, aber stoppbar über stop_event
            while not stop_event.is_set():
                try:
                    root.update()
                    time.sleep(0.03)
                except tk.TclError:
                    break

            if stop_event.is_set():
                try:
                    root.destroy()
                except Exception:
                    pass

        except Exception as e:
            log(f"Failed to display end_stats overlay: {e}\n{traceback.format_exc()}")

    threading.Thread(target=_run, daemon=True).start()


# ---------------------------------------------------------------------------
# Typewriter-Logik
# ---------------------------------------------------------------------------

def _start_typewriter(canvas: Canvas,
                      root: tk.Tk,
                      stop_event,
                      col_left,
                      col_width,
                      base_y,
                      base_font,
                      small_font,
                      section_font,
                      summary,
                      save_sections,
                      license_sections):
    """
    4 Spalten:
      Col0: OVERVIEW, STATS
      Col1: ACHIEVEMENTS
      Col2: BOSSES, COLLECTABLES, WORLDS
      Col3: CHARACTERS, OTHER
    Rubrik-Header sofort, Einträge mit Typewriter pro Spalte.
    """

    n_cols = len(col_left)
    col_lines: list[list[tuple[str, str]]] = [[] for _ in range(n_cols)]

    def get_section(sections, *names):
        for name in names:
            for sec_name, sec in sections.items():
                if sec_name.lower() == name.lower():
                    return sec or {}
        return {}

    stats_sec = get_section(save_sections, "Stats", "stats")
    ach_sec = get_section(save_sections, "Achievements", "achievements")
    boss_sec = get_section(save_sections, "Bosses", "bosses")
    coll_sec = get_section(save_sections, "Collectables", "collectables")
    unlock_sec = get_section(license_sections, "Unlockables", "unlockables")

    # ------------------- Col 0: OVERVIEW / STATS ------------------------------
    col_lines[0].append(("OVERVIEW", "header"))
    col_lines[0].append(("", "sep"))
    col_lines[0].append((f"Time  {summary['time_str']}", "normal"))
    col_lines[0].append((f"Deaths  {summary['deaths']}", "normal"))
    col_lines[0].append((f"Difficulty  {summary['difficulty_label']}", "normal"))
    col_lines[0].append(("", "normal"))

    col_lines[0].append(("STATS", "header"))
    col_lines[0].append(("", "sep"))
    stats_added = False
    for k, v in stats_sec.items():
        kl = k.lower()
        if kl in ("deaths", "timeseconds", "difficulty"):
            continue
        col_lines[0].append((f"{k}  {v}", "normal"))
        stats_added = True
    if not stats_added:
        col_lines[0].append(("NONE", "normal"))

    # ------------------- Col 1: ACHIEVEMENTS ---------------------------------
    col_lines[1].append(("ACHIEVEMENTS", "header"))
    col_lines[1].append(("", "sep"))
    col_lines[1].append((f"Total  {summary['achievements_count']}", "normal"))
    ach_any = False
    for k, v in sorted(ach_sec.items(), key=lambda kv: kv[0].lower()):
        if str(v).strip() in ("", "0"):
            continue
        col_lines[1].append((f"{k}  {v}", "normal"))
        ach_any = True
    if not ach_any:
        col_lines[1].append(("NONE", "normal"))

    # ------------------- Col 2: BOSSES / COLLECTABLES / WORLDS ---------------
    col_lines[2].append(("BOSSES", "header"))
    col_lines[2].append(("", "sep"))
    boss_any = False
    for k, v in sorted(boss_sec.items(), key=lambda kv: kv[0].lower()):
        if str(v).strip() in ("", "0"):
            continue
        col_lines[2].append((f"{k}  {v}", "normal"))
        boss_any = True
    if not boss_any:
        col_lines[2].append(("NONE", "normal"))
    col_lines[2].append(("", "normal"))

    col_lines[2].append(("COLLECTABLES", "header"))
    col_lines[2].append(("", "sep"))
    col_lines[2].append((f"Total  {summary['collectables_count']}", "normal"))
    coll_any = False
    for k, v in sorted(coll_sec.items(), key=lambda kv: kv[0].lower()):
        if str(v).strip() in ("", "0"):
            continue
        col_lines[2].append((f"{k}  {v}", "normal"))
        coll_any = True
    if not coll_any:
        col_lines[2].append(("NONE", "normal"))
    col_lines[2].append(("", "normal"))

    col_lines[2].append(("WORLDS", "header"))
    col_lines[2].append(("", "sep"))
    if summary["worlds_clear"] == 0 and summary["worlds_pro"] == 0:
        col_lines[2].append(("NONE", "normal"))
    else:
        col_lines[2].append((f"Worlds clear  {summary['worlds_clear']}", "normal"))
        col_lines[2].append((f"Worlds pro  {summary['worlds_pro']}", "normal"))

    # ------------------- Col 3: CHARACTERS / OTHER ---------------------------
    col_lines[3].append(("CHARACTERS", "header"))
    col_lines[3].append(("", "sep"))
    col_lines[3].append((f"Total  {summary['unlockables_count']}", "normal"))
    char_any = False
    for k, v in sorted(unlock_sec.items(), key=lambda kv: kv[0].lower()):
        if str(v).strip() in ("", "0"):
            continue
        col_lines[3].append((f"{k}", "normal"))
        char_any = True
    if not char_any:
        col_lines[3].append(("NONE", "normal"))
    col_lines[3].append(("", "normal"))

    col_lines[3].append(("OTHER", "header"))
    col_lines[3].append(("", "sep"))
    other_any = False

    handled_save_sections = {n.lower() for n in ("Stats", "Achievements", "Bosses", "Collectables")}
    for sec_name, sec in save_sections.items():
        if sec_name.lower() in handled_save_sections:
            continue
        for k, v in sec.items():
            col_lines[3].append((f"{sec_name}  {k}  {v}", "normal"))
            other_any = True

    # License-Sektionen (ohne Unlockables) -> ebenfalls OTHER
    for sec_name, sec in license_sections.items():
        if sec_name.lower() == "unlockables":
            continue
        for k, v in sec.items():
            col_lines[3].append((f"{sec_name}  {k}  {v}", "normal"))
            other_any = True

    if not other_any:
        col_lines[3].append(("NONE", "normal"))

    # ---------- Header sofort zeichnen, Items für Typewriter sammeln ----------
    line_height = 18
    col_items: list[list[tuple[int, int, str]]] = [[] for _ in range(n_cols)]

    max_rows = max(len(c) for c in col_lines) if col_lines else 0

    for col in range(n_cols):
        for row, (text, kind) in enumerate(col_lines[col]):
            x_base = col_left[col]
            y = base_y + row * line_height

            if kind == "header":
                canvas.create_text(
                    x_base,
                    y,
                    text=text,
                    fill=ACCENT,
                    font=section_font,
                    anchor="nw",
                )
            elif kind == "sep":
                y_line = y + line_height * 0.4
                canvas.create_line(
                    x_base,
                    y_line,
                    x_base + col_width - 20,
                    y_line,
                    fill=LINE_DIM,
                )
            else:
                col_items[col].append((x_base + 6, y, text))

    # Scrollregion passend setzen (inkl. Footer)
    total_height = base_y + (max_rows + 6) * line_height
    root.update_idletasks()
    canvas.config(scrollregion=(0, 0, canvas.winfo_width(), total_height))

    # ---------- Typewriter Effekte pro Spalte ---------------------------------
    footer_drawn = {"value": False}
    col_done = [False] * n_cols

    def maybe_draw_footer():
        if footer_drawn["value"]:
            return
        if all(col_done):
            footer_y = base_y + (max_rows + 3) * line_height
            canvas.create_text(
                canvas.winfo_width() // 2,
                footer_y,
                text="Close: Esc  Ctrl+S  F2  (closes automatically when run ends)",
                fill=TEXT_DIM,
                font=small_font,
            )
            footer_drawn["value"] = True

    def type_line(col_idx: int, idx: int):
        if stop_event.is_set():
            return
        items = col_items[col_idx]
        if idx >= len(items):
            col_done[col_idx] = True
            maybe_draw_footer()
            return

        x, y, full_text = items[idx]
        item_id = canvas.create_text(
            x,
            y,
            text="",
            fill=FG_COLOR,
            font=base_font,
            anchor="nw",
        )

        def step(pos=0):
            if stop_event.is_set():
                return
            if pos <= len(full_text):
                canvas.itemconfigure(item_id, text=full_text[:pos])
                root.after(12, step, pos + 1)
            else:
                root.after(40, type_line, col_idx, idx + 1)

        step(0)

    # alle vier Spalten parallel starten
    for col in range(n_cols):
        root.after(400, type_line, col, 0)
