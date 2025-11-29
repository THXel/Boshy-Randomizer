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


def _import_deps():
    log = None
    cfg = None
    try:
        from PY.logger import log as _log
        from PY import config as _cfg
        log = _log
        cfg = _cfg
    except Exception:
        try:
            from logger import log as _log
        except Exception:
            def _log(msg: str):
                print(msg, flush=True)

        log = _log
        try:
            import config as _cfg
            cfg = _cfg
        except Exception:
            class _Dummy:
                ini_folder = os.path.join(os.getcwd(), "INI")
                window_title = "I Wanna Be The Boshy"
                custom_logo_path = os.path.join(
                    os.getcwd(),
                    "Custom",
                    "boshy_randomizer.png",
                )

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
WINDOW_TITLE_VARIANTS = getattr(_cfg, "window_title_variants", [])
LEGACY_JSON_PATH = getattr(_cfg, "json_path", None)
STATE_JSON = os.path.join(INI_FOLDER, "live_tracker_state.json")

BG_COLOR = "#000000"
CARD_BG = "#000000"
FG_COLOR = "#FFFFFF"
ACCENT = "#00D1FF"
TEXT_DIM = "#AAAAAA"
LINE_DIM = "#30343A"

TROPHY_DIR = os.path.join(os.path.dirname(CUSTOM_LOGO), "trophies")
TROPHY_FALLBACK = os.path.join(TROPHY_DIR, "trophy.png")


def _find_game_window_rect():
    try:
        candidates = []
        titles = []
        main_title = WINDOW_TITLE or ""
        if main_title:
            titles.append(main_title)
        for t in WINDOW_TITLE_VARIANTS:
            if t and t not in titles:
                titles.append(t)

        for title in titles:
            try:
                wins = gw.getWindowsWithTitle(title)
            except Exception:
                continue
            for w in wins:
                try:
                    if not w.isVisible:
                        continue
                    if w.width <= 100 or w.height <= 100:
                        continue
                    candidates.append(w)
                except Exception:
                    continue

        if not candidates:
            try:
                all_wins = gw.getAllWindows()
            except Exception:
                all_wins = []
            for w in all_wins:
                try:
                    title = (w.title or "").lower()
                    if not title:
                        continue
                    if (WINDOW_TITLE or "").lower() in title:
                        if w.isVisible and w.width > 100 and w.height > 100:
                            candidates.append(w)
                            continue
                    for t in WINDOW_TITLE_VARIANTS:
                        if t and t.lower() in title:
                            if w.isVisible and w.width > 100 and w.height > 100:
                                candidates.append(w)
                                break
                except Exception:
                    continue

        if not candidates:
            return None

        w = max(candidates, key=lambda win: win.width * win.height)
        return (w.left, w.top, w.width, w.height)
    except Exception as e:
        log(f"[end_stats] _find_game_window_rect failed: {e}")
        return None


def _centered_geometry_over_game(w, h):
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


def _register_private_font(ttf_path: str) -> None:
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
            ctypes.windll.user32.SendNotifyMessageW(
                HWND_BROADCAST,
                WM_FONTCHANGE,
                0,
                0,
            )
    except Exception as e:
        log(f"[end_stats] font registration failed: {e}")


def _choose_boshy_font(root: tk.Tk, fallback: str = "Consolas") -> str:
    try:
        custom_dir = os.path.dirname(CUSTOM_LOGO)
        ttf_candidate = os.path.join(custom_dir, "fonts", "its-boshy-time.ttf")
        _register_private_font(ttf_candidate)
        fams = set(str(f) for f in tkfont.families(root))
        for name in (
            "It's Boshy Time!",
            "Its Boshy Time!",
            "It’s Boshy Time!",
            "It s Boshy Time!",
        ):
            if name in fams:
                return name
    except Exception as e:
        log(f"[end_stats] choose_boshy_font failed: {e}")
    return fallback


def _get_icon_for(display_name: str | None, root: tk.Tk, size=(22, 22)):
    if not display_name:
        return None
    display_name = display_name.strip()
    if not display_name:
        return None

    if not hasattr(root, "_icon_cache"):
        root._icon_cache = {}

    cache = root._icon_cache

    candidates = []
    base = display_name
    candidates.append(base)
    candidates.append(base.replace(" ", "_"))
    candidates.append(base.replace("_", " "))
    candidates.append(base.lower())
    candidates.append(base.title())

    paths = []
    for name in candidates:
        paths.append(os.path.join(TROPHY_DIR, f"{name}.png"))
    paths.append(TROPHY_FALLBACK)

    for p in paths:
        if not os.path.exists(p):
            continue
        key = (p, size)
        if key in cache:
            return cache[key]
        try:
            img = Image.open(p)
            img.thumbnail(size)
            tk_img = ImageTk.PhotoImage(img, master=root)
            cache[key] = tk_img
            return tk_img
        except Exception:
            continue
    return None


