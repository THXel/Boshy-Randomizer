from __future__ import annotations
import os, sys, time, argparse, json, ctypes, traceback, re
import tkinter as tk
from tkinter import ttk
import tkinter.font as tkfont

try:
    from PIL import Image, ImageTk
except Exception:
    Image = ImageTk = None

try:
    from PY.file_utils import smart_read as _smart_read_global
except ModuleNotFoundError:
    try:
        from file_utils import smart_read as _smart_read_global
    except ModuleNotFoundError:
        _smart_read_global = None


def _import_deps():
    log = None
    cfg = None
    rc4_crypt = None
    decrypt_save = None
    try:
        from PY.logger import log as _log
        from PY import config as _cfg
        from PY.rc4_utils import rc4_crypt as _rc, decrypt_save as _dec
        log = _log
        cfg = _cfg
        rc4_crypt = _rc
        decrypt_save = _dec
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
            rc4_crypt = _rc
            decrypt_save = _dec
        except Exception:
            def _rc(key, data): return data
            def _dec(path, key):
                with open(path, "rb") as f:
                    raw = f.read()
                head = raw[:400]
                if b"[" in head and b"=" in head:
                    return raw.decode("latin-1", errors="ignore")
                return raw.decode("latin-1", errors="ignore")
            rc4_crypt = _rc
            decrypt_save = _dec
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
VIRTUAL_JSON = os.path.join(INI, "item_randomizer_virtual.json")

TROPHY_DIR = os.path.join(os.path.dirname(CUSTOM_LOGO), "trophies")
TROPHY_FALLBACK = os.path.join(TROPHY_DIR, "trophy.png")

SHOW_POPUPS_ONLY_RANDOMIZER = True

try:
    GetAsyncKeyState = ctypes.windll.user32.GetAsyncKeyState
except Exception:
    GetAsyncKeyState = None

try:
    from PY.pixel_detector import check_pixel_regions
except ModuleNotFoundError:
    try:
        from pixel_detector import check_pixel_regions
    except ModuleNotFoundError:
        check_pixel_regions = None


