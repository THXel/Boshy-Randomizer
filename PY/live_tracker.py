from __future__ import annotations
import os, sys, time, argparse, json, ctypes, traceback, re
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont
try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None
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
STATE_JSON = os.path.join(INI, "live_tracker_state.json")
TROPHY_DIR = os.path.join(os.path.dirname(CUSTOM_LOGO), "trophies")
TROPHY_FALLBACK = os.path.join(TROPHY_DIR, "trophy.png")
try:
    GetAsyncKeyState = ctypes.windll.user32.GetAsyncKeyState
except Exception:
    GetAsyncKeyState = None
def _hotkey_ctrl_r() -> bool:
    if GetAsyncKeyState is None:
        return False
    VK_CONTROL = 0x11
    VK_R = 0x52
    return (GetAsyncKeyState(VK_CONTROL) & 0x8000) and (GetAsyncKeyState(VK_R) & 0x8000)
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
READER = CachedReader(cooldown=0.5)
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
def load_items_allowlist() -> set[str]:
    return set()
ITEM_ALLOW = load_items_allowlist()
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
def play_quiet_success_sound():
    try:
        import winsound
        base_dir = os.path.dirname(CUSTOM_LOGO)
        quiet_wav = os.path.join(base_dir, "success_quiet.wav")
        if os.path.exists(quiet_wav):
            winsound.PlaySound(quiet_wav, winsound.SND_FILENAME | winsound.SND_ASYNC)
    except Exception:
        pass
