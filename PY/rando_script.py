# ======================================================
# rando_script_refactored.py
# Main entry that pulls pixel + achievement triggers out to trigger_engine.py
# and common helpers to save_utils.py, window_utils.py, positions_utils.py,
# tracker_utils.py
# ======================================================
from __future__ import annotations
import os, sys, time, json, random, shutil, ctypes, subprocess
from threading import Event, Thread, Lock
import ctypes  # replaced keyboard with WinAPI hotkey
GetAsyncKeyState = ctypes.windll.user32.GetAsyncKeyState

def _hotkey_ctrl_r():
    VK_CONTROL = 0x11
    VK_R = 0x52
    return (GetAsyncKeyState(VK_CONTROL) & 0x8000) and (GetAsyncKeyState(VK_R) & 0x8000)


# >>> F2-Helferfunktion (für Ctrl+R-Reset) <<<
def press_f2(delay: float = 0.05):
    """Sendet F2 über die WinAPI."""
    VK_F2 = 0x71
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(VK_F2, 0, 0, 0)   # key down
        time.sleep(delay)
        user32.keybd_event(VK_F2, 0, 2, 0)   # key up (KEYEVENTF_KEYUP = 0x0002)
    except Exception as e:
        # log ist weiter unten importiert, aber zur Laufzeit vorhanden
        try:
            from PY.logger import log as _log_inner
            _log_inner(f"⚠️ Failed to send F2: {e}")
        except Exception:
            pass
# ----------------------------------------------------


# Qt env
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false")


import os as _os, sys as _sys
# Ensure parent folder (project root) is on sys.path so "PY.*" imports work even when running this file directly
_proj_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _proj_root not in _sys.path:
    _sys.path.insert(0, _proj_root)

# Project imports
from PY.config import *
from PY.logger import log
from PY.rc4_utils import decrypt_save, encrypt_save, rc4_crypt

from PY.pixel_detector import check_pixel_regions as _pd_check_pixel_regions
from PY.gui_config import build_gui_config, write_selected_difficulty_to_encrypted_save
from PY.route_builder import build_random_route
from PY.character_randomizer import set_random_character   # <<< Random-Character-API
from PY.target_collect import (                           # <<< NEU: Target-Mode-API
    _clear_target_file,
    _choose_targets,
    _write_targets_file,
    _monitor_targets_thread,
)
from PY.end_stats import show_end_stats
from PY.reset_overlay import show_reset_overlay
from PY.loading_overlay import begin_loading_overlay, end_loading_overlay
try:
    from PY.config import overlays_enabled
except Exception:
    overlays_enabled = True

# ---------- Overlay-Wrappers ----------
def safe_begin_overlay(*args, **kwargs):
    if not overlays_enabled:
        return
    try:
        begin_loading_overlay(*args, **kwargs)
    except Exception as e:
        log(f"⚠️ begin_loading_overlay failed: {e}")


def safe_end_overlay():
    if not overlays_enabled:
        return
    try:
        end_loading_overlay()
    except Exception as e:
        log(f"⚠️ end_loading_overlay failed: {e}")
# -----------------------------------------------------------------------------


# New modules
from PY.window_utils import find_game_hwnd_by_pid, is_hwnd_valid, focus_hwnd, send_ctrl_s, send_esc, send_key_R, terminate_proc_tree
from PY.save_utils import audit_save, snapshot_plain, mirror_plain_for_tracker, size_or_zero, restore_if_save_shrunk, mark_last_writer
from PY.positions_utils import load_positions, apply_positions_to_save
from PY.tracker_utils import start_live_tracker_robust
from PY.trigger_engine import check_pixel_trigger, check_achievements_trigger

# ------------------------------------------------------

def perform_randomizer_overwrite(stage_name: str, POS_DATA):
    ok = apply_positions_to_save(stage_name, POS_DATA)
    if ok:
        log("💾 Overwrite SaveFile (Randomizer) done.")
    else:
        log("⚠️ Overwrite skipped (apply_positions_to_save failed)." )
    mirror_plain_for_tracker()
    return ok


