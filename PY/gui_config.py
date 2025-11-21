import os
import json
import platform
import ctypes
import random
import re
import tkinter.messagebox as messagebox
from typing import Dict, Tuple
import customtkinter as ctk
from PIL import Image
from .config import (
    positions_json,
    custom_logo_path,
    save_enc, rc4_key,
)
from .rc4_utils import decrypt_save, encrypt_save
DEFAULT_DISABLED_BOSSES = {
    "boss5.ini":  "Gastly",
    "boss7.ini":  "Gravitron",
    "boss10.ini": "Gradius",
    "boss14.ini": "Kid Icarus (Flame)",
    "boss15.ini": "Bomberman",
    "boss16.ini": "Ryu Hayabusa",
    "boss19.ini": "Questionmark",
    "boss20.ini": "Ridley",
    "boss21.ini": "Cheetahman",
    "boss23.ini": "Old Sonic",
}
DEFAULT_DISABLED_ROOMS = {
    "save5.ini":  "VVVVV (2nd Half)",
    "save9.ini":  "Pokémon World",
    "save14.ini": "Mario World",
    "save20.ini": "Tower",
    "save21.ini": "World of Warcraft",
}
DEFAULT_ENABLED_BOSSES = {"boss19.ini", "boss20.ini", "boss23.ini"}
class RouteConfig:
    def __init__(self):
        self.rooms_to_play = 7
        self.bosses_to_play = 7
        self.only_rooms = False
        self.only_bosses = False
        self.item_randomizer_enabled = True
        self.target_collect_mode = False
        self.target_item_count = 5
        self.difficulty = "Average"
        self.difficulty_code = 1
        self.random_start_character = False
        self.random_character_per_stage = False
        self.cancelled = False
        self.disabled_bosses = set(DEFAULT_DISABLED_BOSSES.keys())
        self.disabled_rooms = set(DEFAULT_DISABLED_ROOMS.keys())
        self.route_seed = None
def _set_stats_difficulty_in_plaintext(plain_text: str, code: int) -> str:
    lines = plain_text.splitlines(keepends=False)
    out = []
    in_stats = False
    saw_difficulty = False
    for ln in lines:
        s = ln.strip()
        if s.startswith("[") and s.endswith("]"):
            if in_stats and not saw_difficulty:
                out.append(f"Difficulty={code}")
            in_stats = (s.strip("[]").lower() == "stats")
            saw_difficulty = False
            out.append(ln)
            continue
        if in_stats and "=" in s:
            k, _ = s.split("=", 1)
            if k.strip().lower() == "difficulty":
                out.append(f"Difficulty={code}")
                saw_difficulty = True
                continue
        out.append(ln)
    if in_stats and not saw_difficulty:
        out.append(f"Difficulty={code}")
    return "\n".join(out) + ("\n" if plain_text.endswith("\n") else "")
def _difficulty_code_from_label(label: str) -> int:
    l = (label or "").strip().lower()
    if l == "ez":
        return 0
    if l == "rage":
        return 3
    return 1
def write_selected_difficulty_to_encrypted_save(difficulty_label: str) -> None:
    try:
        plain = decrypt_save(save_enc, rc4_key)
    except Exception:
        return
    code = _difficulty_code_from_label(difficulty_label)
    new_plain = _set_stats_difficulty_in_plaintext(plain, code)
    encrypt_save(new_plain, save_enc, rc4_key)