class LiveTrackerUI:
    def __init__(self, root: tk.Tk, watch_save: str, watch_license: str):
        self.root = root
        self.watch_save = watch_save
        self.watch_license = watch_license
        self.font_name = choose_boshy_font()
        self.SIZE_TITLE = 12
        self.SIZE_TIMER = 21
        self.SIZE_TIMER_MS = 12
        self.SIZE_DEATH = 10
        self.SIZE_SUB = 9
        self.SIZE_TINY = 8
        default_font = tkfont.nametofont("TkDefaultFont")
        self.body_font_family = default_font.actual("family")
        self.section_nodes: dict[str, str] = {}
        self.section_children: dict[str, dict[str, str]] = {}
        self.section_tree_map: dict[str, str] = {}
        self.targets_node: str | None = None
        self._icon_cache: dict[str, tk.PhotoImage] = {}
        self._build()
        self._timer_running = False
        self._frozen_time = None
        self._start_ts = None
        self._solgryn_done = False
        self._ctrl_r_held = False
        self._last_stats = {}
        self._last_ach = {}
        self._last_boss = {}
        self._last_col = {}
        self._last_char = {}
        self._last_worlds = {}
        self._shown_keys = set()
        self._last_deaths = 0
        self._last_deaths = 0
        self.route_list: list[str] = []
        self.route_index: int = 0
        self.route_total: int = 0
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
            r.geometry(f"450x520+{sw - 500}+80")
        except Exception:
            r.geometry("440x520+60+60")
        r.configure(bg=THEME["bg"])
        logo_wrap = tk.Frame(r, bg=THEME["bg"])
        logo_wrap.pack(fill="x", padx=8, pady=(8, 2))
        self._safe_logo(logo_wrap, max_w=420, max_h=70)
        top = tk.Frame(r, bg=THEME["bg"])
        top.pack(fill="x", padx=12, pady=(0, 4))
        self.lbl_title = tk.Label(
            top,
            text="Boshy Live Tracker",
            bg=THEME["bg"],
            fg=THEME["fg"],
            font=(self.font_name, self.SIZE_TITLE, "bold"),
        )
        self.lbl_title.pack(side="left")
        mid = tk.Frame(r, bg=THEME["bg"])
        mid.pack(fill="x", padx=12, pady=(0, 4))
        timer_row = tk.Frame(mid, bg=THEME["bg"])
        timer_row.pack(anchor="w")
        self.timer_lbl_main = tk.Label(
            timer_row,
            text="00:00:00",
            bg=THEME["bg"],
            fg=self.THEME["accent"],
            font=(self.font_name, self.SIZE_TIMER, "bold"),
        )
        self.timer_lbl_main.pack(side="left")
        self.timer_lbl_ms = tk.Label(
            timer_row,
            text=".000",
            bg=THEME["bg"],
            fg=self.THEME["accent"],
            font=(self.font_name, self.SIZE_TIMER_MS, "bold"),
        )
        self.timer_lbl_ms.pack(side="left", pady=(17, 0))
        self.deaths_lbl = tk.Label(
            mid,
            text="Deaths: 0",
            bg=THEME["bg"],
            fg="#FF6B6B",
            font=(self.font_name, self.SIZE_DEATH, "bold"),
        )
        self.deaths_lbl.pack(anchor="w")
        self.pb_frame = tk.Frame(r, bg=THEME["bg"])
        self.pb_frame.pack(fill="x", padx=12, pady=(0, 6))
        self.progress_label = tk.Label(
            self.pb_frame,
            text="",
            bg=THEME["bg"],
            fg=self.THEME["muted"],
            font=(self.font_name, self.SIZE_SUB),
        )
        self.progress_label.pack(anchor="w", pady=(0, 1))
        style = ttk.Style()
        try:
            style.theme_use("alt")
        except Exception:
            pass
        style.configure(
            "Boshy.Horizontal.TProgressbar",
            troughcolor=THEME["panel"],
        )
        self.pb = ttk.Progressbar(
            self.pb_frame,
            mode="determinate",
            maximum=100,
            value=0,
            style="Boshy.Horizontal.TProgressbar",
        )
        self.pb.pack(fill="x")
        self.target_center_frame = tk.Frame(self.pb_frame, bg=THEME["panel"])
        self.target_center_list = tk.Listbox(
            self.target_center_frame,
            bg=THEME["panel"],
            fg=THEME["fg"],
            selectbackground=self.THEME["accent"],
            selectforeground=self.THEME["bg"],
            activestyle="none",
            highlightthickness=1,
            highlightbackground=self.THEME["accent"],
            borderwidth=0,
        )
        self.target_center_list.pack(fill="x", expand=False, padx=4, pady=2)
        self.target_center_frame.pack_forget()
        self._build_tree_2col()
    def _build_tree_2col(self):
        outer = tk.Frame(self.root, bg=self.THEME["bg"])
        outer.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        style = ttk.Style()
        style.configure(
            "Boshy.Treeview",
            background=self.THEME["panel"],
            foreground=self.THEME["fg"],
            fieldbackground=self.THEME["panel"],
            rowheight=20,
            font=(self.body_font_family, self.SIZE_SUB),
        )
        style.map("Boshy.Treeview", background=[("selected", "#1E88E5")])
        style.configure(
            "Vertical.TScrollbar",
            troughcolor=self.THEME["panel"],
            background="#2A2D33",
            arrowcolor=self.THEME["fg"],
            bordercolor=self.THEME["panel"],
        )
        columns_pane = tk.PanedWindow(
            outer,
            orient="horizontal",
            sashrelief="raised",
            bg=self.THEME["bg"],
            bd=0,
            sashwidth=6,
        )
        columns_pane.pack(fill="both", expand=True)
        left_frame = tk.Frame(columns_pane, bg=self.THEME["bg"])
        right_frame = tk.Frame(columns_pane, bg=self.THEME["bg"])
        columns_pane.add(left_frame, stretch="always")
        columns_pane.add(right_frame, stretch="always")
        self.tree_left = ttk.Treeview(left_frame, show="tree", style="Boshy.Treeview")
        self.tree_left.pack(side="left", fill="both", expand=True)
        sb_left = ttk.Scrollbar(
            left_frame,
            orient="vertical",
            command=self.tree_left.yview,
            style="Vertical.TScrollbar",
        )
        self.tree_left.configure(yscrollcommand=sb_left.set)
        sb_left.pack(side="right", fill="y")
        self.tree_right = ttk.Treeview(right_frame, show="tree", style="Boshy.Treeview")
        self.tree_right.pack(side="left", fill="both", expand=True)
        sb_right = ttk.Scrollbar(
            right_frame,
            orient="vertical",
            command=self.tree_right.yview,
            style="Vertical.TScrollbar",
        )
        self.tree_right.configure(yscrollcommand=sb_right.set)
        sb_right.pack(side="right", fill="y")
        for t in (self.tree_left, self.tree_right):
            t.tag_configure(
                "target_section",
                foreground="#FFD75E",
                font=(self.body_font_family, self.SIZE_SUB, "bold"),
            )
            t.tag_configure(
                "target_item",
                foreground="#FFE082",
                font=(self.body_font_family, self.SIZE_TINY, "normal"),
            )
            t.tag_configure(
                "world_item",
                foreground="#A5D6A7",
                font=(self.body_font_family, self.SIZE_TINY, "bold"),
            )
        self.section_tree_map = {
            "achievements": "left",
            "bosses": "left",
            "targets": "left",
            "worlds": "right",
            "collectables": "right",
            "characters": "right",
        }
        self.section_nodes["achievements"] = self.tree_left.insert(
            "", "end", text="🏆 Achievements", open=True
        )
        self.section_nodes["bosses"] = self.tree_left.insert(
            "", "end", text="👑 Bosses", open=True
        )
        self.section_nodes["characters"] = self.tree_right.insert(
            "", "end", text="🎭 Characters", open=True
        )
        self.section_nodes["collectables"] = self.tree_right.insert(
            "", "end", text="💎 Collectables", open=True
        )
        self.section_nodes["worlds"] = self.tree_right.insert(
            "", "end", text="🌍 Worlds", open=True
        )
        self.section_children.setdefault("achievements", {})
        self.section_children.setdefault("worlds", {})
        self.section_children.setdefault("bosses", {})
        self.section_children.setdefault("collectables", {})
        self.section_children.setdefault("characters", {})
        self.section_children.setdefault("targets", {})
    def _get_tree_for_section(self, section_name: str):
        side = self.section_tree_map.get(section_name, "left")
        return self.tree_left if side == "left" else self.tree_right
    def _safe_logo(self, parent, max_w=420, max_h=70):
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
    def _get_icon_for(self, display_name: str) -> tk.PhotoImage | None:
        if not display_name:
            display_name = "trophy"
        candidates = []
        base = display_name.strip()
        if base:
            candidates.append(base)
            candidates.append(base.replace("_", " "))
            candidates.append(base.replace("_", " ").title())
            candidates.append(base.replace(" ", ""))
            candidates.append(base.replace(" ", "").title())
        paths = []
        for name in candidates:
            paths.append(os.path.join(TROPHY_DIR, f"{name}.png"))
        paths.append(TROPHY_FALLBACK)
        for p in paths:
            if not os.path.exists(p):
                continue
            if p in self._icon_cache:
                return self._icon_cache[p]
            try:
                if Image and ImageTk:
                    im = Image.open(p)
                    im.thumbnail((18, 18))
                    img = ImageTk.PhotoImage(im, master=self.root)
                else:
                    img = tk.PhotoImage(file=p, master=self.root)
                self._icon_cache[p] = img
                return img
            except Exception:
                continue
        return None
    def _tick(self):
        try:
            reset_now = False
            try:
                if _hotkey_ctrl_r():
                    if not self._ctrl_r_held:
                        self._ctrl_r_held = True
                        self._timer_running = False
                        self._frozen_time = None
                        self._start_ts = None
                        self._solgryn_done = False
                        reset_now = True
                else:
                    self._ctrl_r_held = False
            except Exception:
                pass
            if reset_now:
                cur = 0.0
            elif self._solgryn_done and self._frozen_time is not None:
                cur = self._frozen_time
            elif self._timer_running and self._start_ts is not None:
                cur = max(0.0, time.time() - self._start_ts)
            else:
                cur = 0.0
            s = fmt_time_hhmmss_ms(cur)
            if "." in s:
                main, ms = s.split(".")
                self.timer_lbl_main.config(text=main)
                self.timer_lbl_ms.config(text="." + ms)
            else:
                self.timer_lbl_main.config(text=s)
                self.timer_lbl_ms.config(text="")
        except Exception as e:
            log(f"[live] tick error: {e}")
        finally:
            self.root.after(16, self._tick)
    def _poll_files(self):
        try:
            state = None
            if os.path.exists(STATE_JSON):
                try:
                    with open(STATE_JSON, "r", encoding="utf-8") as f:
                        state = json.load(f) or {}
                except Exception as e:
                    log(f"[live] failed to read {STATE_JSON}: {e}")
            if state:
                save_sections = (state.get("save") or {}).get("sections") or {}
                lic_sections = (state.get("license") or {}).get("sections") or {}
                stats = save_sections.get("stats", {}) or {}
                ach_raw = {k.strip(): v for k, v in (save_sections.get("achievements", {}) or {}).items()}
                bos_raw = {k.strip(): v for k, v in (save_sections.get("bosses", {}) or {}).items()}
                col_raw = {k.strip(): v for k, v in (save_sections.get("collectables", {}) or {}).items()}
                chars_raw = {k.strip(): v for k, v in (lic_sections.get("unlockables", {}) or {}).items()}
                ach = ach_raw
                bosses = bos_raw
                col = col_raw
                chars = chars_raw
                route_data = state.get("route") or {}
                self.route_list = route_data.get("list", []) or []
                self.route_index = int(route_data.get("index", 0) or 0)
                self.route_total = int(route_data.get("total", len(self.route_list)) or 0)
            else:
                save_txt = READER.read(self.watch_save)
                lic_txt = READER.read(self.watch_license)
                stats, ach, bosses, col = self._parse_save_ini(save_txt)
                chars = self._parse_license_ini(lic_txt)
                self.route_list = []
                self.route_index = 0
                self.route_total = 0
            self._apply_stats(stats)
            self._apply_section(self._last_ach, ach, "achievements")
            self._apply_worlds_section(ach)
            self._apply_section(self._last_boss, bosses, "bosses")
            self._apply_section(self._last_col, col, "collectables")
            self._apply_section(self._last_char, chars, "characters", is_characters=True)
            self._apply_progress(ach)
            self._apply_targets_section()
        except Exception as e:
            log(f"[live] poll error: {e}\n{traceback.format_exc()}")
        finally:
            self.root.after(200, self._poll_files)
    def _parse_save_ini(self, txt: str):
        data = {}
        sec = None
        for line in (txt or "").splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("[") and s.endswith("]"):
                sec = s.strip("[]")
                data.setdefault(sec, {})
                continue
            if "=" in s and sec:
                k, v = [x.strip() for x in s.split("=", 1)]
                data[sec][k] = v
        stats = data.get("Stats", data.get("stats", {}))
        ach_raw = {k.strip(): v for k, v in (data.get("Achievements", data.get("achievements", {})) or {}).items()}
        bos_raw = {k.strip(): v for k, v in (data.get("Bosses", data.get("bosses", {})) or {}).items()}
        col_raw = {k.strip(): v for k, v in (data.get("Collectables", data.get("collectables", {})) or {}).items()}
        return stats or {}, ach_raw, bos_raw, col_raw
    def _parse_license_ini(self, txt: str):
        data = {}
        sec = None
        for line in (txt or "").splitlines():
            s = line.strip()
            if not s:
                continue
            if s.startswith("[") and s.endswith("]"):
                sec = s.strip("[]")
                data.setdefault(sec, {})
                continue
            if "=" in s and sec:
                k, v = [x.strip() for x in s.split("=", 1)]
                data[sec][k] = v
        unlocks = {k.strip(): v for k, v in (data.get("Unlockables", data.get("unlockables", {})) or {}).items()}
        return unlocks
    def _ensure_section_node(self, section_name: str):
        if section_name in self.section_nodes:
            return self.section_nodes[section_name]
        if section_name == "targets":
            tree = self._get_tree_for_section("targets")
            node = tree.insert(
                "",
                0,
                text="🎯 Target Items (Mode)",
                open=True,
                tags=("target_section",),
            )
            self.section_nodes[section_name] = node
            self.section_children.setdefault(section_name, {})
            return node
        tree = self._get_tree_for_section(section_name)
        node = tree.insert("", "end", text=section_name.title(), open=True)
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
        if not new_map and cache_dict:
            return
        parent = self._ensure_section_node(section_name)
        tree = self._get_tree_for_section(section_name)
        children = self.section_children.setdefault(section_name, {})
        display_items = []
        for k, v in sorted(new_map.items(), key=lambda kv: kv[0].lower()):
            key_lower = k.strip().lower()
            if section_name == "achievements" and key_lower == "deathsworldstats":
                continue
            if section_name == "achievements":
                if re.match(r"world\d+(clear|promode)$", key_lower):
                    continue
            if str(v).strip() == "1":
                display_items.append(k)
                if section_name in ("characters", "collectables"):
                    key_id = f"{section_name}:{key_lower}"
                    if key_id not in self._shown_keys:
                        self._shown_keys.add(key_id)
                        self._popup_toast(k, is_characters=(section_name == "characters"))
        if set(display_items) == set(cache_dict.keys()):
            return
        cache_dict.clear()
        for x in display_items:
            cache_dict[x] = "1"
        old_keys = set(children.keys())
        new_keys = set(display_items)
        for k in old_keys - new_keys:
            try:
                tree.delete(children[k])
            except Exception:
                pass
            children.pop(k, None)
        icon_emoji = "•"
        if section_name == "achievements":
            icon_emoji = "🏆"
        elif section_name == "bosses":
            icon_emoji = "👑"
        elif section_name == "collectables":
            icon_emoji = "💎"
        elif section_name == "characters":
            icon_emoji = "🎭"
        elif section_name == "worlds":
            icon_emoji = "🌍"
        for k in new_keys:
            display_name = k.replace("_", " ")
            text = f"{icon_emoji} {display_name}"
            img = self._get_icon_for(display_name)
            if k in children:
                try:
                    tree.item(children[k], text=text, image=img)
                except Exception:
                    pass
            else:
                item_id = tree.insert(parent, "end", text=text, image=img)
                children[k] = item_id
    def _apply_worlds_section(self, ach: dict):
        parent = self._ensure_section_node("worlds")
        tree = self._get_tree_for_section("worlds")
        children = self.section_children.setdefault("worlds", {})
        worlds_data: dict[int, dict[str, bool]] = {}
        for k, v in ach.items():
            key_lower = k.strip().lower()
            m = re.match(r"world(\d+)(clear|promode)$", key_lower)
            if not m:
                continue
            idx = int(m.group(1))
            kind = m.group(2)
            val = str(v).strip()
            is_on = val not in ("", "0")
            worlds_data.setdefault(idx, {})
            worlds_data[idx][kind] = is_on
        if not worlds_data and not self._last_worlds:
            return
        if worlds_data == self._last_worlds:
            return
        self._last_worlds = worlds_data
        for _, item_id in list(children.items()):
            try:
                tree.delete(item_id)
            except Exception:
                pass
        children.clear()
        for idx in sorted(worlds_data.keys()):
            info = worlds_data[idx]
            clear_on = info.get("clear", False)
            pro_on = info.get("promode", False)
            s_clear = "✓" if clear_on else "·"
            s_pro = "✓" if pro_on else "·"
            display_name = f"World {idx}"
            text = f"🌍 {display_name}:  Clear {s_clear}   PRO {s_pro}"
            img = self._get_icon_for(display_name)
            item_id = tree.insert(
                parent,
                "end",
                text=text,
                image=img,
                tags=("world_item",),
            )
            children[idx] = item_id
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
            img_path = os.path.join(TROPHY_DIR, f"{name}.png")
            if not os.path.exists(img_path):
                img = self._get_icon_for(name.replace("_", " "))
                if img is not None:
                    win._toast_img = img
                else:
                    img_path = TROPHY_FALLBACK
            if os.path.exists(img_path) and (Image and ImageTk):
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
    def _apply_stats(self, stats: dict):
        if not isinstance(stats, dict):
            stats = {}
        if not stats and self._last_stats:
            stats = self._last_stats
        def _get_num(d: dict, keys, default=0.0):
            for k in keys:
                if k in d:
                    try:
                        return float(d[k])
                    except Exception:
                        pass
            return float(default)
        t = _get_num(stats, ["TimeSeconds", "timeseconds"], default=0.0)
        deaths_val = int(_get_num(stats, ["Deaths", "deaths"], default=self._last_deaths))
        new_run = False
        if self._last_stats:
            last_t = _get_num(self._last_stats, ["TimeSeconds", "timeseconds"], default=0.0)
            if (
                self._last_deaths > 0
                and deaths_val == 0
                and t < 2.0
                and last_t > 5.0
            ):
                new_run = True
        if new_run:
            self._last_deaths = 0
            deaths_val = 0
        else:
            if deaths_val < self._last_deaths:
                deaths_val = self._last_deaths
        self._last_deaths = deaths_val
        self._last_stats = dict(stats)
        self.deaths_lbl.config(text=f"Deaths: {deaths_val}")
        if self._solgryn_done:
            if self._frozen_time is None:
                self._frozen_time = max(
                    0.0,
                    t if t > 0 else (time.time() - (self._start_ts or time.time())),
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
            sol_val = None
            for k, v in ach.items():
                if k.strip().lower() == "solgryn":
                    sol_val = v
                    break
            if sol_val is not None and str(sol_val).strip() not in ("", "0"):
                if not self._solgryn_done:
                    self._solgryn_done = True
                    if self._frozen_time is None:
                        if self._start_ts is not None:
                            self._frozen_time = max(0.0, time.time() - self._start_ts)
                        else:
                            self._frozen_time = 0.0
                    log("[live] Solgryn achievement detected – timer will freeze")
            targets: list[str] = []
            try:
                if os.path.exists(TARGETS_JSON):
                    with open(TARGETS_JSON, "r", encoding="utf-8") as f:
                        tj = json.load(f) or {}
                    raw_list = []
                    if isinstance(tj, dict):
                        raw_list = tj.get("targets") or []
                    elif isinstance(tj, list):
                        raw_list = tj
                    targets = [
                        str(x).strip().lower()
                        for x in raw_list
                        if str(x).strip()
                    ]
            except Exception:
                targets = []
            use_target_mode = bool(targets)
            if use_target_mode:
                try:
                    if self.pb.winfo_ismapped():
                        self.pb.pack_forget()
                except Exception:
                    pass
                try:
                    if self.target_center_frame is not None:
                        if not self.target_center_frame.winfo_ismapped():
                            self.target_center_frame.pack(fill="x")
                        self._update_target_center_list(targets)
                except Exception:
                    pass
                return
            else:
                try:
                    if (
                        self.target_center_frame is not None
                        and self.target_center_frame.winfo_ismapped()
                    ):
                        self.target_center_frame.pack_forget()
                except Exception:
                    pass
                try:
                    if not self.pb.winfo_ismapped():
                        self.pb.pack(fill="x")
                except Exception:
                    pass
            if self.route_total and self.route_total > 0:
                cur = max(0, min(self.route_index, self.route_total))
                pct = int(100 * cur / self.route_total)
                self.pb["value"] = pct
                try:
                    self.progress_label.config(text=f"Step {cur}/{self.route_total}")
                except Exception:
                    pass
                return
            total = max(1, len(ach))
            got = sum(1 for v in ach.values() if str(v).strip() == "1")
            self.pb["value"] = int(100 * got / total)
        except Exception:
            try:
                self.pb["value"] = 0
            except Exception:
                pass
    def _update_target_center_list(self, targets: list[str]):
        if not self.target_center_frame or not self.target_center_list:
            return
        self.target_center_list.delete(0, tk.END)
        n = max(1, min(len(targets), 10))
        self.target_center_list.config(height=n)
        for name in targets:
            collected = (
                any(name == k.lower() for k in self._last_ach.keys())
                or any(name == k.lower() for k in self._last_col.keys())
                or any(name == k.lower() for k in self._last_char.keys())
            )
            box = "[✓]" if collected else "[ ]"
            display_name = name.replace("_", " ")
            text = f"{box} {display_name}"
            self.target_center_list.insert(tk.END, text)
    def _apply_targets_section(self):
        if not os.path.exists(TARGETS_JSON):
            if "targets" in self.section_nodes:
                tree = self._get_tree_for_section("targets")
                node = self.section_nodes.pop("targets")
                try:
                    tree.delete(node)
                except Exception:
                    pass
            self.targets_node = None
            return
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
        if not targets:
            if "targets" in self.section_nodes:
                tree = self._get_tree_for_section("targets")
                node = self.section_nodes.pop("targets")
                try:
                    tree.delete(node)
                except Exception:
                    pass
            self.targets_node = None
            return
        use_target_mode = bool(targets)
        if use_target_mode:
            if "targets" in self.section_nodes:
                tree = self._get_tree_for_section("targets")
                node = self.section_nodes.pop("targets")
                try:
                    tree.delete(node)
                except Exception:
                    pass
            self.targets_node = None
            return
        parent = self._ensure_section_node("targets")
        tree = self._get_tree_for_section("targets")
        children = self.section_children.setdefault("targets", {})
        old_keys = set(children.keys())
        new_keys = set(targets)
        for k in old_keys - new_keys:
            try:
                tree.delete(children[k])
            except Exception:
                pass
            children.pop(k, None)
        for name in new_keys:
            collected = (
                any(name == k.lower() for k in self._last_ach.keys())
                or any(name == k.lower() for k in self._last_col.keys())
                or any(name == k.lower() for k in self._last_char.keys())
            )
            box = "[✓]" if collected else "[ ]"
            display_name = name.replace("_", " ")
            text = f"{box} {display_name}"
            img = self._get_icon_for(display_name)
            if name in children:
                try:
                    tree.item(children[name], text=text, image=img, tags=("target_item",))
                except Exception:
                    pass
            else:
                item_id = tree.insert(
                    parent, "end", text=text, image=img, tags=("target_item",)
                )
                children[name] = item_id
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
