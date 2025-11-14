# ======================================================
# Boshy Live Tracker (Tkinter) — 60 FPS + custom font + caching + targets
# Treeview version + in-game popup
# ======================================================
from __future__ import annotations
import os, sys, time, argparse, json, ctypes, traceback
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None

# ---- Dependency bootstrap ----------------------------------------------------
def _import_deps():
    log = None
    cfg = None
    rc4_crypt = None
    decrypt_save = None
    try:
        from PY.logger import log as _log
        from PY import config as _cfg
        from PY.rc4_utils import rc4_crypt as _rc, decrypt_save as _dec
        log = _log; cfg = _cfg; rc4_crypt = _rc; decrypt_save = _dec
    except Exception:
        try:
            from logger import log as _log
        except Exception:
            def _log(msg): print(msg, flush=True)
        log = _log
        try:
            import config as _cfg
            cfg = _cfg
        except Exception:
            class _Dummy:
                ini_folder = os.path.join(os.getcwd(), "INI")
                iwbtb_folder = os.path.join(os.getcwd(), "IWBTB")
                rc4_key = b"Boshy"
                custom_logo_path = os.path.join(os.getcwd(), "Custom", "logo.png")
                target_collect_mode = False
                window_title = "I Wanna Be The Boshy"
                window_title_variants = []
            cfg = _Dummy()
        try:
            from rc4_utils import rc4_crypt as _rc, decrypt_save as _dec
            rc4_crypt = _rc; decrypt_save = _dec
        except Exception:
            def _rc(key, data): return data
            def _dec(path, key):
                with open(path, "rb") as f: raw = f.read()
                head = raw[:400]
                if b"[" in head and b"=" in head:
                    return raw.decode("latin-1", errors="ignore")
                return raw.decode("latin-1", errors="ignore")
            rc4_crypt = _rc; decrypt_save = _dec
    return log, cfg, rc4_crypt, decrypt_save

log, _cfg, rc4_crypt, decrypt_save = _import_deps()
INI = getattr(_cfg, "ini_folder", os.path.join(os.getcwd(), "INI"))
IWBTB = getattr(_cfg, "iwbtb_folder", os.path.join(os.getcwd(), "IWBTB"))
RC4_KEY = getattr(_cfg, "rc4_key", b"Boshy")
CUSTOM_LOGO = getattr(_cfg, "custom_logo_path", os.path.join(os.getcwd(), "Custom", "logo.png"))
BOOT_LOG = os.path.join(INI, "live_tracker_boot.log")

WINDOW_TITLE = getattr(_cfg, "window_title", "I Wanna Be The Boshy")
WINDOW_TITLE_VARIANTS = getattr(_cfg, "window_title_variants", [])

TARGETS_JSON = os.path.join(INI, "target_items.json")

# ---- Smart reader with cooldown ---------------------------------------------
class CachedReader:
    def __init__(self, cooldown: float = 2.0):
        self.cooldown = float(cooldown)
        self._cache: dict[str, tuple[float, str]] = {}

    def read(self, path: str) -> str:
        now = time.time()
        entry = self._cache.get(path)
        if entry and now - entry[0] < self.cooldown:
            return entry[1]
        txt = self._smart_read(path)
        if txt:
            self._cache[path] = (now, txt)
        else:
            if entry:
                return entry[1]
            self._cache[path] = (now, "")
        return self._cache[path][1]

    @staticmethod
    def _smart_read(path: str) -> str:
        try:
            with open(path, "rb") as f:
                raw = f.read()
            if not raw:
                return ""
            head = raw[:400]
            if b"[" in head and b"=" in head:
                return raw.decode("latin-1", errors="ignore")
            try:
                txt = rc4_crypt(RC4_KEY, raw).decode("latin-1", errors="ignore")
                if "[" not in txt[:400] or "=" not in txt[:400]:
                    return decrypt_save(path, RC4_KEY)
                return txt
            except Exception:
                return decrypt_save(path, RC4_KEY)
        except Exception:
            try:
                with open(path, "r", encoding="latin-1", errors="ignore") as f:
                    return f.read()
            except Exception:
                return ""

READER = CachedReader(cooldown=2.0)