def _load_counts() -> Tuple[int, int]:
    total_rooms, total_bosses = 0, 0
    if os.path.exists(positions_json):
        try:
            with open(positions_json, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            total_rooms = len((data.get("rooms") or data.get("Rooms") or {}))
            total_bosses = len((data.get("bosses") or data.get("Bosses") or {}))
        except Exception:
            pass
    return total_rooms, total_bosses
def _load_max_items() -> int:
    try:
        ini_dir = os.path.dirname(os.path.dirname(positions_json))
        path = os.path.join(ini_dir, "items.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                js = json.load(f) or {}
            return max(1, len(js.keys()))
    except Exception:
        pass
    return 20
def _try_set_icon(root):
    if platform.system().lower() != "windows":
        return
    try:
        base_dir = os.path.dirname(os.path.dirname(__file__))
        icon_path = os.path.join(base_dir, "Custom", "rando_icon.ico")
        if not os.path.exists(icon_path):
            return
        try:
            root.iconbitmap(default=icon_path)
        except Exception:
            pass
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("BoshyRandomizer.App")
        except Exception:
            pass
        try:
            root.update_idletasks()
            hwnd = root.winfo_id()
            WM_SETICON = 0x0080
            ICON_BIG, ICON_SMALL = 1, 0
            LoadImage = ctypes.windll.user32.LoadImageW
            SendMessage = ctypes.windll.user32.SendMessageW
            LR_LOADFROMFILE = 0x0010
            IMAGE_ICON = 1
            big = LoadImage(0, icon_path, IMAGE_ICON, 32, 32, LR_LOADFROMFILE)
            small = LoadImage(0, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE)
            if big:
                SendMessage(hwnd, WM_SETICON, ICON_BIG, big)
            if small:
                SendMessage(hwnd, WM_SETICON, ICON_SMALL, small)
        except Exception:
            pass
    except Exception:
        pass
def build_gui_config():
    cfg = RouteConfig()
    total_rooms, total_bosses = _load_counts()
    max_items = _load_max_items()
    ctk.set_appearance_mode("Dark")
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    root.title("Boshy Randomizer – v1.0")
    root.geometry("1000x760")
    root.resizable(False, False)
    _try_set_icon(root)
    top = ctk.CTkFrame(root, fg_color="transparent")
    top.pack(side="top", fill="x", padx=16, pady=12)
    top_left = ctk.CTkFrame(top, fg_color="transparent")
    top_left.pack(side="left", fill="x", expand=True)
    top_right = ctk.CTkFrame(top, fg_color="transparent")
    top_right.pack(side="right")
    if os.path.exists(custom_logo_path):
        try:
            img = Image.open(custom_logo_path)
            h = 64
            w = int(img.width * (h / img.height))
            img = img.resize((w, h))
            logo = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
            ctk.CTkLabel(top_left, image=logo, text="").pack(side="left", padx=(0, 12))
        except Exception:
            ctk.CTkLabel(top_left, text="Boshy Randomizer", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
    else:
        ctk.CTkLabel(top_left, text="Boshy Randomizer", font=ctk.CTkFont(size=20, weight="bold")).pack(side="left")
    start_btn = ctk.CTkButton(top_right, text="🚀 Create Route & Launch Game",
                              width=280, height=44, font=ctk.CTkFont(size=14, weight="bold"))
    start_btn.pack(side="right")
    tabs = ctk.CTkTabview(root, width=960, height=640)
    tabs.pack(fill="both", expand=True, padx=16, pady=(0, 16))
    tab_general = tabs.add("General Settings")
    tab_optional = tabs.add("Optional Content")
    left_col = ctk.CTkFrame(tab_general, corner_radius=12)
    left_col.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=8)
    right_col = ctk.CTkFrame(tab_general, corner_radius=12)
    right_col.pack(side="right", fill="both", expand=True, padx=(8, 0), pady=8)
    sec_stage = ctk.CTkFrame(left_col, corner_radius=12)
    sec_stage.pack(fill="x", padx=12, pady=(12, 8))
    ctk.CTkLabel(sec_stage, text="Stage Selection", font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=12, pady=10)
    bosses_var = ctk.IntVar(value=max(0, min(cfg.bosses_to_play, total_bosses)))
    boss_block = ctk.CTkFrame(sec_stage, corner_radius=10)
    boss_block.pack(fill="x", padx=12, pady=6)
    ctk.CTkLabel(boss_block, text=f"Number of Bosses (available: {total_bosses})",
                 font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(10, 2))
    boss_val_lbl = ctk.CTkLabel(boss_block, text=f"Selected: {bosses_var.get()} / {total_bosses}", font=ctk.CTkFont(size=12))
    boss_val_lbl.pack(anchor="w", padx=10, pady=(0, 6))
    boss_slider = ctk.CTkSlider(
        boss_block, from_=0, to=max(1, total_bosses),
        number_of_steps=max(1, max(1, total_bosses)-1),
        command=lambda v: boss_val_lbl.configure(text=f"Selected: {int(round(v))} / {total_bosses}")
    )
    boss_slider.set(bosses_var.get())
    boss_slider.pack(fill="x", padx=10, pady=(0, 12))
    rooms_var = ctk.IntVar(value=max(0, min(cfg.rooms_to_play, total_rooms)))
    level_block = ctk.CTkFrame(sec_stage, corner_radius=10)
    level_block.pack(fill="x", padx=12, pady=6)
    ctk.CTkLabel(level_block, text=f"Number of Levels (available: {total_rooms})",
                 font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(10, 2))
    level_val_lbl = ctk.CTkLabel(level_block, text=f"Selected: {rooms_var.get()} / {total_rooms}", font=ctk.CTkFont(size=12))
    level_val_lbl.pack(anchor="w", padx=10, pady=(0, 6))
    level_slider = ctk.CTkSlider(
        level_block, from_=0, to=max(1, total_rooms),
        number_of_steps=max(1, max(1, total_rooms)-1),
        command=lambda v: level_val_lbl.configure(text=f"Selected: {int(round(v))} / {total_rooms}")
    )
    level_slider.set(rooms_var.get())
    level_slider.pack(fill="x", padx=10, pady=(0, 12))
    only_bosses_var = ctk.BooleanVar(value=False)
    only_rooms_var = ctk.BooleanVar(value=False)
    toggle_block = ctk.CTkFrame(sec_stage, corner_radius=10)
    toggle_block.pack(fill="x", padx=12, pady=(0, 10))
    only_bosses_chk = ctk.CTkCheckBox(toggle_block, text="⚔️ Only Bosses", variable=only_bosses_var)
    only_rooms_chk  = ctk.CTkCheckBox(toggle_block, text="🧱 Only Levels", variable=only_rooms_var)
    only_bosses_chk.pack(side="left", padx=(10, 6), pady=10)
    only_rooms_chk.pack(side="left", padx=(6, 10),  pady=10)
    sec_target = ctk.CTkFrame(left_col, corner_radius=12)
    sec_target.pack(fill="x", padx=12, pady=(8, 8))
    ctk.CTkLabel(sec_target, text="★ Target Collect Mode ★",
                 font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=12, pady=(12, 4))
    ctk.CTkLabel(
        sec_target,
        text="Play endlessly until all target items or characters are collected.\n"
             "Once completed, Solgryn will appear as the final boss.",
        font=ctk.CTkFont(size=12), text_color="gray70"
    ).pack(anchor="w", padx=12, pady=(0, 8))
    target_var = ctk.BooleanVar(value=False)
    target_switch = ctk.CTkSwitch(sec_target, text="Enable Target Collect Mode", variable=target_var)
    target_switch.pack(anchor="w", padx=12, pady=(0, 10))
    target_frame = ctk.CTkFrame(sec_target, corner_radius=10)
    target_title = ctk.CTkLabel(target_frame, text="Target Item Count",
                                font=ctk.CTkFont(size=13, weight="bold"))
    target_title.pack(anchor="w", padx=12, pady=(10, 2))
    target_val_label = ctk.CTkLabel(target_frame, text="", font=ctk.CTkFont(size=12))
    target_val_label.pack(anchor="w", padx=12, pady=(0, 6))
    target_slider = ctk.CTkSlider(
        target_frame,
        from_=1, to=max_items,
        number_of_steps=max(1, max_items - 1),
        command=lambda v: target_val_label.configure(
            text=f"Selected: {int(round(v))} / {max_items}"
        ),
    )
    target_slider.set(max(1, min(cfg.target_item_count, max_items)))
    target_val_label.configure(
        text=f"Selected: {int(round(target_slider.get()))} / {max_items}"
    )
    target_slider.pack(fill="x", padx=12, pady=(0, 12))
    target_hint_box = ctk.CTkFrame(sec_target, corner_radius=10)
    target_hint_label = ctk.CTkLabel(
        target_hint_box,
        text="🎯 Endless Mode active — Play until all target items are collected!",
        font=ctk.CTkFont(size=12, weight="bold"),
    )
    def apply_target_rules():
        on = target_var.get()
        if on:
            sec_stage.pack_forget()
            if not target_frame.winfo_ismapped():
                target_frame.pack(fill="x", padx=12, pady=(0, 12))
            if not target_hint_box.winfo_ismapped():
                target_hint_box.pack(fill="x", padx=12, pady=(0, 10))
                target_hint_label.pack(anchor="w", padx=12, pady=10)
            target_slider.configure(state="normal")
            target_val_label.configure(text_color="white")
            _force_levels_checked_and_disabled(True)
            _force_bosses_gastly_cheetah(True)
        else:
            try:
                target_frame.pack_forget()
                target_hint_box.pack_forget()
            except Exception:
                pass
            if not sec_stage.winfo_ismapped():
                sec_stage.pack(before=sec_target, fill="x", padx=12, pady=(12, 8))
            target_slider.configure(state="disabled")
            target_val_label.configure(text_color="gray50")
            _force_levels_checked_and_disabled(False)
            _force_bosses_gastly_cheetah(False)
            apply_only_rules()
        root.after(50, lambda: root.update_idletasks())
    target_switch.configure(command=apply_target_rules)
    sec_diff = ctk.CTkFrame(right_col, corner_radius=12)
    sec_diff.pack(fill="x", padx=12, pady=(12, 8))
    ctk.CTkLabel(
        sec_diff,
        text="Difficulty",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(anchor="w", padx=12, pady=10)
    diff_var = ctk.StringVar(value="Average")
    diff_menu = ctk.CTkOptionMenu(
        sec_diff,
        variable=diff_var,
        values=["Ez", "Average", "Rage"],
        width=160
    )
    diff_menu.pack(anchor="w", padx=12, pady=(0, 12))
    sec_item = ctk.CTkFrame(right_col, corner_radius=12)
    sec_item.pack(fill="x", padx=12, pady=(12, 8))
    ctk.CTkLabel(sec_item, text="Item Randomizer", font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=12, pady=10)
    item_var = ctk.StringVar(value="No")
    item_yes = ctk.CTkRadioButton(sec_item, text="Yes", variable=item_var, value="Yes")
    item_no  = ctk.CTkRadioButton(sec_item, text="No",  variable=item_var, value="No")
    item_yes.pack(side="left", padx=(12, 6), pady=(0, 12))
    item_no.pack(side="left",  padx=(6, 12),  pady=(0, 12))
    sec_char = ctk.CTkFrame(right_col, corner_radius=12)
    sec_char.pack(fill="x", padx=12, pady=(8, 12))
    ctk.CTkLabel(
        sec_char,
        text="Random Character",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(anchor="w", padx=12, pady=(10, 0))
    ctk.CTkLabel(
        sec_char,
        text="ℹ️ While Random Character is active,\n"
             "the in-game Character Menu (F3) is disabled.",
        font=ctk.CTkFont(size=12),
        text_color="gray70",
        justify="left"
    ).pack(anchor="w", padx=12, pady=(2, 10))
    random_char_var = ctk.BooleanVar(value=False)
    random_char_switch = ctk.CTkSwitch(
        sec_char,
        text="Start with Random Character",
        variable=random_char_var
    )
    random_char_switch.pack(anchor="w", padx=12, pady=(0, 8))
    random_char_stage_var = ctk.BooleanVar(value=False)
    random_char_stage = ctk.CTkCheckBox(
        sec_char,
        text="🔁 Change Character after each Boss/Level",
        variable=random_char_stage_var,
        state="disabled"
    )
    random_char_stage.pack(anchor="w", padx=12, pady=(0, 8))
    ctk.CTkLabel(
        sec_char,
        text="Default: Dark Boshy",
        font=ctk.CTkFont(size=12),
        text_color="gray70"
    ).pack(anchor="w", padx=12, pady=(0, 10))
    def on_random_char_toggle():
        if random_char_var.get():
            random_char_stage.configure(state="normal")
        else:
            random_char_stage_var.set(False)
            random_char_stage.configure(state="disabled")
    def on_random_char_stage_toggle():
        if not random_char_var.get() and random_char_stage_var.get():
            random_char_stage_var.set(False)
            random_char_stage.configure(state="disabled")
    random_char_switch.configure(command=on_random_char_toggle)
    random_char_stage.configure(command=on_random_char_stage_toggle)
    on_random_char_toggle()
    optional_wrap = ctk.CTkFrame(tab_optional, corner_radius=12)
    optional_wrap.pack(fill="both", expand=True, padx=12, pady=12)
    opt_header = ctk.CTkLabel(
        optional_wrap,
        text="Optional content recommendations",
        font=ctk.CTkFont(size=16, weight="bold")
    )
    opt_header.pack(anchor="w", padx=12, pady=(12, 6))
    sec_seed = ctk.CTkFrame(optional_wrap, corner_radius=12)
    sec_seed.pack(fill="x", padx=12, pady=(4, 8))
    ctk.CTkLabel(
        sec_seed,
        text="Route Seed (optional)",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(anchor="w", padx=12, pady=(8, 2))
    ctk.CTkLabel(
        sec_seed,
        text=(
            "Enter either a pure number (e.g. 898677) or a full code like\n"
            "R3-B3-T0-C1-P0-898677. Leave empty for a random seed."
        ),
        font=ctk.CTkFont(size=11),
        text_color="gray70",
        justify="left"
    ).pack(anchor="w", padx=12, pady=(0, 4))
    seed_var = ctk.StringVar(value="")
    seed_entry = ctk.CTkEntry(sec_seed, textvariable=seed_var, width=250)
    seed_entry.pack(anchor="w", padx=12, pady=(0, 8))
    opt_hint = ctk.CTkLabel(
        optional_wrap,
        text="(Checked = included in the generated random route)",
        font=ctk.CTkFont(size=12),
        text_color="gray70"
    )
    opt_hint.pack(anchor="w", padx=12, pady=(0, 10))
    opt_scroll = ctk.CTkScrollableFrame(optional_wrap, corner_radius=12, height=440)
    opt_scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))
    opt_cols = ctk.CTkFrame(opt_scroll, fg_color="transparent")
    opt_cols.pack(fill="x", padx=6, pady=6)
    opt_left  = ctk.CTkFrame(opt_cols, corner_radius=12)
    opt_right = ctk.CTkFrame(opt_cols, corner_radius=12)
    opt_left.pack(side="left", fill="both", expand=True, padx=(0, 6))
    opt_right.pack(side="left", fill="both", expand=True, padx=(6, 0))
    ctk.CTkLabel(
        opt_left,
        text="Bosses",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(anchor="w", padx=10, pady=(10, 6))
    ctk.CTkLabel(
        opt_right,
        text="Levels",
        font=ctk.CTkFont(size=14, weight="bold")
    ).pack(anchor="w", padx=10, pady=(10, 6))
    boss_vars: Dict[str, ctk.BooleanVar] = {}
    boss_checks: Dict[str, ctk.CTkCheckBox] = {}
    room_vars: Dict[str, ctk.BooleanVar] = {}
    room_checks: Dict[str, ctk.CTkCheckBox] = {}
    for name, label in DEFAULT_DISABLED_BOSSES.items():
        var = ctk.BooleanVar(value=(name not in DEFAULT_ENABLED_BOSSES))
        chk = ctk.CTkCheckBox(opt_left, text=label, variable=var)
        chk.pack(anchor="w", padx=10, pady=2)
        boss_vars[name] = var
        boss_checks[name] = chk
    for name, label in DEFAULT_DISABLED_ROOMS.items():
        var = ctk.BooleanVar(value=True)
        chk = ctk.CTkCheckBox(opt_right, text=label, variable=var)
        chk.pack(anchor="w", padx=10, pady=2)
        room_vars[name] = var
        room_checks[name] = chk
    def _set_block_enabled(block: ctk.CTkBaseClass, enabled: bool):
        st = "normal" if enabled else "disabled"
        try:
            children = block.winfo_children()
        except Exception:
            children = []
        for child in children:
            if isinstance(child, (ctk.CTkSlider, ctk.CTkCheckBox, ctk.CTkSwitch,
                                  ctk.CTkOptionMenu, ctk.CTkRadioButton, ctk.CTkButton)):
                try:
                    child.configure(state=st)
                except Exception:
                    pass
            if isinstance(child, ctk.CTkLabel):
                try:
                    child.configure(text_color=("white" if enabled else "gray50"))
                except Exception:
                    pass
            if hasattr(child, "winfo_children"):
                for g in child.winfo_children():
                    if isinstance(g, (ctk.CTkSlider, ctk.CTkCheckBox, ctk.CTkSwitch,
                                      ctk.CTkOptionMenu, ctk.CTkRadioButton, ctk.CTkButton)):
                        try:
                            g.configure(state=st)
                        except Exception:
                            pass
                    if isinstance(g, ctk.CTkLabel):
                        try:
                            g.configure(text_color=("white" if enabled else "gray50"))
                        except Exception:
                            pass
    def _set_item_randomizer_enabled(enabled: bool, force_no: bool = False):
        if force_no:
            try:
                item_var.set("No")
            except Exception:
                pass
        state = "normal" if enabled else "disabled"
        try:
            item_yes.configure(state=state)
            item_no.configure(state=state)
        except Exception:
            pass
    def _update_seed_lock(*_):
        locked = bool(seed_var.get().strip())
        _set_block_enabled(sec_stage, not locked)
        _set_block_enabled(sec_target, not locked)
        _set_block_enabled(sec_diff, not locked)
        _set_block_enabled(sec_item, not locked)
        _set_block_enabled(sec_char, not locked)
        _set_block_enabled(opt_scroll, not locked)
        if locked:
            for name, chk in boss_checks.items():
                try:
                    boss_vars[name].set(True)
                    chk.configure(state="disabled")
                except Exception:
                    pass
            for name, chk in room_checks.items():
                try:
                    room_vars[name].set(True)
                    chk.configure(state="disabled")
                except Exception:
                    pass
        else:
            if target_var.get():
                apply_target_rules()
            else:
                for name, chk in boss_checks.items():
                    try:
                        chk.configure(state="normal")
                    except Exception:
                        pass
                for name, chk in room_checks.items():
                    try:
                        chk.configure(state="normal")
                    except Exception:
                        pass
                _set_item_randomizer_enabled(True)
    seed_var.trace_add("write", _update_seed_lock)
    _update_seed_lock()
    def apply_only_rules():
        ob = bool(only_bosses_var.get())
        oroom = bool(only_rooms_var.get())
        if ob and oroom:
            only_rooms_var.set(False)
            oroom = False
        boss_enabled = True
        level_enabled = True
        if ob:
            level_enabled = False
            level_slider.set(0)
            level_val_lbl.configure(text=f"Selected: 0 / {total_rooms}")
        elif oroom:
            boss_enabled = False
            boss_slider.set(0)
            boss_val_lbl.configure(text=f"Selected: 0 / {total_bosses}")
        _set_block_enabled(boss_block, boss_enabled)
        _set_block_enabled(level_block, level_enabled)
    only_bosses_chk.configure(command=apply_only_rules)
    only_rooms_chk.configure(command=apply_only_rules)
    def _force_levels_checked_and_disabled(force_on: bool):
        for name, chk in room_checks.items():
            try:
                if force_on:
                    room_vars[name].set(True)
                    chk.configure(state="disabled")
                else:
                    chk.configure(state="normal")
            except Exception:
                pass
    def _force_bosses_target_mode(force_on: bool):
        exceptions = {"boss15.ini", "boss19.ini", "boss20.ini"}
        for name, chk in boss_checks.items():
            try:
                if force_on:
                    boss_vars[name].set(True)
                    if name in exceptions:
                        chk.configure(state="normal")
                    else:
                        chk.configure(state="disabled")
                else:
                    chk.configure(state="normal")
            except Exception:
                pass
    def apply_target_rules():
        on = target_var.get()
        if on:
            sec_stage.pack_forget()
            if not target_frame.winfo_ismapped():
                target_frame.pack(fill="x", padx=12, pady=(0, 12))
            if not target_hint_box.winfo_ismapped():
                target_hint_box.pack(fill="x", padx=12, pady=(0, 10))
                target_hint_label.pack(anchor="w", padx=12, pady=10)
            target_slider.configure(state="normal")
            target_val_label.configure(text_color="white")
            _force_levels_checked_and_disabled(True)
            _force_bosses_target_mode(True)
            _set_item_randomizer_enabled(False, force_no=True)
        else:
            try:
                target_frame.pack_forget()
                target_hint_box.pack_forget()
            except Exception:
                pass
            if not sec_stage.winfo_ismapped():
                sec_stage.pack(before=sec_target, fill="x", padx=12, pady=(12, 8))
            target_slider.configure(state="disabled")
            target_val_label.configure(text_color="gray50")
            _force_levels_checked_and_disabled(False)
            _force_bosses_target_mode(False)
            _set_item_randomizer_enabled(True)
            apply_only_rules()
        root.after(50, lambda: root.update_idletasks())
    target_switch.configure(command=apply_target_rules)
    apply_only_rules()
    apply_target_rules()
    def on_start():
        cfg.target_collect_mode = bool(target_var.get())
        cfg.item_randomizer_enabled = (item_var.get() == "Yes")
        cfg.difficulty = diff_var.get()
        cfg.difficulty_code = _difficulty_code_from_label(cfg.difficulty)
        cfg.random_start_character = bool(random_char_var.get())
        cfg.random_character_per_stage = bool(random_char_stage_var.get())
        if cfg.target_collect_mode:
            cfg.bosses_to_play = 0
            cfg.rooms_to_play = 0
            cfg.only_bosses = False
            cfg.only_rooms = False
            cfg.target_item_count = int(round(target_slider.get()))
        else:
            cfg.bosses_to_play = int(round(boss_slider.get()))
            cfg.rooms_to_play = int(round(level_slider.get()))
            cfg.only_bosses = bool(only_bosses_var.get())
            cfg.only_rooms = bool(only_rooms_var.get())
            cfg.target_item_count = int(round(target_slider.get()))
        try:
            seed_text = seed_var.get().strip()
        except Exception:
            seed_text = ""
        code_pattern = re.compile(
            r"^R(?P<R>\d+)-B(?P<B>\d+)-T(?P<T>[01])-C(?P<C>[0-2])-P(?P<P>[01])-(?P<S>\d+)$"
        )
        if seed_text:
            m = code_pattern.match(seed_text)
            if m:
                try:
                    rooms = int(m.group("R"))
                    bosses = int(m.group("B"))
                    t_flag = int(m.group("T"))
                    c_flag = int(m.group("C"))
                    p_flag = int(m.group("P"))
                    s_val = int(m.group("S"))
                except ValueError:
                    messagebox.showerror(
                        "Invalid Seed Code",
                        "The seed code could not be parsed.\n"
                        "Please use a format like: R3-B3-T0-C1-P0-898677"
                    )
                    return
                cfg.route_seed = s_val
                cfg.target_collect_mode = bool(t_flag)
                cfg.item_randomizer_enabled = bool(p_flag)
                if not cfg.target_collect_mode:
                    cfg.rooms_to_play = rooms
                    cfg.bosses_to_play = bosses
                if c_flag == 0:
                    cfg.random_start_character = False
                    cfg.random_character_per_stage = False
                elif c_flag == 1:
                    cfg.random_start_character = True
                    cfg.random_character_per_stage = False
                else:
                    cfg.random_start_character = True
                    cfg.random_character_per_stage = True
            else:
                try:
                    cfg.route_seed = int(seed_text)
                except ValueError:
                    messagebox.showerror(
                        "Invalid Seed",
                        "Please enter either a number (e.g. 898677) or a full code like:\n"
                        "R3-B3-T0-C1-P0-898677"
                    )
                    return
        else:
            cfg.route_seed = random.randint(100000, 999999)
        cfg.disabled_bosses = {name for name, var in boss_vars.items() if not var.get()}
        cfg.disabled_rooms = {name for name, var in room_vars.items() if not var.get()}
        write_selected_difficulty_to_encrypted_save(cfg.difficulty)
        try:
            base_dir = os.path.dirname(os.path.dirname(__file__))
            wav_path = os.path.join(base_dir, "Custom", "its-boshy-time.wav")
            if os.path.exists(wav_path):
                try:
                    import winsound
                    winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                except Exception:
                    pass
                start_btn.configure(state="disabled", text="Creating Route...")
                root.after(1500, root.destroy)
                return
        except Exception:
            pass
        root.destroy()
    start_btn.configure(command=on_start)
    def on_close():
        cfg.cancelled = True
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()
    return cfg