def _load_stats_from_json():
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

        stats = (
            save_sections.get("stats", {})
            or save_sections.get("Stats", {})
            or {}
        )
        ach = (
            save_sections.get("achievements", {})
            or save_sections.get("Achievements", {})
            or {}
        )
        col = (
            save_sections.get("collectables", {})
            or save_sections.get("Collectables", {})
            or {}
        )
        bosses = (
            save_sections.get("bosses", {})
            or save_sections.get("Bosses", {})
            or {}
        )

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

    achievements = {
        k: v for k, v in ach.items() if str(v).strip() not in ("", "0")
    }
    collectables = {
        k: v for k, v in col.items() if str(v).strip() not in ("", "0")
    }
    unlockables = {
        k: v for k, v in unlocks.items() if str(v).strip() not in ("", "0")
    }

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

    boss_deaths = {}
    for k, v in bosses.items():
        kl = k.lower()
        if not kl.endswith("deaths"):
            continue
        vv = str(v).strip()
        if not vv.isdigit():
            continue
        iv = int(vv)
        if iv <= 0:
            continue
        boss_deaths[k] = iv

    item_rand_info = data.get("item_randomizer") or {}
    item_rand_enabled = bool(item_rand_info.get("enabled"))
    try:
        item_rand_events = int(item_rand_info.get("virtual_events", 0) or 0)
    except Exception:
        item_rand_events = 0

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
            "item_randomizer_enabled": item_rand_enabled,
            "item_randomizer_events": item_rand_events,
        },
        "save_sections": save_sections,
        "license_sections": lic_sections,
    }