# ---- Fonts -------------------------------------------------------------------
def register_private_font(ttf_path: str) -> bool:
    try:
        if os.path.exists(ttf_path):
            FR_PRIVATE = 0x10
            AddFontResourceEx = ctypes.windll.gdi32.AddFontResourceExW
            res = AddFontResourceEx(ttf_path, FR_PRIVATE, 0)
            try:
                HWND_BROADCAST = 0xFFFF
                WM_FONTCHANGE = 0x001D
                ctypes.windll.user32.SendNotifyMessageW(HWND_BROADCAST, WM_FONTCHANGE, 0, 0)
            except Exception:
                pass
            if res > 0:
                with open(BOOT_LOG, "a", encoding="utf-8", errors="ignore") as f:
                    f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [font] registered: {ttf_path}\n")
            return bool(res > 0)
    except Exception:
        pass
    return False

def choose_boshy_font(fallback: str = "Consolas") -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(os.path.dirname(here), "Custom", "fonts", "its-boshy-time.ttf"),
        os.path.join(os.path.dirname(os.getcwd()), "Custom", "fonts", "its-boshy-time.ttf"),
        os.path.join(here, "Custom", "fonts", "its-boshy-time.ttf"),
        os.path.join(INI, "..", "Custom", "fonts", "its-boshy-time.ttf"),
    ]
    for p in candidates:
        register_private_font(os.path.abspath(p))
    try:
        root = tk.Tk(); root.withdraw()
        fams = set(str(x) for x in tkfont.families(root))
        root.destroy()
        for cand in ("It's Boshy Time!", "Its Boshy Time!", "It’s Boshy Time!", "It s Boshy Time!"):
            if cand in fams:
                return cand
    except Exception:
        pass
    return fallback

def fmt_time_hhmmss_ms(seconds: float) -> str:
    if seconds < 0 or seconds != seconds:
        seconds = 0.0
    total_ms = int(round(seconds * 1000.0))
    hh = total_ms // 3_600_000
    rem = total_ms % 3_600_000
    mm = rem // 60_000
    rem = rem % 60_000
    ss = rem // 1_000
    ms = rem % 1_000
    return f"{hh:02d}:{mm:02d}:{ss:02d}.{ms:03d}"

# ---- Items allowlist --------------------------------------------------------
def load_items_allowlist() -> set[str]:
    try:
        p = os.path.join(INI, "items.json")
        with open(p, "r", encoding="utf-8") as f:
            j = json.load(f) or {}
        if isinstance(j, dict) and "items" in j and isinstance(j["items"], dict):
            return {k.strip().lower() for k in j["items"].keys()}
        return {k.strip().lower() for k in j.keys()}
    except Exception:
        return set()

ITEM_ALLOW = load_items_allowlist()

# ---- Game window rect (for popup position) ----------------------------------
def get_game_window_rect():
    try:
        user32 = ctypes.windll.user32

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        titles = []
        main_t = WINDOW_TITLE or ""
        if main_t:
            titles.append(main_t)
        for t in WINDOW_TITLE_VARIANTS:
            if t and t not in titles:
                titles.append(t)

        for title in titles:
            hwnd = user32.FindWindowW(None, title)
            if hwnd:
                rect = RECT()
                if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
                    return rect.left, rect.top, rect.right, rect.bottom
    except Exception:
        pass
    return None