def initialize_saves_from(folder):
    ref_hash = {}
    for i in (1, 2, 3):
        src = os.path.join(folder, f"SaveFile{i}.ini")
        dst = os.path.join(iwbtb_folder, f"SaveFile{i}.ini")  # <<< KORREKTED!
        if os.path.exists(src):
            shutil.copy2(src, dst)
            try:
                import hashlib
                h = hashlib.md5()
                with open(src, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                if i in (2, 3):
                    ref_hash[i] = h.hexdigest()
            except Exception:
                pass
            log(f"Initial copy: {src} -> {dst}")
        else:
            log(f"WARNING: {src} missing – not copied")
    mirror_plain_for_tracker()
    return ref_hash


def check_auto_restore_from(folder, ref_hash):
    for i in (2, 3):
        src = os.path.join(folder, f"SaveFile{i}.ini")
        dst = os.path.join(iwbtb_folder, f"SaveFile{i}.ini")
        try:
            import hashlib
            def md5(p):
                h = hashlib.md5()
                with open(p, "rb") as f:
                    for chunk in iter(lambda: f.read(8192), b""):
                        h.update(chunk)
                return h.hexdigest()
            if os.path.exists(dst):
                if ref_hash.get(i) and os.path.exists(src) and md5(dst) != ref_hash[i]:
                    shutil.copy2(src, dst)
                    log(f"Auto-restore: SaveFile{i}.ini changed → restored")
            elif os.path.exists(src):
                shutil.copy2(src, dst)
                log(f"Auto-restore: SaveFile{i}.ini missing → recreated")
        except Exception:
            pass


def reset_savefile1_from(folder):
    src = os.path.join(folder, "SaveFile1.ini")
    if os.path.exists(src):
        shutil.copy2(src, save_enc)
        mark_last_writer("reset_restore", {"src": src})
        audit_save("post_reset_restore", force=True)
        mirror_plain_for_tracker()
        log("SaveFile1.ini reset due to 'solgryn' achievement")


def keep_game_liveness(game_proc, state, grace_s=game_absent_grace_s):
    now = time.time()

    hwnd = state.get("force_hwnd")
    if hwnd and is_hwnd_valid(hwnd):
        state["last_game_seen"] = now
        return True

    try:
        new_hwnd = find_game_hwnd_by_pid(game_proc.pid, timeout_s=0.0, poll=0.0)
    except Exception:
        new_hwnd = None
    if new_hwnd and is_hwnd_valid(new_hwnd):
        state["force_hwnd"] = new_hwnd
        state["last_game_seen"] = now
        return True

    try:
        import pygetwindow as _gw
        for title in [window_title] + list(window_title_variants):
            try:
                ws = _gw.getWindowsWithTitle(title)
                if ws:
                    try:
                        if ws[0].isVisible:
                            state["last_game_seen"] = now
                            try:
                                state["force_hwnd"] = getattr(ws[0], "_hWnd", None) or state.get("force_hwnd")
                            except Exception:
                                pass
                            return True
                    except Exception:
                        state["last_game_seen"] = now
                        return True
            except Exception:
                continue
    except Exception:
        pass

    missing_frames = state.get("window_missing_frames", 0)
    missing_secs = max(0.0, missing_frames) * float(poll_interval)
    last_seen = state.get("last_game_seen", 0.0)
    too_long = ((now - last_seen) > grace_s) or (missing_secs > grace_s)
    return not too_long


if __name__ == "__main__":
    # DPI awareness early
    try:
        DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = ctypes.c_void_p(-4)
        ctypes.windll.user32.SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2)
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

    log("Randomizer started (positions.json + overlay + Difficulty Modes)")
    try:
        log(f"⚙️ Randomizer config loaded: poll={poll_interval:.1f}s, cooldown={trigger_pause_s:.1f}s, repeats={getattr(__import__('PY.config', fromlist=['allow_repeats']), 'allow_repeats', False)}")
    except Exception:
        pass

    # Load trigger targets
    if os.path.exists(trigger_json):
        with open(trigger_json, "r", encoding="utf-8") as f:
            raw_triggers = json.load(f)
    else:
        raw_triggers = {}
    trigger_targets = {}
    for name, entries in raw_triggers.items():
        lname = name.lower()
        if isinstance(entries, list):
            trigger_targets[lname] = entries
        else:
            trigger_targets[lname] = [
                {"section": "achievements", "source": "SaveFile1.ini", "description": "legacy trigger"}
            ]
    total_entries = sum(len(v) for v in trigger_targets.values())
    log(f"{len(trigger_targets)} trigger names loaded ({total_entries} total entries)")

    # Pixel regions
    if os.path.exists(pixel_json):
        with open(pixel_json, "r", encoding="utf-8") as f:
            pixel_regions = json.load(f)
        log(f"{len(pixel_regions) if isinstance(pixel_regions, list) else 0} pixel regions loaded.")
    else:
        pixel_regions = []
        log("⚠️ WARNING: pixel_regions.json not found, pixel detection disabled.")

    POS_DATA = load_positions()

    # GUI & difficulty
    cfg = build_gui_config()
    if cfg.cancelled:
        sys.exit(0)

    import PY.config as _cfg
    difficulty = getattr(cfg, "difficulty", "Average").strip().lower()
    if difficulty in ("ez", "ez mode", "ez-mode"):
        _cfg.room_folder = _cfg.ez_room
        _cfg.boss_folder = _cfg.ez_boss
        folder_used = _cfg.ez_folder
        diff_label = "Ez Mode 🧊"
    elif difficulty in ("rage", "rage mode", "rage-mode", "you're gonna rage"):
        _cfg.room_folder = _cfg.rage_room
        _cfg.boss_folder = _cfg.rage_boss
        folder_used = _cfg.rage_folder
        diff_label = "Rage Mode 🔥"
    else:
        _cfg.room_folder = os.path.join(_cfg.ini_folder, "Room")
        _cfg.boss_folder = os.path.join(_cfg.ini_folder, "Boss")
        folder_used = _cfg.ini_folder
        diff_label = "Average ⚖️"
    log(f"🎚 Difficulty set to {diff_label}")
    log(f"📁 Using pools: Rooms={_cfg.room_folder} | Bosses={_cfg.boss_folder}")

    # <<< NEU: Target-Mode-Flag auch in config setzen, damit Live Tracker es kennt >>>
    try:
        _cfg.target_collect_mode = bool(getattr(cfg, "target_collect_mode", False))
    except Exception:
        pass

    # Events/Threads
    stop_event = Event()

    # Runtime state ...
    state = {
        "route_i": 0,
        "current_stage": None,
        "last_trophies": {},
        "pixel_streak": 0,
        "last_game_seen": time.time(),
        "triggered_pixels": set(),
        "pause_until": 0.0,
        "last_trigger_time": 0.0,
        "last_was_boss": False,
        "force_solgryn_next": False,
        "force_next_file": None,
        "item_cooldown_until": 0.0,
        "item_thread_running": True,
        "force_hwnd": None,
    }

    # Write difficulty into save
    try:
        write_selected_difficulty_to_encrypted_save(cfg.difficulty)
    except Exception as e:
        log(f"⚠️ Failed to write Difficulty to save: {e}")

    # ------------------ Route / Targets ------------------
    targets_done_event = Event()
    if getattr(cfg, "target_collect_mode", False):
        try:
            _clear_target_file()
            target_count = int(getattr(cfg, "target_item_count", 5) or 5)
            targets = _choose_targets(target_count)
            _write_targets_file(targets)
            Thread(
                target=_monitor_targets_thread,
                args=(stop_event, targets_done_event),
                daemon=True,
            ).start()
            route = []
            log(f"➡️  Target Collect Mode active — endless random route until {target_count} targets are collected.")
        except Exception as e:
            _clear_target_file()
            route = build_random_route(cfg, POS_DATA)
            log(f"⚠️ Target Collect Mode init failed: {e}")
    else:
        _clear_target_file()  # <<< wichtig: alte Targets immer weg, wenn Mode OFF
        route = build_random_route(cfg, POS_DATA)
        log("➡️  Route built: " + " -> ".join(route))
        
    # Item Randomizer thread
    try:
        from PY.item_randomizer import monitor_items
        if getattr(cfg, "item_randomizer_enabled", True):
            Thread(target=monitor_items, args=(stop_event, getattr(cfg, "item_randomizer_popups", False)), daemon=True).start()
            log("🧩 Item Randomizer (re)started.")
        else:
            log("🧩 Item Randomizer disabled by GUI.")
    except Exception as e:
        log(f"⚠️ Item Randomizer thread failed: {e}")

    # Start game, then mirror, then tracker
    if not os.path.exists(game_exe):
        log(f"⛔ Game not found: {game_exe}")
        sys.exit(1)
    game_proc = subprocess.Popen([game_exe], cwd=iwbtb_folder)
    log("🎮 Game launched.")

    # Reset-Overlay auch beim Spielstart
    try:
        show_reset_overlay(stop_event)
    except Exception as e:
        log(f"⚠️ Reset overlay failed on game start: {e}")

    ref_hash = initialize_saves_from(folder_used)

    log("⌛ Waiting for the game window to become visible...")
    game_hwnd = find_game_hwnd_by_pid(game_proc.pid, timeout_s=15.0, poll=0.1)
    if game_hwnd and is_hwnd_valid(game_hwnd):
        log(f"🪟 Game window detected (HWND={game_hwnd}) — initializing…")
        time.sleep(0.4)
        try:
            state["force_hwnd"] = game_hwnd
            state["last_game_seen"] = time.time()
            log("🔗 Pixel detector pinned to game HWND (force_hwnd set).")
        except Exception:
            pass

    # copy license (Template aus INI → IWBTB)
    license_path = os.path.join(ini_folder, "onlineLicense.ini")
    if os.path.exists(license_path):
        try:
            shutil.copy2(license_path, os.path.join(iwbtb_folder, "onlineLicense.ini"))
            log("✅ onlineLicense.ini copied.")
        except Exception as e:
            log(f"⚠️ Failed to copy onlineLicense.ini: {e}")

    # Random Character beim Start (GUI-Option) – NACH dem Kopieren
    try:
        if getattr(cfg, "random_start_character", False):
            set_random_character()
    except Exception as e:
        log(f"⚠️ Random start character failed: {e}")

    audit_save("startup", force=True)
    mirror_plain_for_tracker()

    # Live Tracker
    tracker_proc = start_live_tracker_robust()
    if tracker_proc is None:
        log("⚠️ Live Tracker exited early. Check INI\\live_tracker_boot.log for details.")

    # Cleanup
    import atexit
    def _cleanup():
        try:
            stop_event.set()
        except Exception:
            pass
        try:
            terminate_proc_tree(tracker_proc, name="Live Tracker", wait_s=0.8)
        except Exception:
            pass
        try:
            terminate_proc_tree(game_proc, name="Game Process", wait_s=0.8)
        except Exception:
            pass
    atexit.register(_cleanup)

    # ------------------------------- MAIN LOOP -------------------------------
    reset_held = False
    _last_hb = 0.0

    while True:
        try:
            # ---- Game-Liveness: beende Randomizer, wenn das Spiel weg ist ----
            # 1) Prozess beendet?
            if game_proc.poll() is not None:
                log("🎮 Game process has exited — shutting down randomizer.")
                try:
                    stop_event.set()
                except Exception:
                    pass
                break

            # 2) Fenster zu lange nicht gesehen?
            if not keep_game_liveness(game_proc, state, grace_s=game_absent_grace_s):
                log("🧹 Game window not found for too long — shutting down randomizer.")
                try:
                    stop_event.set()
                except Exception:
                    pass
                break

            # ---------------- Herz der Loop: Trigger, Route, Reset -------------

            # Ctrl+R Reset
            if _hotkey_ctrl_r():
                if not reset_held:
                    reset_held = True
                    try:
                        # Flag für Live Tracker ... (falls du da noch etwas hast)

                        reset_savefile1_from(folder_used)
                        ref_hash = initialize_saves_from(folder_used)
                        mark_last_writer("ctrl_r_reset")
                        audit_save("post_ctrl_r_reset", force=True)
                        mirror_plain_for_tracker()

                        # Route/Targets rebuild
                        if getattr(cfg, "target_collect_mode", False):
                            _clear_target_file()
                            target_count = int(getattr(cfg, "target_item_count", 5) or 5)
                            targets = _choose_targets(target_count)
                            _write_targets_file(targets)
                            targets_done_event.clear()
                            state["force_next_file"] = None
                            state["current_stage"] = None
                        else:
                            route = build_random_route(cfg, POS_DATA)
                            state["route_i"] = 0
                            state["force_next_file"] = None
                            state["current_stage"] = None

                        show_reset_overlay(stop_event)
                        if state.get("force_hwnd") and is_hwnd_valid(state["force_hwnd"]):
                            focus_hwnd(state["force_hwnd"])
                        press_f2()
                        time.sleep(0.4)
                    except Exception as e:
                        log(f"⚠️ Reset failed: {e}")
            else:
                reset_held = False

            now = time.time()
            if now < state.get("pause_until", 0.0):
                time.sleep(poll_interval)
                continue

            check_auto_restore_from(folder_used, ref_hash)

            cooldown_until = 0.0
            if getattr(cfg, "target_collect_mode", False):
                cooldown_until = max(state.get("item_cooldown_until", 0.0), 0.0)

            triggered = False
            planned_next_file = None
            current_stage = state.get("current_stage")

            # --- Pixel Trigger via engine ---
            trig, reason, p_region, p_level = check_pixel_trigger(
                pixel_check_fn=_pd_check_pixel_regions,
                pixel_regions=pixel_regions,
                state=state,
                current_stage=current_stage,
                cooldown_until=cooldown_until,
            )
            if trig:
                triggered = True
                if reason == "first_pixel":
                    if getattr(cfg, "target_collect_mode", False):
                        rooms = list(POS_DATA["rooms"].keys())
                        bosses = list(POS_DATA["bosses"].keys())
                        preferred = "boss" if not state.get("last_was_boss", False) else "room"
                        if preferred == "boss" and bosses:
                            planned_next_file = random.choice(bosses)
                            state["last_was_boss"] = True
                        elif rooms:
                            planned_next_file = random.choice(rooms)
                            state["last_was_boss"] = False
                        state["current_stage"] = (planned_next_file or "").lower()
                    else:
                        if route and state["route_i"] < len(route):
                            planned_next_file = route[state["route_i"]]
                            state["current_stage"] = (planned_next_file or "").lower()
                log(f"✅ Pixel-trigger accepted ({p_region}) → preparing stage transition")

            # --- Achievement/Trophy Trigger via engine ---
            if not triggered:
                ach_trig, ach_reason = check_achievements_trigger(trigger_targets, state)
                if ach_trig:
                    triggered = True

            # Target-Mode: wenn alles gesammelt wurde → Solgryn erzwingen
            if getattr(cfg, "target_collect_mode", False) and targets_done_event.is_set():
                state["force_solgryn_next"] = True

            if triggered:
                state["pause_until"] = now + trigger_pause_s

                if getattr(cfg, "target_collect_mode", False):
                    if state.get("force_solgryn_next", False):
                        next_file = "boss_solgryn.ini"
                        state["force_solgryn_next"] = False
                        overlay_text = "Final Battle – Solgryn!"
                    else:
                        rooms = list(POS_DATA["rooms"].keys())
                        bosses = list(POS_DATA["bosses"].keys())
                        preferred = "boss" if not state.get("last_was_boss", False) else "room"
                        if preferred == "boss" and bosses:
                            next_file = random.choice(bosses)
                            state["last_was_boss"] = True
                        elif rooms:
                            next_file = random.choice(rooms)
                            state["last_was_boss"] = False
                        else:
                            next_file = None
                        overlay_text = "Loading next stage..."
                else:
                    if planned_next_file:
                        next_file = planned_next_file
                    elif state["route_i"] >= len(route):
                        time.sleep(poll_interval)
                        continue
                    else:
                        next_file = route[state["route_i"]]
                    overlay_text = "Loading next stage..."

                if not next_file:
                    log("⚠️ No next stage available (all pools disabled?).")
                    time.sleep(poll_interval)
                    continue

                # Random Character pro Stage (Boss + Level), falls in GUI aktiviert
                try:
                    if getattr(cfg, "random_character_per_stage", False):
                        set_random_character()
                except Exception as e:
                    log(f"⚠️ Random character per stage failed: {e}")

                try:
                    if state.get("force_hwnd") and is_hwnd_valid(state["force_hwnd"]):
                        focus_hwnd(state["force_hwnd"])

                    # PRE-SNAPSHOT
                    try:
                        pre_plain = decrypt_save(save_enc, rc4_key)
                        pre_snap = snapshot_plain("pre_transition", pre_plain)
                    except Exception:
                        pre_snap = None

                    step_info = None
                    if not getattr(cfg, "target_collect_mode", False) and len(route) > 0:
                        step_info = f"Step {state['route_i']+1}/{len(route)}"
                    safe_begin_overlay(stop_event, text=overlay_text, step_info=step_info, blackout=True)

                    try:
                        before_size = size_or_zero(save_enc)

                        def quick_overwrite():
                            perform_randomizer_overwrite(next_file, POS_DATA)
                            time.sleep(0.06)

                        send_ctrl_s()
                        time.sleep(0.06)

                        quick_overwrite()

                        send_key_R()
                        time.sleep(0.06)

                        quick_overwrite()

                        send_key_R()
                        time.sleep(0.06)

                        send_key_R()
                        time.sleep(0.06)

                        quick_overwrite()

                        send_key_R()
                        time.sleep(0.06)

                        send_ctrl_s()
                        time.sleep(0.25)

                        send_key_R()
                        time.sleep(0.25)

                        try:
                            post_plain = decrypt_save(save_enc, rc4_key)
                            from PY.save_utils import snapshot_plain
                            snap = snapshot_plain("route_backup", post_plain)
                            if snap:
                                mark_last_writer("route_backup", {"snapshot": os.path.basename(snap)})
                        except Exception:
                            pass
                    finally:
                        safe_end_overlay()

                    restore_if_save_shrunk(before_size, min_expected=96, window_s=3.0)

                    state["last_trigger_time"] = time.time()
                    state["current_stage"] = (next_file or "").lower()
                    if not getattr(cfg, "target_collect_mode", False):
                        state["route_i"] += 1
                        log(f"✅ Next stage loaded: {next_file} (Step {state['route_i']}/{len(route)})")
                    else:
                        log(f"✅ Next stage (endless): {next_file}")

                    audit_save("post_transition", force=True)
                    mirror_plain_for_tracker()

                except Exception as e:
                    log(f"⚠️ Route trigger failed: {e}")

            time.sleep(poll_interval)

        except KeyboardInterrupt:
            try:
                stop_event.set()
            except Exception:
                pass
            break
        except Exception as e:
            log(f"Error: {e}")
            time.sleep(1)