def show_end_stats(stop_event, route_code: str | None = None):
    def _run():
        try:
            delay = 10.0
            t_end_delay = time.time() + delay
            while time.time() < t_end_delay:
                if stop_event.is_set():
                    return
                time.sleep(0.1)

            data = _load_stats_from_json()
            if not data:
                log("[end_stats] no stats data, aborting overlay.")
                return

            summary = data["summary"]
            save_sections = data.get("save_sections", {}) or {}
            license_sections = data.get("license_sections", {}) or {}

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
            section_font = (boshy_font, 9)
            small_dim = ("Consolas", 10, "italic")

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

            def _on_mousewheel(event):
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

            root.bind_all("<MouseWheel>", _on_mousewheel)

            _draw_rounded_rect(canvas, 12, 12, w - 12, h - 12, 26, fill=CARD_BG)

            pad_top = 26
            logo_y = pad_top + 60

            try:
                if os.path.exists(CUSTOM_LOGO):
                    img = Image.open(CUSTOM_LOGO)
                    img.thumbnail((380, 90))
                    root._logo_img = ImageTk.PhotoImage(img, master=root)
                    canvas.create_image(w // 2, logo_y, image=root._logo_img)
                    pad_top = logo_y + 72
                else:
                    pad_top += 72
            except Exception as e:
                log(f"[end_stats] logo load failed: {e}")
                pad_top += 72

            title_y = pad_top
            seed_id_holder = {"id": None}
            copy_status = {"id": None}

            def _set_copy_status(msg: str, duration_ms: int = 2000):
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

            def _copy_route_code(event=None, code: str | None = None):
                if not code:
                    return
                try:
                    root.clipboard_clear()
                    root.clipboard_append(code)
                    log(f"[end_stats] route code copied to clipboard: {code}")
                    _set_copy_status("Seed copied to clipboard!", 2500)
                    if seed_id_holder["id"] is not None:
                        try:
                            canvas.itemconfigure(
                                seed_id_holder["id"],
                                fill="#FFFFFF",
                            )
                        except Exception:
                            pass

                        def _reset_color():
                            try:
                                if seed_id_holder["id"] is not None:
                                    canvas.itemconfigure(
                                        seed_id_holder["id"],
                                        fill=TEXT_DIM,
                                    )
                            except Exception:
                                pass

                        root.after(800, _reset_color)
                except Exception as e:
                    log(f"[end_stats] clipboard copy failed: {e}")
                    _set_copy_status("Copy failed :(", 2500)

            def draw_title_and_headers():
                canvas.create_text(
                    w // 2,
                    title_y,
                    text="RUN COMPLETE",
                    fill=ACCENT,
                    font=big_font,
                )
                canvas.create_text(
                    w - 32,
                    title_y + 14,
                    text="(click to copy)",
                    fill=TEXT_DIM,
                    font=("Consolas", 9),
                    anchor="ne",
                )
                if route_code:
                    seed_label = f"Seed: {route_code}"
                    seed_id_holder["id"] = canvas.create_text(
                        w - 32,
                        title_y,
                        text=seed_label,
                        fill=TEXT_DIM,
                        font=("Consolas", 10, "italic"),
                        anchor="ne",
                        tags=("route_seed",),
                    )
                    canvas.tag_bind(
                        "route_seed",
                        "<Button-1>",
                        lambda e, code=route_code: _copy_route_code(e, code),
                    )

                line_y = title_y + 24
                canvas.create_line(60, line_y, w - 60, line_y, fill=LINE_DIM)

                headers_y = line_y + 18
                inner_left = 70
                inner_right = w - 70
                col_width = (inner_right - inner_left) / 3.0
                col_left = [inner_left + i * col_width for i in range(3)]

                header_texts = [
                    "RUN / BOSSES / PROFILE",
                    "ACHIEVEMENTS / ITEMS",
                    "WORLDS",
                ]
                for i in range(len(header_texts)):
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

            draw_title_and_headers()

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
                        from PY.save_utils import copy_dest
                        from PY.reload_sequence import send_reload_sequence

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
                            log(
                                "End stats trigger skipped "
                                "(missing end.ini or SaveFile1.ini)",
                            )
                    except Exception as e2:
                        log(f"[end_stats] end.ini trigger error: {e2}")
                except Exception:
                    try:
                        root.destroy()
                    except Exception:
                        pass

            root.bind("<Escape>", close_event)
            root.bind("<Control-F2>", close_event)
            root.bind("<F2>", close_event)

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
            log(
                f"Failed to display end_stats overlay: {e}\n"
                f"{traceback.format_exc()}",
            )

    threading.Thread(target=_run, daemon=True).start()


def _start_typewriter(
    canvas: Canvas,
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
    license_sections,
):
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
    expl_sec = get_section(save_sections, "Exploration", "exploration")

    time_str = summary.get("time_str", "00:00:00")
    deaths = summary.get("deaths", 0)
    diff_label = summary.get("difficulty_label", "N/A")
    unlock_count = summary.get("unlockables_count", len(unlock_sec))
    item_rand_enabled = bool(summary.get("item_randomizer_enabled", False))
    try:
        item_rand_events = int(summary.get("item_randomizer_events", 0) or 0)
    except Exception:
        item_rand_events = 0

    col_lines[0].append(("RUN SUMMARY", "header"))
    col_lines[0].append(("", "sep"))
    col_lines[0].append((f"Time      {time_str}", "primary"))
    col_lines[0].append((f"Deaths    {deaths}", "primary"))
    col_lines[0].append((f"Difficulty  {diff_label}", "primary"))
    if item_rand_enabled:
        if item_rand_events > 0:
            ir_text = f"Item Rand.  ON ({item_rand_events} rewards)"
        else:
            ir_text = "Item Rand.  ON"
    else:
        ir_text = "Item Rand.  OFF"
    col_lines[0].append((ir_text, "primary"))
    col_lines[0].append(("", "normal"))

    col_lines[0].append(("BOSSES", "header"))
    col_lines[0].append(("", "sep"))

    boss_any = False
    for k, v in sorted(boss_sec.items(), key=lambda kv: kv[0].lower()):
        kl = k.strip().lower()
        if not kl.endswith("deaths"):
            continue
        raw = str(v).strip()
        if not raw or not raw.isdigit():
            continue
        count = int(raw)

        base_name = re.sub(r"(?i)deaths$", "", k).replace("_", " ").strip()
        if not base_name:
            base_name = k.replace("_", " ").strip()

        if base_name.lower() == "bomberman":
            base_name = "Sonic"

        display = f"{base_name} Deaths  {count}"
        col_lines[0].append((display, "normal"))
        boss_any = True
    if not boss_any:
        col_lines[0].append(("NONE", "normal"))

    col_lines[0].append(("", "normal"))
    col_lines[0].append(("PROFILE / CHARACTERS", "header"))
    col_lines[0].append(("", "sep"))
    col_lines[0].append((f"Total  {unlock_count}", "normal"))

    char_any = False
    for k, v in sorted(unlock_sec.items(), key=lambda kv: kv[0].lower()):
        if str(v).strip() in ("", "0"):
            continue
        col_lines[0].append((f"{k}", "normal"))
        char_any = True
    if not char_any:
        col_lines[0].append(("NONE", "normal"))

    ach_count = summary.get("achievements_count", len(ach_sec))
    coll_count = summary.get("collectables_count", len(coll_sec))

    col_lines[1].append(("ACHIEVEMENTS", "header"))
    col_lines[1].append(("", "sep"))
    col_lines[1].append((f"Total  {ach_count}", "normal"))

    ach_any = False
    for k, v in sorted(ach_sec.items(), key=lambda kv: kv[0].lower()):
        if str(v).strip() in ("", "0"):
            continue
        kl = k.strip().lower()
        if kl == "deathsworldstats":
            continue
        if re.match(r"world\d+(clear|promode)$", kl):
            continue
        col_lines[1].append((f"{k}  {v}", "normal"))
        ach_any = True
    if not ach_any:
        col_lines[1].append(("NONE", "normal"))

    col_lines[1].append(("", "normal"))
    col_lines[1].append(("COLLECTABLES", "header"))
    col_lines[1].append(("", "sep"))
    col_lines[1].append((f"Total  {coll_count}", "normal"))

    coll_any = False
    for k, v in sorted(coll_sec.items(), key=lambda kv: kv[0].lower()):
        if str(v).strip() in ("", "0"):
            continue
        col_lines[1].append((f"{k}  {v}", "normal"))
        coll_any = True
    if not coll_any:
        col_lines[1].append(("NONE", "normal"))

    col_lines[2].append(("WORLDS", "header"))
    col_lines[2].append(("", "sep"))

    WORLDS_MAP: dict[int, tuple[str, str | None]] = {
        1: ("Prehistorik 2", "Hello Kitty"),
        2: ("Kirby's Adventure", "Ryu"),
        3: ("Cheetahmen II", "Mario"),
        4: ("VVVVVV", "Biollante"),
        5: ("Wario Land", "Sonic"),
        6: ("Castlevania", "Skeleton King"),
        7: ("Random World", "Mega Man"),
        8: ("Mega Man", "Shang Tsung"),
        9: ("Kid Icarus", "Ganon"),
        10: ("Ninja Gaiden", "Missingno"),
        11: ("Mario Desert", None),
        12: ("Final Path", "Solgryn"),
    }

    worlds_any = False
    for idx in sorted(WORLDS_MAP.keys()):
        w_name, b_name = WORLDS_MAP[idx]
        w_key = f"W{idx}"
        b_key = f"B{idx}"
        w_val = str(expl_sec.get(w_key, "")).strip()
        b_val = str(expl_sec.get(b_key, "")).strip()
        world_done = w_val not in ("", "0")
        boss_done = b_val not in ("", "0")

        if not (world_done or boss_done):
            continue

        worlds_any = True
        world_mark = "[x]" if world_done else "[ ]"
        boss_mark = "[x]" if boss_done else "[ ]"

        col_lines[2].append((f"{idx}. {w_name}", "normal"))
        col_lines[2].append((f"   World   {world_mark}", "normal"))
        if b_name:
            col_lines[2].append((f"   {b_name}   {boss_mark}", "normal"))
        else:
            col_lines[2].append(("   (kein Boss)", "normal"))
        col_lines[2].append(("", "normal"))

    if not worlds_any:
        col_lines[2].append(("NONE", "normal"))

    line_height = 18
    col_items: list[list[tuple[int, int, str, str, tuple]]] = [[] for _ in range(n_cols)]
    max_rows = max(len(c) for c in col_lines) if col_lines else 0

    base_family = base_font[0]
    base_size = base_font[1]

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
                size = base_size + 1 if kind == "primary" else base_size
                font_tuple = (base_family, size)
                try:
                    f_obj = tkfont.Font(family=base_family, size=size)
                    max_width = col_width - 30
                    while f_obj.measure(text) > max_width and size > 8:
                        size -= 1
                        f_obj.configure(size=size)
                    font_tuple = (base_family, size)
                except Exception:
                    pass

                x_text = x_base + 26
                col_items[col].append((x_text, y, text, kind, font_tuple))

    total_height = base_y + (max_rows + 6) * line_height
    root.update_idletasks()
    canvas.config(scrollregion=(0, 0, canvas.winfo_width(), total_height))

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
                text="Close: Esc  Ctrl+F2  F2  (closes automatically when run ends)",
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

        x, y, full_text, kind, font_tuple = items[idx]
        color = ACCENT if kind == "primary" else FG_COLOR

        raw = full_text.lstrip()
        icon_key = None
        parts = raw.split("  ")
        if parts:
            icon_key = parts[0].strip()
        img = _get_icon_for(icon_key, root)
        if img is not None:
            canvas.create_image(
                x - 12,
                y + line_height * 0.55,
                image=img,
                anchor="center",
            )

        item_id = canvas.create_text(
            x,
            y,
            text="",
            fill=color,
            font=font_tuple,
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

    for col in range(n_cols):
        root.after(400, type_line, col, 0)