# ---- Sound helper: success_quiet.wav only -----------------------------------
def play_quiet_success_sound():
    try:
        import winsound
        base_dir = os.path.dirname(CUSTOM_LOGO)
        quiet_wav = os.path.join(base_dir, "success_quiet.wav")
        if os.path.exists(quiet_wav):
            winsound.PlaySound(quiet_wav, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass

# ---- LiveTracker UI ---------------------------------------------------------
class LiveTrackerUI:
    def __init__(self, root: tk.Tk, watch_save: str, watch_license: str):
        self.root = root
        self.watch_save = watch_save
        self.watch_license = watch_license

        self.font_name = choose_boshy_font()
        self.SIZE_TITLE = 12
        self.SIZE_TIMER = 21
        self.SIZE_DEATH = 10
        self.SIZE_SUB = 9
        self.SIZE_TINY = 8

        # *** Wichtig: Tree-Tracking VOR _build() initialisieren ***
        self.section_nodes: dict[str, str] = {}
        self.section_children: dict[str, dict[str, str]] = {}
        self.targets_node: str | None = None

        self._build()

        self._timer_running = False
        self._frozen_time = None
        self._start_ts = None
        self._solgryn_done = False

        self._last_stats = {}
        self._last_ach = {}
        self._last_boss = {}
        self._last_col = {}
        self._last_char = {}
        self._shown_keys = set()

        self._tick()
        self._poll_files()

    def _build(self):
        THEME = {
            "bg": "#0E0E10",
            "panel": "#14161A",
            "fg": "#EDEEF0",
            "muted": "#9AA0A6",
            "accent": "#13C3FF",
        }
        self.THEME = THEME

        r = self.root
        r.title("Boshy Live Tracker")
        try:
            r.attributes("-topmost", True)
        except Exception:
            pass

        try:
            sw = r.winfo_screenwidth()
            r.geometry(f"380x640+{sw - 420}+60")
        except Exception:
            r.geometry("380x600+60+60")
        r.configure(bg=THEME["bg"])

        logo_wrap = tk.Frame(r, bg=THEME["bg"])
        logo_wrap.pack(fill="x", padx=8, pady=(8, 2))
        self._safe_logo(logo_wrap, max_w=350, max_h=80)

        top = tk.Frame(r, bg=THEME["bg"])
        top.pack(fill="x", padx=12, pady=(0, 6))
        self.lbl_title = tk.Label(
            top,
            text="Boshy Live",
            bg=THEME["bg"],
            fg=THEME["fg"],
            font=(self.font_name, self.SIZE_TITLE, "bold"),
        )
        self.lbl_title.pack(side="left")

        mid = tk.Frame(r, bg=THEME["bg"])
        mid.pack(fill="x", padx=12, pady=(0, 6))
        self.timer_lbl = tk.Label(
            mid,
            text="00:00:00.000",
            bg=THEME["bg"],
            fg=THEME["accent"],
            font=(self.font_name, self.SIZE_TIMER, "bold"),
        )
        self.timer_lbl.pack(anchor="w")
        self.deaths_lbl = tk.Label(
            mid,
            text="Deaths: 0",
            bg=THEME["bg"],
            fg="#FF6B6B",
            font=(self.font_name, self.SIZE_DEATH, "bold"),
        )
        self.deaths_lbl.pack(anchor="w")

        pb_frame = tk.Frame(r, bg=THEME["bg"])
        pb_frame.pack(fill="x", padx=12, pady=(0, 8))
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure(
            "Boshy.Horizontal.TProgressbar",
            troughcolor=THEME["panel"],
        )
        self.pb = ttk.Progressbar(
            pb_frame,
            mode="determinate",
            maximum=100,
            value=0,
            style="Boshy.Horizontal.TProgressbar",
        )
        self.pb.pack(fill="x")

        self._build_tree()

    def _build_tree(self):
        frame = tk.Frame(self.root, bg=self.THEME["bg"])
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        style = ttk.Style()
        style.configure(
            "Boshy.Treeview",
            background=self.THEME["panel"],
            foreground=self.THEME["fg"],
            fieldbackground=self.THEME["panel"],
            rowheight=20,
        )
        style.map("Boshy.Treeview", background=[("selected", "#1E88E5")])

        tree = ttk.Treeview(frame, show="tree", style="Boshy.Treeview")
        tree.pack(side="left", fill="both", expand=True)
        sb = tk.Scrollbar(frame, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        self.tree = tree

        # Root-Knoten für die Rubriken
        self.section_nodes["achievements"] = self.tree.insert(
            "", "end", text="🏆 Achievements", open=True
        )
        self.section_nodes["bosses"] = self.tree.insert(
            "", "end", text="👑 Bosses", open=True
        )
        self.section_nodes["collectables"] = self.tree.insert(
            "", "end", text="💎 Collectables", open=True
        )
        self.section_nodes["characters"] = self.tree.insert(
            "", "end", text="🎭 Characters", open=True
        )

        self.section_children.setdefault("achievements", {})
        self.section_children.setdefault("bosses", {})
        self.section_children.setdefault("collectables", {})
        self.section_children.setdefault("characters", {})

        self.tree.tag_configure(
            "target_section",
            foreground="#FFD75E",
            font=(self.font_name, self.SIZE_SUB, "bold"),
        )
        self.tree.tag_configure(
            "target_item",
            foreground="#FFE082",
            font=(self.font_name, self.SIZE_TINY, "normal"),
        )

    def _safe_logo(self, parent, max_w=320, max_h=80):
        if not Image or not ImageTk:
            return
        p = CUSTOM_LOGO
        try:
            if os.path.exists(p):
                img = Image.open(p)
                img.thumbnail((max_w, max_h))
                self._logo_img = ImageTk.PhotoImage(img, master=self.root)
                tk.Label(parent, image=self._logo_img, bg=self.THEME["bg"]).pack(
                    anchor="center"
                )
        except Exception:
            with open(BOOT_LOG, "a", encoding="utf-8", errors="ignore") as f:
                f.write("logo load fail\n")

    # ---- Main ticks ----------------------------------------------------------
    def _tick(self):
        try:
            if self._solgryn_done and self._frozen_time is not None:
                cur = self._frozen_time
            elif self._timer_running and self._start_ts is not None:
                cur = max(0.0, time.time() - self._start_ts)
            else:
                cur = 0.0
            self.timer_lbl.config(text=fmt_time_hhmmss_ms(cur))
        except Exception as e:
            log(f"[live] tick error: {e}")
        finally:
            self.root.after(16, self._tick)

    def _poll_files(self):
        try:
            save_txt = READER.read(self.watch_save)
            lic_txt = READER.read(self.watch_license)

            stats, ach, bosses, col = self._parse_save_ini(save_txt)
            chars = self._parse_license_ini(lic_txt)

            self._apply_stats(stats)
            self._apply_section(self._last_ach, ach, "achievements")
            self._apply_section(self._last_boss, bosses, "bosses")
            self._apply_section(self._last_col, col, "collectables")
            self._apply_section(self._last_char, chars, "characters", is_characters=True)

            self._apply_progress(ach)
            self._apply_targets_section()

        except Exception as e:
            log(f"[live] poll error: {e}\n{traceback.format_exc()}")
        finally:
            self.root.after(200, self._poll_files)

    # ---- Parsing -------------------------------------------------------------
    def _parse_save_ini(self, txt: str):
        data = {}
        sec = None
        for line in (txt or "").splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("[") and s.endswith("]"):
                sec = s.strip("[]").lower()
                data.setdefault(sec, {})
                continue
            if "=" in s and sec:
                k, v = [x.strip() for x in s.split("=", 1)]
                data[sec][k] = v
        stats = data.get("stats", {})
        ach_raw = {k.strip().lower(): v for k, v in (data.get("achievements", {}) or {}).items()}
        bos_raw = {k.strip().lower(): v for k, v in (data.get("bosses", {}) or {}).items()}
        col_raw = {k.strip().lower(): v for k, v in (data.get("collectables", {}) or {}).items()}

        if ITEM_ALLOW:
            ach = {k: v for k, v in ach_raw.items() if k in ITEM_ALLOW}
            bos = {k: v for k, v in bos_raw.items() if k in ITEM_ALLOW}
            col = {k: v for k, v in col_raw.items() if k in ITEM_ALLOW}
        else:
            ach, bos, col = ach_raw, bos_raw, col_raw
        return stats, ach, bos, col

    def _parse_license_ini(self, txt: str):
        data = {}
        sec = None
        for line in (txt or "").splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("[") and s.endswith("]"):
                sec = s.strip("[]").lower()
                data.setdefault(sec, {})
                continue
            if "=" in s and sec:
                k, v = [x.strip() for x in s.split("=", 1)]
                data[sec][k] = v
        unlocks = {k.strip().lower(): v for k, v in (data.get("unlockables", {}) or {}).items()}
        if ITEM_ALLOW:
            unlocks = {k: v for k, v in unlocks.items() if k in ITEM_ALLOW}
        return unlocks

    # ---- Tree helpers --------------------------------------------------------
    def _ensure_section_node(self, section_name: str):
        # Wenn der Abschnitt schon existiert, direkt zurückgeben
        if section_name in self.section_nodes:
            return self.section_nodes[section_name]

        # Targets immer ganz nach oben setzen
        if section_name == "targets":
            node = self.tree.insert(
                "",
                0,  # <-- erster Eintrag in der Root-Liste
                text="🎯 Target Items (Mode)",
                open=True,
                tags=("target_section",),
            )
            self.section_nodes[section_name] = node
            self.section_children.setdefault(section_name, {})
            return node

        # Alle anderen Abschnitte wie bisher ans Ende anhängen
        node = self.tree.insert("", "end", text=section_name.title(), open=True)
        self.section_nodes[section_name] = node
        self.section_children.setdefault(section_name, {})
        return node

    def _apply_section(
        self,
        cache_dict: dict,
        new_map: dict,
        section_name: str,
        is_characters: bool = False,
    ):
        # falls INI kurz leer / kaputt ist: alten Stand behalten
        if not new_map and cache_dict:
            return

        parent = self._ensure_section_node(section_name)
        children = self.section_children.setdefault(section_name, {})

        display_items = []
        for k, v in sorted(new_map.items()):
            if str(v).strip() == "1":
                display_items.append(k)
                key_id = f"{section_name}:{k}"
                if key_id not in self._shown_keys:
                    self._shown_keys.add(key_id)
                    self._popup_toast(k, is_characters=is_characters)

        if set(display_items) == set(cache_dict.keys()):
            return

        cache_dict.clear()
        for x in display_items:
            cache_dict[x] = "1"

        old_keys = set(children.keys())
        new_keys = set(display_items)

        for k in old_keys - new_keys:
            try:
                self.tree.delete(children[k])
            except Exception:
                pass
            children.pop(k, None)

        icon = "•"
        if section_name == "achievements":
            icon = "🏆"
        elif section_name == "bosses":
            icon = "👑"
        elif section_name == "collectables":
            icon = "💎"
        elif section_name == "characters":
            icon = "🎭"

        for k in new_keys:
            text = f"{icon} {k.replace('_', ' ')}"
            if k in children:
                try:
                    self.tree.item(children[k], text=text)
                except Exception:
                    pass
            else:
                item_id = self.tree.insert(parent, "end", text=text)
                children[k] = item_id

    # ---- Popup ---------------------------------------------------------------
    def _popup_toast(self, name: str, is_characters: bool = False):
        try:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)
            try:
                win.attributes("-topmost", True)
            except Exception:
                pass
            bg = "#111317"
            win.configure(bg="#000000")

            self.root.update_idletasks()

            game_rect = get_game_window_rect()
            w, h = 420, 140
            if game_rect:
                gx, gy, gr, gb = game_rect
                gw = max(0, gr - gx)
                gh = max(0, gb - gy)
                x = gx + (gw - w) // 2
                y = gy + gh - h - 40
            else:
                rx = self.root.winfo_rootx()
                ry = self.root.winfo_rooty()
                rw = self.root.winfo_width()
                rh = self.root.winfo_height()
                x = rx + rw - w - 10
                y = ry + rh - h - 30
            win.geometry(f"{w}x{h}+{x}+{y}")

            try:
                win.attributes("-alpha", 0.0)
                can_alpha = True
            except Exception:
                can_alpha = False

            frame = tk.Frame(win, bg=bg)
            frame.pack(fill="both", expand=True)

            img_path = os.path.join(os.path.dirname(CUSTOM_LOGO), "trophies", f"{name}.png")
            if Image and ImageTk and os.path.exists(img_path):
                im = Image.open(img_path)
                im.thumbnail((120, 120))
                win._toast_img = ImageTk.PhotoImage(im, master=win)
                tk.Label(frame, image=win._toast_img, bg=bg).pack(
                    side="left", padx=10, pady=10
                )

            title = "Character Unlocked!" if is_characters else "Item Collected!"
            tk.Label(
                frame,
                text=title,
                fg="#EDEEF0",
                bg=bg,
                font=(self.font_name, 13, "bold"),
            ).pack(anchor="nw", padx=10, pady=(10, 0))
            tk.Label(
                frame,
                text=name.replace("_", " "),
                fg="#13C3FF",
                bg=bg,
                font=(self.font_name, 16, "bold"),
            ).pack(anchor="nw", padx=10, pady=(2, 0))

            play_quiet_success_sound()

            if can_alpha:
                def fade_in(step=0):
                    try:
                        alpha = min(0.9, step / 10.0 * 0.9)
                        win.attributes("-alpha", alpha)
                        if step < 10:
                            win.after(20, fade_in, step + 1)
                        else:
                            win.after(1000, fade_out, 10)
                    except Exception:
                        win.after(1000, win.destroy)

                def fade_out(step):
                    try:
                        alpha = max(0.0, step / 10.0 * 0.9)
                        win.attributes("-alpha", alpha)
                        if step > 0:
                            win.after(20, fade_out, step - 1)
                        else:
                            win.destroy()
                    except Exception:
                        win.destroy()

                fade_in(0)
            else:
                win.after(1600, win.destroy)
        except Exception as e:
            log(f"[toast] failed: {e}")

    # ---- Stats / progress ----------------------------------------------------
    def _apply_stats(self, stats: dict):
        try:
            deaths = int(stats.get("Deaths", stats.get("deaths", "0")))
        except Exception:
            deaths = 0
        self.deaths_lbl.config(text=f"Deaths: {deaths}")

        try:
            t = float(stats.get("TimeSeconds", stats.get("timeseconds", "0")))
        except Exception:
            t = 0.0

        if self._solgryn_done:
            if self._frozen_time is None:
                self._frozen_time = max(
                    0.0, t if t > 0 else (time.time() - (self._start_ts or time.time()))
                )
            self._timer_running = False
            return

        if t > 0 and not self._timer_running:
            self._timer_running = True
            self._start_ts = time.time() - t
            log("[live] timer started")
        elif t == 0 and not self._timer_running and self._start_ts is None:
            pass

    def _apply_progress(self, ach: dict):
        try:
            # --- Targets aus JSON lesen (unterstützt beide Formate) ---
            targets = []
            if os.path.exists(TARGETS_JSON):
                with open(TARGETS_JSON, "r", encoding="utf-8") as f:
                    tj = json.load(f) or {}

                raw_list = []
                if isinstance(tj, dict):
                    raw_list = tj.get("targets") or []
                elif isinstance(tj, list):
                    raw_list = tj
                targets = [str(x).strip().lower() for x in raw_list if str(x).strip()]

            # Target-Mode ist aktiv, sobald eine Targets-Liste existiert
            use_target_mode = bool(targets)

            if use_target_mode:
                # gesammelt wird über alle Caches geprüft (Achievments, Collectables, Characters)
                got = 0
                for name in targets:
                    if (
                        name in self._last_ach
                        or name in self._last_col
                        or name in self._last_char
                    ):
                        got += 1
                total = len(targets)
                self.pb["value"] = int(100 * got / total) if total else 0
                return

            # normaler Modus: nur Achievements zählen
            total = max(1, len(ach))
            got = sum(1 for v in ach.values() if str(v).strip() == "1")
            self.pb["value"] = int(100 * got / total)
        except Exception:
            self.pb["value"] = 0

    def _apply_targets_section(self):
        # JSON existiert nicht → Abschnitt entfernen
        if not os.path.exists(TARGETS_JSON):
            if "targets" in self.section_nodes:
                node = self.section_nodes.pop("targets")
                try:
                    self.tree.delete(node)
                except Exception:
                    pass
            self.targets_node = None
            return

        # --- Targets aus JSON lesen (beide Formate unterstützt) ---
        try:
            with open(TARGETS_JSON, "r", encoding="utf-8") as f:
                tj = json.load(f) or {}

            raw_list = []
            if isinstance(tj, dict):
                raw_list = tj.get("targets") or []
            elif isinstance(tj, list):
                raw_list = tj
            targets = [str(x).strip().lower() for x in raw_list if str(x).strip()]
        except Exception:
            targets = []

        # keine Targets → Abschnitt ausblenden
        if not targets:
            if "targets" in self.section_nodes:
                node = self.section_nodes.pop("targets")
                try:
                    self.tree.delete(node)
                except Exception:
                    pass
            self.targets_node = None
            return

        parent = self._ensure_section_node("targets")
        self.targets_node = parent
        children = self.section_children.setdefault("targets", {})

        old_keys = set(children.keys())
        new_keys = set(targets)

        # veraltete Einträge entfernen
        for k in old_keys - new_keys:
            try:
                self.tree.delete(children[k])
            except Exception:
                pass
            children.pop(k, None)

        # neue / aktualisierte Einträge
        for name in new_keys:
            collected = (
                name in self._last_ach
                or name in self._last_col
                or name in self._last_char
            )
            box = "[✓]" if collected else "[ ]"
            text = f"{box} {name.replace('_', ' ')}"

            if name in children:
                try:
                    self.tree.item(children[name], text=text, tags=("target_item",))
                except Exception:
                    pass
            else:
                item_id = self.tree.insert(
                    parent, "end", text=text, tags=("target_item",)
                )
                children[name] = item_id


# ---- CLI --------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", default="SaveFile1.ini")
    args = parser.parse_args()

    save_path = os.path.join(IWBTB, args.watch)
    lic_path = os.path.join(IWBTB, "onlineLicense.ini")
    os.makedirs(INI, exist_ok=True)

    with open(BOOT_LOG, "a", encoding="utf-8", errors="ignore") as f:
        f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] === Live Tracker booting ===\n")

    try:
        root = tk.Tk()
    except Exception as e:
        with open(BOOT_LOG, "a", encoding="utf-8", errors="ignore") as f:
            f.write(f"Tk init failed: {e}\n")
        raise

    ui = LiveTrackerUI(root, save_path, lic_path)
    root.mainloop()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open(BOOT_LOG, "a", encoding="utf-8", errors="ignore") as f:
            f.write(f"Fatal error: {e}\n{traceback.format_exc()}\n")
        raise
