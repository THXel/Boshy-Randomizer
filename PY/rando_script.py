from __future__ import annotations
import os, sys, time, json, random, shutil, ctypes, subprocess
from threading import Event, Thread, Lock
import ctypes
GetAsyncKeyState = ctypes.windll.user32.GetAsyncKeyState
def _hotkey_ctrl_r():
    VK_CONTROL = 0x11
    VK_R = 0x52
    return (GetAsyncKeyState(VK_CONTROL) & 0x8000) and (GetAsyncKeyState(VK_R) & 0x8000)
def press_f2(delay: float = 0.05):
    VK_F2 = 0x71
    try:
        user32 = ctypes.windll.user32
        user32.keybd_event(VK_F2, 0, 0, 0)
        time.sleep(delay)
        user32.keybd_event(VK_F2, 0, 2, 0)
    except Exception as e:
        try:
            from PY.logger import log as _log_inner
            _log_inner(f"⚠️ Failed to send F2: {e}")
        except Exception:
            pass
os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
os.environ.setdefault("QT_AUTO_SCREEN_SCALE_FACTOR", "1")
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false")
import os as _os, sys as _sys
_proj_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
if _proj_root not in _sys.path:
    _sys.path.insert(0, _proj_root)
from PY.config import *
from PY.logger import log
from PY.rc4_utils import decrypt_save, encrypt_save, rc4_crypt
from PY.pixel_detector import check_pixel_regions as _pd_check_pixel_regions
from PY.gui_config import build_gui_config, write_selected_difficulty_to_encrypted_save
from PY.route_builder import build_random_route
from PY.character_randomizer import (
    set_random_character,
    enable_character_lock,
    init_seed,
)
from PY.target_collect import (
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
from PY.window_utils import find_game_hwnd_by_pid, is_hwnd_valid, focus_hwnd, send_ctrl_s, send_esc, send_key_R, terminate_proc_tree
from PY.save_utils import audit_save, snapshot_plain, mirror_plain_for_tracker, size_or_zero, restore_if_save_shrunk, mark_last_writer
from PY.positions_utils import load_positions, apply_positions_to_save
from PY.tracker_utils import start_live_tracker_robust
from PY.trigger_engine import check_pixel_trigger, check_achievements_trigger
from PY import state_exporter
try:
    from PY.save_profile_manager import write_all_saves_from_profiles
except ModuleNotFoundError:
    from save_profile_manager import write_all_saves_from_profiles
def start_state_exporter_thread(interval: float = 1.0):
\
\
\
\
    try:
        t = Thread(
            target=state_exporter.main,
            kwargs={"loop": True, "interval": float(interval)},
            daemon=True,
        )
        t.start()
        log(f"[state_exporter] background exporter started (interval={interval:.2f}s)")
        return t
    except Exception as e:
        log(f"[state_exporter] could not start exporter thread: {e}")
        return None
def perform_randomizer_overwrite(stage_name: str, POS_DATA):
    ok = apply_positions_to_save(stage_name, POS_DATA)
    if ok:
        log("💾 Overwrite SaveFile (Randomizer) done.")
    else:
        log("⚠️ Overwrite skipped (apply_positions_to_save failed)." )
    mirror_plain_for_tracker()
    return ok
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
    if os.path.exists(pixel_json):
        with open(pixel_json, "r", encoding="utf-8") as f:
            pixel_regions = json.load(f)
        log(f"{len(pixel_regions) if isinstance(pixel_regions, list) else 0} pixel regions loaded.")
    else:
        pixel_regions = []
        log("⚠️ WARNING: pixel_regions.json not found, pixel detection disabled.")
    POS_DATA = load_positions()
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
    route_seed_raw = getattr(cfg, "route_seed", None)
    route_seed_int = None
    if route_seed_raw in ("", None):
        log("🎲 Route seed: none (standard random route)")
    else:
        try:
            route_seed_int = int(route_seed_raw)
            log(f"🎲 Route seed from GUI: {route_seed_int}")
        except Exception as e:
            log(f"⚠️ Invalid route seed ({route_seed_raw!r}) – ignoring: {e}")
            route_seed_int = None
    route_code = None
    try:
        if route_seed_int is not None:
            rooms = int(getattr(cfg, "rooms_to_play", 0))
            bosses = int(getattr(cfg, "bosses_to_play", 0))
            t_flag = 1 if getattr(cfg, "target_collect_mode", False) else 0
            if getattr(cfg, "random_character_per_stage", False):
                c_flag = 2
            elif getattr(cfg, "random_start_character", False):
                c_flag = 1
            else:
                c_flag = 0
            p_flag = 1 if getattr(cfg, "item_randomizer_enabled", False) else 0
            route_code = f"R{rooms}-B{bosses}-T{t_flag}-C{c_flag}-P{p_flag}-{route_seed_int}"
            log(f"🎲 Route code: {route_code}")
    except Exception as e:
        log(f"⚠️ Failed to compute route code: {e}")
    try:
        init_seed(route_seed_int)
    except Exception as e:
        log(f"⚠️ Could not init character seed: {e}")
    try:
        if getattr(cfg, "random_start_character", False) or getattr(cfg, "random_character_per_stage", False):
            enable_character_lock()
            log("🔒 Character lock enabled – F3 (character menu) is blocked while random character mode is active.")
        else:
            log("ℹ️ Character lock not enabled (no random character mode selected).")
    except Exception as e:
        log(f"⚠️ Could not enable character lock: {e}")
    try:
        _cfg.target_collect_mode = bool(getattr(cfg, "target_collect_mode", False))
    except Exception:
        pass
    stop_event = Event()
    state = {
        "route_i": 0,
        "route_list": [],
        "route_index": 0,
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
        "route_code": route_code,
    }
    try:
        write_all_saves_from_profiles(tag="startup")
        log("💾 Save profiles initialized from JSON (startup).")
    except Exception as e:
        log(f"⚠️ Failed to initialize saves from profiles: {e}")
    try:
        write_selected_difficulty_to_encrypted_save(cfg.difficulty)
    except Exception as e:
        log(f"⚠️ Failed to write Difficulty to save: {e}")
    targets_done_event = Event()
    if getattr(cfg, "target_collect_mode", False) and route_seed_int is not None:
        target_rng = random.Random(route_seed_int + 1337)
        log("🎲 Target Collect RNG initialized from route seed.")
    else:
        target_rng = random
    if getattr(cfg, "target_collect_mode", False):
        try:
            _clear_target_file()
            target_count = int(getattr(cfg, "target_item_count", 5) or 5)
            targets = _choose_targets(target_count, seed=route_seed_int)
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
        _clear_target_file()
        route = build_random_route(cfg, POS_DATA)
        log("➡️  Route built: " + " -> ".join(route))
        state["route_list"] = list(route)
        state["route_index"] = 0
    try:
        from PY.item_randomizer import monitor_items
        if getattr(cfg, "item_randomizer_enabled", True):
            Thread(target=monitor_items, args=(stop_event, getattr(cfg, "item_randomizer_popups", False)), daemon=True).start()
            log("🧩 Item Randomizer (re)started.")
        else:
            log("🧩 Item Randomizer disabled by GUI.")
    except Exception as e:
        log(f"⚠️ Item Randomizer thread failed: {e}")
    if not os.path.exists(game_exe):
        log(f"⛔ Game not found: {game_exe}")
        sys.exit(1)
    game_proc = subprocess.Popen([game_exe], cwd=iwbtb_folder)
    log("🎮 Game launched.")
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
    try:
        show_reset_overlay(
            stop_event,
            duration=4.0,
            route_code=state.get("route_code"),
            route_code_duration=15.0,
        )
    except Exception as e:
        log(f"⚠️ Reset overlay on startup failed: {e}")
    try:
        if getattr(cfg, "random_start_character", False):
            set_random_character()
    except Exception as e:
        log(f"⚠️ Random start character failed: {e}")
    audit_save("startup", force=True)
    mirror_plain_for_tracker()
    exporter_thread = start_state_exporter_thread(interval=1.0)
    tracker_proc = start_live_tracker_robust()
    if tracker_proc is None:
        log("⚠️ Live Tracker exited early. Check INI\\live_tracker_boot.log for details.")
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
    reset_held = False
    _last_hb = 0.0
    while True:
        try:
            if game_proc.poll() is not None:
                log("🎮 Game process has exited — shutting down randomizer.")
                try:
                    stop_event.set()
                except Exception:
                    pass
                break
            if not keep_game_liveness(game_proc, state, grace_s=game_absent_grace_s):
                log("🧹 Game window not found for too long — shutting down randomizer.")
                try:
                    stop_event.set()
                except Exception:
                    pass
                break
            if _hotkey_ctrl_r():
                if not reset_held:
                    reset_held = True
                    try:
                        write_all_saves_from_profiles(tag="ctrl_r_reset")
                        mark_last_writer("ctrl_r_reset")
                        audit_save("post_ctrl_r_reset", force=True)
                        mirror_plain_for_tracker()
                        if getattr(cfg, "target_collect_mode", False):
                            _clear_target_file()
                            target_count = int(getattr(cfg, "target_item_count", 5) or 5)
                            targets = _choose_targets(target_count, seed=route_seed_int)
                            _write_targets_file(targets)
                            targets_done_event.clear()
                            state["force_next_file"] = None
                            state["current_stage"] = None
                            if route_seed_int is not None:
                                target_rng = random.Random(route_seed_int + 1337)
                                log("🎲 Target Collect RNG reinitialized after reset.")
                            else:
                                target_rng = random
                        else:
                            route = build_random_route(cfg, POS_DATA)
                            state["route_i"] = 0
                            state["force_next_file"] = None
                            state["current_stage"] = None
                        try:
                            show_reset_overlay(
                                stop_event,
                                duration=4.0,
                                route_code=state.get("route_code"),
                                route_code_duration=15.0,
                            )
                        except Exception as e:
                            log(f"⚠️ Reset overlay (with route code) failed: {e}")
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
            cooldown_until = 0.0
            if getattr(cfg, "target_collect_mode", False):
                cooldown_until = max(state.get("item_cooldown_until", 0.0), 0.0)
            triggered = False
            planned_next_file = None
            current_stage = state.get("current_stage")
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
                            planned_next_file = target_rng.choice(bosses)
                            state["last_was_boss"] = True
                        elif rooms:
                            planned_next_file = target_rng.choice(rooms)
                            state["last_was_boss"] = False
                        state["current_stage"] = (planned_next_file or "").lower()
                    else:
                        if route and state["route_i"] < len(route):
                            planned_next_file = route[state["route_i"]]
                            state["current_stage"] = (planned_next_file or "").lower()
                log(f"✅ Pixel-trigger accepted ({p_region}) → preparing stage transition")
            if not triggered:
                ach_trig, ach_reason = check_achievements_trigger(trigger_targets, state)
                if ach_trig:
                    triggered = True
                    try:
                        if isinstance(ach_reason, str) and ach_reason.lower() == "achievement:solgryn":
                            log("🏁 Solgryn achievement detected – starting end stats overlay.")
                            show_end_stats(stop_event, route_code=state.get("route_code"))
                    except Exception as e:
                        log(f"⚠️ Could not start end_stats overlay: {e}")
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
                            next_file = target_rng.choice(bosses)
                            state["last_was_boss"] = True
                        elif rooms:
                            next_file = target_rng.choice(rooms)
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
                try:
                    if getattr(cfg, "random_character_per_stage", False):
                        set_random_character()
                except Exception as e:
                    log(f"⚠️ Random character per stage failed: {e}")
                try:
                    if state.get("force_hwnd") and is_hwnd_valid(state["force_hwnd"]):
                        focus_hwnd(state["force_hwnd"])
                    try:
                        pre_plain = decrypt_save(save_enc, rc4_key)
                        pre_snap = snapshot_plain("pre_transition", pre_plain)
                    except Exception:
                        pre_snap = None
                    step_info = None
                    if not getattr(cfg, "target_collect_mode", False) and len(route) > 0:
                        step_info = f"Step {state['route_i']+1}/{len(route)}"
                    safe_begin_overlay(
                        stop_event,
                        text=overlay_text,
                        step_info=step_info,
                        blackout=True,
                        route_code=state.get("route_code"),
                    )
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
                        state["route_index"] = state["route_i"]
                        state["route_list"] = list(route)
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