def _hotkey_ctrl_f2() -> bool:
    if GetAsyncKeyState is None:
        return False
    VK_CONTROL = 0x11
    VK_F2 = 0x71
    return (GetAsyncKeyState(VK_CONTROL) & 0x8000) and (GetAsyncKeyState(VK_F2) & 0x8000)


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
        if _smart_read_global is not None:
            try:
                text, _ = _smart_read_global(path)
                return text or ""
            except Exception:
                pass
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
                ctypes.windll.user32.SendNotifyMessageW(
                    HWND_BROADCAST, WM_FONTCHANGE, 0, 0
                )
            except Exception:
                pass
            if res > 0:
                with open(BOOT_LOG, "a", encoding="utf-8", errors="ignore") as f:
                    f.write(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [font] registered: {ttf_path}\n"
                    )
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
        root = tk.Tk()
        root.withdraw()
        fams = set(str(x) for x in tkfont.families(root))
        root.destroy()
        for cand in (
            "It's Boshy Time!",
            "Its Boshy Time!",
            "It’s Boshy Time!",
            "It s Boshy Time!",
        ):
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
            winsound.PlaySound(
                quiet_wav, winsound.SND_FILENAME | winsound.SND_ASYNC
            )
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
        self.SIZE_LIST = 10

        default_font = tkfont.nametofont("TkDefaultFont")
        self.body_font_family = default_font.actual("family")

        self.section_nodes: dict[str, str] = {}
        self.section_children: dict[str, dict[str, str]] = {}
        self.section_tree_map: dict[str, str] = {}
        self.targets_node: str | None = None
        self._icon_cache: dict[str, tk.PhotoImage] = {}

        self.notebook: ttk.Notebook | None = None
        self.section_frames: dict[str, tk.Frame] = {}
        self.section_trees: dict[str, ttk.Treeview] = {}

        self.targets_tab_text: str | None = None
        self.targets_tab_frame: tk.Frame | None = None

        self._target_collect_states: dict[str, bool] = {}

        self._build()

        self._timer_running = False
        self._frozen_time = None
        self._start_ts = None
        self._solgryn_done = False
        self._ctrl_f2_held = False

        self._last_stats = {}
        self._last_ach = {}
        self._last_boss: dict[str, int] = {}
        self._last_col = {}
        self._last_char = {}
        self._last_worlds = {}
        self._shown_keys = set()
        self._last_deaths = 0

        self.route_list: list[str] = []
        self.route_index: int = 0
        self.route_total: int = 0

        self._pixel_state: dict = {}
        self._pixel_enabled = bool(check_pixel_regions)

        self.item_randomizer_enabled: bool = False

        self._tick()
        self._poll_files()
        self._poll_pixel_start()

    def _build(self):
        THEME = {
            "bg": "#0E0E10",
            "panel": "#14161A",
            "fg": "#EDEEF0",
            "muted": "#9AA0A6",
            "accent": "#13C3FF",
            "good": "#5EE37A",
            "bad": "#FF6B6B",
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
            bg=self.THEME["bg"],
            fg=self.THEME["accent"],
            font=(self.font_name, self.SIZE_TIMER_MS, "bold"),
        )
        self.timer_lbl_ms.pack(side="left", pady=(17, 0))

        self.deaths_lbl = tk.Label(
            mid,
            text="Deaths: 0",
            bg=self.THEME["bg"],
            fg="#FF6B6B",
            font=(self.font_name, self.SIZE_DEATH, "bold"),
        )
        self.deaths_lbl.pack(anchor="w")

        self.pb_frame = tk.Frame(r, bg=self.THEME["bg"])
        self.pb_frame.pack(fill="x", padx=12, pady=(0, 6))

        self.progress_label = tk.Label(
            self.pb_frame,
            text="",
            bg=self.THEME["bg"],
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
            troughcolor=self.THEME["panel"],
        )

        self.pb = ttk.Progressbar(
            self.pb_frame,
            mode="determinate",
            maximum=100,
            value=0,
            style="Boshy.Horizontal.TProgressbar",
        )
        self.pb.pack(fill="x")

        self._build_tabs()

    def _build_tabs(self):
        outer = tk.Frame(self.root, bg=self.THEME["bg"])
        outer.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        style = ttk.Style()
        style.configure(
            "Boshy.Treeview",
            background=self.THEME["panel"],
            foreground=self.THEME["fg"],
            fieldbackground=self.THEME["panel"],
            rowheight=22,
            font=(self.font_name, self.SIZE_LIST),
        )
        style.map("Boshy.Treeview", background=[("selected", "#1E88E5")])

        style.configure(
            "Vertical.TScrollbar",
            troughcolor=self.THEME["panel"],
            background="#2A2D33",
            arrowcolor=self.THEME["fg"],
            bordercolor=self.THEME["panel"],
        )

        style.configure(
            "TNotebook",
            background=self.THEME["bg"],
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background=self.THEME["panel"],
            foreground=self.THEME["fg"],
            padding=(8, 2),
            font=(self.body_font_family, self.SIZE_LIST),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#1F2229")],
            foreground=[("selected", self.THEME["accent"])],
        )

        style.configure(
            "Target.TNotebook.Tab",
            background="#2A1F16",
            foreground="#FFE082",
            padding=(10, 3),
            font=(self.body_font_family, self.SIZE_LIST + 1, "bold"),
        )
        style.map(
            "Target.TNotebook.Tab",
            background=[("selected", "#3A2814")],
            foreground=[("selected", "#FFE082")],
        )

        nb = ttk.Notebook(outer)
        nb.pack(fill="both", expand=True)
        self.notebook = nb

        sections = [
            ("targets", "🎯 TARGETS"),
            ("achievements", "🏆 Achv."),
            ("bosses", "👑 Boss"),
            ("characters", "🎭 Chars"),
            ("collectables", "💎 Items"),
            ("worlds", "🌍 World"),
        ]

        for sec_key, sec_label in sections:
            frame = tk.Frame(nb, bg=self.THEME["bg"])
            tree = ttk.Treeview(frame, show="tree", style="Boshy.Treeview")
            tree.pack(side="left", fill="both", expand=True)
            sb = ttk.Scrollbar(
                frame,
                orient="vertical",
                command=tree.yview,
                style="Vertical.TScrollbar",
            )
            tree.configure(yscrollcommand=sb.set)
            sb.pack(side="right", fill="y")

            tree.tag_configure(
                "target_section",
                foreground="#FFD75E",
                font=(self.font_name, self.SIZE_LIST),
            )
            tree.tag_configure(
                "target_item",
                foreground="#FFE082",
                font=(self.font_name, self.SIZE_LIST - 1),
            )
            tree.tag_configure(
                "world_item",
                foreground="#A5D6A7",
                font=(self.font_name, self.SIZE_LIST - 1),
            )
            tree.tag_configure(
                "world_header",
                foreground="#A5D6A7",
                font=(self.font_name, self.SIZE_LIST),
            )
            tree.tag_configure(
                "world_detail",
                foreground=self.THEME["muted"],
                font=(self.font_name, self.SIZE_LIST - 1),
            )
            tree.tag_configure(
                "highlight",
                background=self.THEME["accent"],
                foreground=self.THEME["bg"],
            )

            self.section_frames[sec_key] = frame
            self.section_trees[sec_key] = tree
            self.section_tree_map[sec_key] = sec_key
            self.section_children.setdefault(sec_key, {})

            if sec_key == "targets":
                self.targets_tab_frame = frame
                self.targets_tab_text = sec_label
            else:
                nb.add(frame, text=sec_label)

        self._update_targets_tab_visibility(False)

    def _update_targets_tab_visibility(self, visible: bool):
        if not self.notebook or not self.targets_tab_frame:
            return

        nb = self.notebook
        frame = self.targets_tab_frame
        tabs = nb.tabs()

        if visible:
            if str(frame) not in tabs:
                try:
                    nb.insert(0, frame)
                except Exception:
                    nb.add(frame)
                try:
                    nb.tab(
                        frame,
                        text=self.targets_tab_text or "🎯 TARGETS",
                        style="Target.TNotebook.Tab",
                    )
                except Exception:
                    nb.tab(frame, text=self.targets_tab_text or "🎯 TARGETS")
        else:
            if str(frame) in tabs:
                nb.forget(frame)

    def _get_tree_for_section(self, section_name: str):
        key = self.section_tree_map.get(section_name, section_name)
        return self.section_trees.get(key)

    def _focus_section_tab(self, section_name: str):
        if not self.notebook:
            return
        frame = self.section_frames.get(section_name)
        if frame is not None:
            try:
                self.notebook.select(frame)
            except Exception:
                pass

    def _highlight_tree_item(self, section_name: str, item_key: str):
        tree = self._get_tree_for_section(section_name)
        if not tree:
            return
        children = self.section_children.get(section_name, {})
        item_id = children.get(item_key)
        if not item_id:
            return

        base_tags = tree.item(item_id, "tags")
        if isinstance(base_tags, str) or base_tags is None:
            base_tags = (base_tags,) if base_tags else ()
        base_tags = tuple(base_tags)

        try:
            tree.tag_configure(
                "zoom_tmp",
                foreground=self.THEME["accent"],
            )
        except Exception:
            pass

        size_deltas = [0, 1, 2, 3, 2, 1, 0]

        def animate(step=0):
            try:
                if step >= len(size_deltas):
                    tree.item(item_id, tags=base_tags)
                    return

                delta = size_deltas[step]
                size = max(1, self.SIZE_LIST + delta)

                try:
                    tree.tag_configure(
                        "zoom_tmp",
                        font=(self.font_name, size, "bold"),
                    )
                except Exception:
                    pass

                new_tags = tuple(t for t in (*base_tags, "zoom_tmp") if t)
                tree.item(item_id, tags=new_tags)

                self.root.after(70, animate, step + 1)
            except Exception:
                try:
                    tree.item(item_id, tags=base_tags)
                except Exception:
                    pass

        animate(0)

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
                    im.thumbnail((25, 25))
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
                if _hotkey_ctrl_f2():
                    if not self._ctrl_f2_held:
                        self._ctrl_f2_held = True
                        self._timer_running = False
                        self._frozen_time = None
                        self._start_ts = None
                        self._solgryn_done = False
                        reset_now = True
                else:
                    self._ctrl_f2_held = False
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

    def _poll_pixel_start(self):
        try:
            if not self._pixel_enabled:
                return
            region = {
                "Region": "live_tracker_start",
                "center": {"x": 118, "y": 951},
                "relative": True,
                "avg_color": "0xF6FFC1",
                "samples": [],
            }
            triggered, _ = check_pixel_regions([region], self._pixel_state, None)
            if triggered and not self._timer_running and not self._solgryn_done:
                self._timer_running = True
                self._start_ts = time.time()
                self._frozen_time = None
                log("[live] pixel-start detected")
        except Exception as e:
            log(f"[live] pixel poll error: {e}")
        finally:
            self.root.after(50, self._poll_pixel_start)

    def _poll_files(self):
        try:
            state = None
            if os.path.exists(STATE_JSON):
                try:
                    txt = READER.read(STATE_JSON)
                    state = json.loads(txt) if txt.strip() else {}
                except Exception as e:
                    log(f"[live] failed to read {STATE_JSON}: {e}")
                    state = None

            if not state:
                return

            save_sections = (state.get("save") or {}).get("sections") or {}
            lic_sections = (state.get("license") or {}).get("sections") or {}

            item_rand_info = state.get("item_randomizer") or {}
            self.item_randomizer_enabled = bool(item_rand_info.get("enabled"))

            stats = save_sections.get("stats", {}) or {}

            ach_raw = {
                k.strip(): v
                for k, v in (save_sections.get("achievements", {}) or {}).items()
            }
            bos_raw = {
                k.strip(): v
                for k, v in (save_sections.get("bosses", {}) or {}).items()
            }
            col_raw = {
                k.strip(): v
                for k, v in (save_sections.get("collectables", {}) or {}).items()
            }
            chars_raw = {
                k.strip(): v
                for k, v in (lic_sections.get("unlockables", {}) or {}).items()
            }
            exploration_raw = {
                k.strip(): v
                for k, v in (save_sections.get("exploration", {}) or {}).items()
            }

            ach = ach_raw
            bosses = bos_raw
            col = col_raw
            chars = chars_raw
            exploration = exploration_raw

            route_data = state.get("route") or {}
            self.route_list = route_data.get("list", []) or []

            try:
                idx_raw = route_data.get("index", 0)
                self.route_index = int(idx_raw if idx_raw is not None else 0)
            except Exception:
                self.route_index = 0

            total_raw = route_data.get("total", None)
            try:
                if total_raw in (None, "", False):
                    total_int = 0
                else:
                    total_int = int(total_raw)
            except Exception:
                total_int = 0

            if total_int <= 0:
                total_int = len(self.route_list)

            self.route_total = int(total_int)

            self._apply_stats(stats)
            self._apply_section(self._last_ach, ach, "achievements")
            self._apply_worlds_section(exploration)
            self._apply_bosses_section(bosses)
            self._apply_section(self._last_col, col, "collectables")
            self._apply_section(
                self._last_char, chars, "characters", is_characters=True
            )
            self._apply_progress(ach)
            self._apply_targets_section()
        except Exception as e:
            log(f"[live] poll error: {e}\n{traceback.format_exc()}")
        finally:
            self.root.after(200, self._poll_files)

    def _ensure_section_node(self, section_name: str):
        tree = self._get_tree_for_section(section_name)
        if not tree:
            return None
        if section_name not in self.section_nodes:
            self.section_nodes[section_name] = ""
            self.section_children.setdefault(section_name, {})
        return self.section_nodes[section_name]

    def _load_virtual_events(self) -> list[dict]:
        if not os.path.exists(VIRTUAL_JSON):
            return []
        try:
            with open(VIRTUAL_JSON, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            events = data.get("events") or []
            if isinstance(events, list):
                return events
        except Exception:
            pass
        return []

    def _find_virtual_source_for_target(
        self, target_name: str, is_characters: bool
    ) -> str | None:
        events = self._load_virtual_events()
        t_l = target_name.strip().lower()
        wanted_type = "character" if is_characters else "item"
        for ev in reversed(events):
            if not isinstance(ev, dict):
                continue
            tgt = ev.get("target") or {}
            src = ev.get("source") or {}
            tname = str(tgt.get("name", "")).strip()
            ttype = str(tgt.get("type", "")).strip().lower()
            if ttype != wanted_type:
                continue
            if tname.strip().lower() != t_l:
                continue
            sname = str(src.get("name", "")).strip()
            return sname or None
        return None

    def _maybe_popup_for_new_reward(self, section_name: str, item_key: str):
        if SHOW_POPUPS_ONLY_RANDOMIZER and not self.item_randomizer_enabled:
            return

        is_char = section_name == "characters"

        replaced_from = self._find_virtual_source_for_target(
            item_key,
            is_characters=is_char,
        )

        if not replaced_from:
            return

        key_id = f"{section_name}:{item_key.strip().lower()}"
        if key_id in self._shown_keys:
            return
        self._shown_keys.add(key_id)

        self._popup_toast(
            item_key,
            is_characters=is_char,
            replaced_from=replaced_from,
        )
        
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
        if not tree:
            return
        children = self.section_children.setdefault(section_name, {})

        display_items = []

        old_display = set(cache_dict.keys())

        for k, v in sorted(new_map.items(), key=lambda kv: kv[0].lower()):
            key_lower = k.strip().lower()

            if section_name == "achievements" and key_lower == "deathsworldstats":
                continue
            if section_name == "achievements":
                if re.match(r"world\d+(clear|promode)$", key_lower):
                    continue

            value_is_on = str(v).strip() == "1"
            if not value_is_on:
                continue

            display_items.append(k)

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

        new_items = [k for k in display_items if k not in old_display]
        if new_items:
            self._focus_section_tab(section_name)
            for name in new_items:
                self._highlight_tree_item(section_name, name)
                if section_name in ("characters", "collectables"):
                    self._maybe_popup_for_new_reward(section_name, name)

    def _apply_worlds_section(self, exploration: dict):
        parent = self._ensure_section_node("worlds")
        tree = self._get_tree_for_section("worlds")
        if not tree:
            return
        children = self.section_children.setdefault("worlds", {})

        WORLDS: dict[int, tuple[str, str | None]] = {
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

        worlds_data: dict[int, dict[str, bool]] = {}
        for idx, (w_name, b_name) in WORLDS.items():
            w_key = f"W{idx}"
            b_key = f"B{idx}"
            w_val = str(exploration.get(w_key, "")).strip()
            b_val = str(exploration.get(b_key, "")).strip()
            world_done = w_val not in ("", "0")
            boss_done = b_val not in ("", "0")
            if world_done or boss_done:
                worlds_data[idx] = {"world_done": world_done, "boss_done": boss_done}

        if worlds_data == self._last_worlds:
            return

        self._last_worlds = worlds_data

        for _, item_id in list(children.items()):
            try:
                tree.delete(item_id)
            except Exception:
                pass
        children.clear()

        for idx in sorted(WORLDS.keys()):
            if idx not in worlds_data:
                continue

            w_name, b_name = WORLDS[idx]
            state = worlds_data[idx]
            world_done = state.get("world_done", False)
            boss_done = state.get("boss_done", False)

            world_mark = "[x]" if world_done else "[ ]"
            boss_mark = "[x]" if boss_done else "[ ]"

            header_text = f"🌍 {idx}. {w_name}"
            img = self._get_icon_for(w_name)
            parent_key = f"W{idx}"

            header_id = tree.insert(
                parent,
                "end",
                text=header_text,
                image=img,
                tags=("world_header",),
            )
            tree.item(header_id, open=True)
            children[parent_key] = header_id

            detail_world = f"   World   {world_mark}"
            world_id = tree.insert(
                header_id,
                "end",
                text=detail_world,
                tags=("world_detail",),
            )
            children[f"{parent_key}_world"] = world_id

            if b_name:
                detail_boss = f"   {b_name}   {boss_mark}"
            else:
                detail_boss = "   (kein Boss)"
            boss_id = tree.insert(
                header_id,
                "end",
                text=detail_boss,
                tags=("world_detail",),
            )
            children[f"{parent_key}_boss"] = boss_id

    def _apply_bosses_section(self, bosses: dict):
        parent = self._ensure_section_node("bosses")
        tree = self._get_tree_for_section("bosses")
        if not tree:
            return
        children = self.section_children.setdefault("bosses", {})

        new_values: dict[str, int] = {}
        any_increase = False

        for k, v in sorted(bosses.items(), key=lambda kv: kv[0].lower()):
            key_lower = k.strip().lower()
            if not key_lower.endswith("deaths"):
                continue

            raw = str(v).strip()
            if raw == "":
                count = 0
            else:
                try:
                    count = int(raw)
                except Exception:
                    try:
                        count = int(float(raw))
                    except Exception:
                        count = 0

            base_name = re.sub(r"(?i)deaths$", "", k).replace("_", " ").strip()
            if not base_name:
                base_name = k.replace("_", " ").strip()

            if base_name.lower() == "bomberman":
                base_name = "Sonic"

            display_name = f"{base_name} Deaths"

            text = f"👑 {display_name}: {count}"
            img = self._get_icon_for(display_name)

            if k in children:
                try:
                    tree.item(children[k], text=text, image=img)
                except Exception:
                    pass
            else:
                item_id = tree.insert(parent, "end", text=text, image=img)
                children[k] = item_id

            try:
                prev = int(self._last_boss.get(k, 0))
            except Exception:
                prev = 0
            if count > prev:
                any_increase = True
                self._highlight_tree_item("bosses", k)

            new_values[k] = count

        for existing in list(children.keys()):
            if existing not in new_values:
                try:
                    tree.delete(children[existing])
                except Exception:
                    pass
                children.pop(existing, None)

        self._last_boss = dict(new_values)

        if any_increase:
            self._focus_section_tab("bosses")

    def _popup_toast(
        self, name: str, is_characters: bool = False, replaced_from: str | None = None
    ):
        try:
            win = tk.Toplevel(self.root)
            win.overrideredirect(True)
            try:
                win.attributes("-topmost", True)
            except Exception:
                pass

            bg = "#111317"
            accent = "#FFB74D" if is_characters else "#13C3FF"

            win.configure(bg="#000000")
            self.root.update_idletasks()

            game_rect = get_game_window_rect()
            w, h = 420, 160
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

            frame = tk.Frame(
                win,
                bg=bg,
                highlightthickness=1,
                highlightbackground="#333333",
            )
            frame.pack(fill="both", expand=True)

            img_path = os.path.join(TROPHY_DIR, f"{name}.png")
            if not os.path.exists(img_path):
                img = self._get_icon_for(name.replace("_", " "))
                if img is not None:
                    win._toast_img = img
                    tk.Label(
                        frame,
                        image=win._toast_img,
                        bg=bg,
                    ).pack(side="left", padx=10, pady=10)
                else:
                    img_path = TROPHY_FALLBACK

            if os.path.exists(img_path) and (Image and ImageTk):
                im = Image.open(img_path)
                im.thumbnail((120, 120))
                win._toast_img = ImageTk.PhotoImage(im, master=win)
                tk.Label(
                    frame,
                    image=win._toast_img,
                    bg=bg,
                ).pack(side="left", padx=10, pady=10)

            title = "Character randomized!" if is_characters else "Item randomized!"
            tk.Label(
                frame,
                text=title,
                fg="#EDEEF0",
                bg=bg,
                font=(self.font_name, 13, "bold"),
            ).pack(anchor="nw", padx=10, pady=(10, 0))

            display_name = name.replace("_", " ")

            try:
                base_size = 16
                name_font = tkfont.Font(
                    family=self.font_name,
                    size=base_size,
                    weight="bold",
                )
                max_text_width = max(80, w - 180)
                while name_font.measure(display_name) > max_text_width and base_size > 8:
                    base_size -= 1
                    name_font.configure(size=base_size)
                name_font_to_use = name_font
            except Exception:
                name_font_to_use = (self.font_name, 16, "bold")

            tk.Label(
                frame,
                text=display_name,
                fg=accent,
                bg=bg,
                font=name_font_to_use,
            ).pack(anchor="nw", padx=10, pady=(2, 0))

            if replaced_from:
                src = replaced_from.replace("_", " ")
                tk.Label(
                    frame,
                    text=f"{src} → {display_name}",
                    fg="#9AA0A6",
                    bg=bg,
                    font=(self.font_name, 11),
                ).pack(anchor="nw", padx=10, pady=(2, 6))

            play_quiet_success_sound()

            if can_alpha:

                def fade_in(step=0):
                    try:
                        alpha = min(0.95, step / 12.0 * 0.95)
                        win.attributes("-alpha", alpha)
                        if step < 12:
                            win.after(25, fade_in, step + 1)
                        else:
                            win.after(1500, fade_out, 12)
                    except Exception:
                        win.after(1500, win.destroy)

                def fade_out(step):
                    try:
                        alpha = max(0.0, step / 12.0 * 0.95)
                        win.attributes("-alpha", alpha)
                        if step > 0:
                            win.after(25, fade_out, step - 1)
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
        deaths_val = int(
            _get_num(stats, ["Deaths", "deaths"], default=self._last_deaths)
        )

        new_run = False
        if self._last_stats:
            last_t = _get_num(
                self._last_stats, ["TimeSeconds", "timeseconds"], default=0.0
            )
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

            if self.route_total and self.route_total > 0:
                cur = max(0, min(self.route_index, self.route_total))
                pct = int(100 * cur / max(1, self.route_total))
                self.pb["value"] = pct
                display_cur = max(1, cur)
                self.progress_label.config(
                    text=f"Route progress: {display_cur}/{self.route_total}"
                )
                return

            targets = []
            try:
                if os.path.exists(TARGETS_JSON):
                    with open(TARGETS_JSON, "r", encoding="utf-8") as f:
                        tj = json.load(f) or {}
                    if isinstance(tj, dict):
                        targets = tj.get("targets") or []
                    else:
                        targets = tj
                    targets = [str(x).strip().lower() for x in targets if str(x).strip()]
            except Exception:
                targets = []

            if targets:
                total_targets = len(targets)
                collected = 0
                for name in targets:
                    if any(name == k.lower() for k in self._last_ach.keys()):
                        collected += 1
                    elif any(name == k.lower() for k in self._last_col.keys()):
                        collected += 1
                    elif any(name == k.lower() for k in self._last_char.keys()):
                        collected += 1

                self.pb["value"] = int(100 * collected / max(1, total_targets))
                self.progress_label.config(
                    text=f"Targets: {collected}/{total_targets}"
                )
                return

            self.pb["value"] = 0
            self.progress_label.config(text="")

        except Exception:
            try:
                self.pb["value"] = 0
            except Exception:
                pass

    def _apply_targets_section(self):
        if not os.path.exists(TARGETS_JSON):
            self.targets_node = None
            self._update_targets_tab_visibility(False)
            tree = self._get_tree_for_section("targets")
            if tree:
                children = self.section_children.setdefault("targets", {})
                for _, item_id in list(children.items()):
                    try:
                        tree.delete(item_id)
                    except Exception:
                        pass
                children.clear()
            self._target_collect_states.clear()
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

        use_target_mode = bool(targets)
        self._update_targets_tab_visibility(use_target_mode)

        tree = self._get_tree_for_section("targets")
        if not tree:
            return
        children = self.section_children.setdefault("targets", {})

        if not use_target_mode:
            for _, item_id in list(children.items()):
                try:
                    tree.delete(item_id)
                except Exception:
                    pass
            children.clear()
            self._target_collect_states.clear()
            self.targets_node = None
            return

        for key in list(self._target_collect_states.keys()):
            if key not in targets:
                del self._target_collect_states[key]

        parent = self._ensure_section_node("targets")

        old_keys = set(children.keys())
        new_keys = set(targets)

        for k in old_keys - new_keys:
            try:
                tree.delete(children[k])
            except Exception:
                pass
            children.pop(k, None)
            self._target_collect_states.pop(k, None)

        any_new_collect = False

        for name in sorted(targets):
            collected = (
                any(name == k.lower() for k in self._last_ach.keys())
                or any(name == k.lower() for k in self._last_col.keys())
                or any(name == k.lower() for k in self._last_char.keys())
            )
            prev_collected = self._target_collect_states.get(name, False)

            check = "☑️" if collected else "⬜"
            display_name = name.replace("_", " ").title()
            text = f"{check} {display_name}"
            img = self._get_icon_for(display_name)

            if name in children:
                try:
                    tree.item(
                        children[name],
                        text=text,
                        image=img,
                        tags=("target_item",),
                    )
                except Exception:
                    pass
            else:
                item_id = tree.insert(
                    parent,
                    "end",
                    text=text,
                    image=img,
                    tags=("target_item",),
                )
                children[name] = item_id

            self._target_collect_states[name] = collected

            if collected and not prev_collected:
                any_new_collect = True
                play_quiet_success_sound()
                self._highlight_tree_item("targets", name)

        if any_new_collect and use_target_mode:
            self._focus_section_tab("targets")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--watch", default="SaveFile1.ini")
    args = parser.parse_args()

    save_path = os.path.join(IWBTB, args.watch)
    lic_path = os.path.join(IWBTB, "onlineLicense.ini")

    os.makedirs(INI, exist_ok=True)
    with open(BOOT_LOG, "a", encoding="utf-8", errors="ignore") as f:
        f.write(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] === Live Tracker booting ===\n"
        )

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
