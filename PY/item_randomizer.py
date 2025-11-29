from __future__ import annotations
import os
import json
import random
import time

from PY.logger import log
from PY.config import iwbtb_folder, ini_folder, save_enc
from PY.loading_overlay import is_loading_overlay_active

from PY.file_utils import smart_read, smart_write
from PY.ini_utils import parse_ini, apply_values_in_section

# Paths
items_path = os.path.join(ini_folder, "items.json")
characters_path = os.path.join(ini_folder, "characters.json")
item_randomizer_state_path = os.path.join(ini_folder, "item_randomizer_state.json")
events_path = os.path.join(ini_folder, "item_randomizer_events.json")
stage_sources_path = os.path.join(ini_folder, "item_randomizer_stage_sources.json")

tmp_old = os.path.join(iwbtb_folder, "_old_plain.ini")

# Tuning
poll_interval_sec = 0.30
avoid_repeats = True

# Blacklist by canonical name
BLACKLIST_SOURCES = {"Awesomesauce", "Dark Boshy"}
BLACKLIST_NAMES = BLACKLIST_SOURCES

# Cooldown & verification
cooldown_sec = 3.0
verify_delay_sec = 2.0

# Globals
_suppress_unlock_until = 0.0
_last_random_ts = 0.0

_stage_cleanup_requested = False
_collect_sources_this_stage: set[str] = set()


def _route_swap_in_progress() -> bool:
    """Returns True while a route swap is in progress (tmp_old present)."""
    return os.path.exists(tmp_old)


def _load_json(path: str, label: str) -> dict:
    if not os.path.exists(path):
        log(f"⚠️ {os.path.basename(path)} missing → {label} disabled.")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        log(f"📦 {len(data)} {label} loaded from {os.path.basename(path)}.")
        return data
    except Exception as e:
        log(f"⚠️ Failed to load {os.path.basename(path)}: {e}")
        return {}


def _write_event(source_name: str, target_name: str, event_type: str) -> None:
    """Persist last item event (for debugging/overlay)."""
    try:
        ev = {
            "source": str(source_name),
            "target": str(target_name),
            "type": str(event_type),
            "timestamp": time.time(),
        }
        with open(events_path, "w", encoding="utf-8") as f:
            json.dump(ev, f)
    except Exception as e:
        log(f"⚠️ Failed to write item randomizer event: {e}")


def _remove_key_from_section(original_text: str, section_name: str, key_name: str) -> str:
    """Remove a key from a given INI section (full line)."""
    if not original_text:
        return original_text
    lines = original_text.splitlines()
    out = []
    in_section = False
    header = f"[{section_name}]"
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            in_section = stripped == header
            out.append(line)
            continue
        if in_section and "=" in stripped:
            k = stripped.split("=", 1)[0].strip()
            if k == key_name:
                # drop this line
                continue
        out.append(line)
    return "\n".join(out) + ("\n" if original_text.endswith("\n") else "")


def _multi_smart_write(path: str, text: str, was_encrypted: bool, attempts: int = 3, delay: float = 0.02) -> None:
    """Write same content multiple times to 'beat' game race conditions."""
    for i in range(max(1, attempts)):
        smart_write(path, text, was_encrypted)
        if i + 1 < attempts and delay > 0:
            time.sleep(delay)


def _save_stage_sources() -> None:
    """Persist current stage source items for the state_exporter."""
    try:
        data = sorted(_collect_sources_this_stage)
        with open(stage_sources_path, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception as e:
        log(f"⚠️ Failed to write stage sources: {e}")


def _clear_stage_sources_file() -> None:
    """Clear the stage sources file."""
    try:
        if os.path.exists(stage_sources_path):
            with open(stage_sources_path, "w", encoding="utf-8") as f:
                json.dump([], f)
    except Exception:
        # Not critical
        pass


def _can_randomize_event() -> bool:
    """Simple cooldown gate for collectable/unlockable events."""
    global _last_random_ts
    now = time.time()
    if now - _last_random_ts < cooldown_sec:
        return False
    _last_random_ts = now
    return True


def suppress_unlock_randomizer_for(seconds: float = 1.0):
    """Called from other systems (z. B. Character Randomizer) to temporarily suppress unlock-randomization."""
    global _suppress_unlock_until
    try:
        secs = float(seconds)
    except Exception:
        secs = 1.0
    now = time.time()
    until = now + max(0.0, secs)
    if until > _suppress_unlock_until:
        _suppress_unlock_until = until


def notify_stage_transition():
    """Called from rando_script when a stage transition has completed."""
    global _stage_cleanup_requested
    _stage_cleanup_requested = True


def monitor_items(stop_event, enable_popups: bool = False):
    """Main item randomizer loop, runs in its own thread."""
    global _stage_cleanup_requested

    savefile_path = save_enc
    license_path = os.path.join(iwbtb_folder, "onlineLicense.ini")

    # Load pools
    items_raw = _load_json(items_path, "items")
    chars_raw = _load_json(characters_path, "characters")

    # Lowercase maps (for robust matching)
    items_by_lower = {name.lower(): name for name in items_raw.keys()}
    chars_by_lower = {name.lower(): name for name in chars_raw.keys()}

    # Combined canonical target pool
    all_targets = list(dict.fromkeys(list(items_raw.keys()) + list(chars_raw.keys())))
    if not all_targets:
        log("⚠️ No item/character pool found for item randomizer.")
        return

    is_char_lower = {name.lower() for name in chars_raw.keys()}
    blacklist_lower = {name.lower() for name in BLACKLIST_NAMES}

    # Achievement key mapping (special cases)
    # Example: Collectable "Awesomesauce" => Achievement "AwesomeSauce"
    achievement_key_map = {
        "Awesomesauce": "AwesomeSauce",
    }
    achievement_key_by_lower = {k.lower(): v for k, v in achievement_key_map.items()}

    last_collect: dict[str, str] = {}
    last_unlock: dict[str, str] = {}
    used_names: set[str] = set()
    first_loop = True

    log(
        f"🔄 Item randomizer initialized "
        f"(items={len(items_raw)}, chars={len(chars_raw)}, pool={len(all_targets)})."
    )

    # Restore used_names for avoid_repeats
    try:
        if os.path.exists(item_randomizer_state_path):
            with open(item_randomizer_state_path, "r", encoding="utf-8") as f:
                st = json.load(f)
            if isinstance(st, dict):
                restored = st.get("used_names") or []
                for n in restored:
                    if n in all_targets:
                        used_names.add(str(n))
                if used_names:
                    log(f"💾 Restored {len(used_names)} used names from state.")
    except Exception as e:
        log(f"⚠️ Failed to restore item randomizer state: {e}")

    # Clear stage sources file at start
    _collect_sources_this_stage.clear()
    _clear_stage_sources_file()

    pending_checks: list[dict] = []

    def schedule_verification(file_key: str, sections: dict[str, dict[str, str]]):
        if not sections:
            return
        pending_checks.append(
            {"time": time.time() + verify_delay_sec, "file": file_key, "sections": sections}
        )

    def process_pending_checks():
        if not pending_checks:
            return
        now = time.time()
        due = [c for c in pending_checks if c["time"] <= now]
        if not due:
            return
        remaining = [c for c in pending_checks if c["time"] > now]
        pending_checks[:] = remaining

        for check in due:
            file_key = check["file"]
            sections = check["sections"]
            path = savefile_path if file_key == "save" else license_path

            txt_cur, enc_cur = smart_read(path)
            if not txt_cur:
                log(f"⚠️ Verification: could not read {os.path.basename(path)}")
                continue

            data_cur = parse_ini(txt_cur)
            ok = True
            missing = []

            for sec_name, kvs in sections.items():
                sec = data_cur.get(sec_name.lower(), {}) or {}
                for k, expected in kvs.items():
                    cur_val = sec.get(k.lower(), None)
                    if cur_val != expected:
                        ok = False
                        missing.append((sec_name, k, expected, cur_val))

            if ok:
                log(f"✅ Verification OK for {file_key} ({os.path.basename(path)})")
                continue

            log(f"⚠️ Verification failed for {file_key} ({os.path.basename(path)}), rewriting:")
            for sec_name, k, expected, cur_val in missing:
                log(f"   {sec_name}.{k}: expected={expected!r}, found={cur_val!r}")

            new_txt = txt_cur
            for sec_name, kvs in sections.items():
                new_txt = apply_values_in_section(new_txt, sec_name, kvs)
            _multi_smart_write(path, new_txt, enc_cur)

    while not stop_event.is_set():
        try:
            # Während Route-Swap (tmp_old) nichts machen
            if _route_swap_in_progress():
                time.sleep(0.2)
                continue

            process_pending_checks()

            # Stage-Cleanup: Source-Items dieser Stage entfernen
            if _stage_cleanup_requested and _collect_sources_this_stage:
                txt_s, enc_s = smart_read(savefile_path)
                if txt_s:
                    txt_s2 = txt_s
                    for src_name in list(_collect_sources_this_stage):
                        txt_s2 = _remove_key_from_section(txt_s2, "Collectables", src_name)
                        txt_s2 = _remove_key_from_section(txt_s2, "Achievements", src_name)
                    _multi_smart_write(savefile_path, txt_s2, enc_s)
                    log(f"🧹 Stage cleanup removed {len(_collect_sources_this_stage)} source items.")
                _collect_sources_this_stage.clear()
                _stage_cleanup_requested = False
                _clear_stage_sources_file()

            if is_loading_overlay_active():
                time.sleep(poll_interval_sec)
                continue

            # --- SaveFile lesen ---
            txt, enc = smart_read(savefile_path)
            if not txt:
                time.sleep(poll_interval_sec)
                continue

            data = parse_ini(txt)
            positions = data.get("positions", {}) or {}
            col = data.get("collectables", {}) or {}

            # Erster Loop: nur Baseline für last_collect / last_unlock aufbauen
            if first_loop:
                last_collect.clear()
                for k_lower, v in col.items():
                    last_collect[k_lower] = v

                txt2_init, _ = smart_read(license_path)
                if txt2_init:
                    data2_init = parse_ini(txt2_init)
                    unl_init = data2_init.get("unlockables", {}) or {}
                    last_unlock.clear()
                    for k_lower, v in unl_init.items():
                        last_unlock[k_lower] = v

                first_loop = False
                time.sleep(poll_interval_sec)
                continue

            # Kein aktiver Run → nichts tun, aber States updaten
            if not positions:
                for k_lower, v in col.items():
                    last_collect[k_lower] = v

                txt_idle, _ = smart_read(license_path)
                if txt_idle:
                    data_idle = parse_ini(txt_idle)
                    unl_idle = data_idle.get("unlockables", {}) or {}
                    for k_lower, v in unl_idle.items():
                        last_unlock[k_lower] = v

                time.sleep(poll_interval_sec)
                continue

            changes_collect: dict[str, str] = {}
            changes_achievements: dict[str, str] = {}
            unlock_to_write: str | None = None

            # --- Collectable-Pickups aus SaveFile1 ---
            for k_lower, v in col.items():
                old = last_collect.get(k_lower, "0")
                last_collect[k_lower] = v

                if k_lower in blacklist_lower:
                    continue

                if old == "0" and v == "1":
                    # Neues Collectable eingesammelt
                    if not _can_randomize_event():
                        log(
                            f"⏱️ Extra collectable '{k_lower}' innerhalb "
                            f"{cooldown_sec:.1f}s cooldown – ignoriert."
                        )
                        continue

                    source_canonical = items_by_lower.get(k_lower, k_lower)

                    candidates = [
                        n
                        for n in all_targets
                        if n.lower() not in blacklist_lower
                        and (n not in used_names or not avoid_repeats)
                    ]
                    if not candidates:
                        used_names.clear()
                        candidates = [n for n in all_targets if n.lower() not in blacklist_lower]

                    target = random.choice(candidates)
                    if avoid_repeats:
                        used_names.add(target)

                    # Für Stage-Cleanup + state_exporter merken
                    _collect_sources_this_stage.add(source_canonical)
                    _save_stage_sources()

                    if target.lower() in is_char_lower:
                        unlock_to_write = target
                        log(f"🎲 Collectable {source_canonical} → Character {target}")
                        _write_event(source_canonical, target, "collectable_to_char")
                    else:
                        ach_key = achievement_key_by_lower.get(target.lower(), target)
                        changes_collect[target] = "1"
                        changes_achievements[ach_key] = "1"
                        log(f"🎲 Collectable {source_canonical} → Item {target}")
                        _write_event(source_canonical, target, "collectable_to_item")

            if changes_collect or changes_achievements:
                new_txt = txt
                if changes_collect:
                    new_txt = apply_values_in_section(new_txt, "Collectables", changes_collect)
                if changes_achievements:
                    new_txt = apply_values_in_section(new_txt, "Achievements", changes_achievements)
                _multi_smart_write(savefile_path, new_txt, enc)
                schedule_verification(
                    "save",
                    {"Collectables": changes_collect, "Achievements": changes_achievements},
                )

            # Pending Character aus Collectable → Unlockables schreiben
            if unlock_to_write:
                txt2w, enc2w = smart_read(license_path)
                if txt2w is None:
                    txt2w, enc2w = "[Unlockables]\n", False
                new_txt2w = apply_values_in_section(
                    txt2w,
                    "Unlockables",
                    {unlock_to_write: "1"},
                )
                _multi_smart_write(license_path, new_txt2w, enc2w)
                schedule_verification("license", {"Unlockables": {unlock_to_write: "1"}})

            # --- Unlockable-Pickups aus onlineLicense ---
            txt2, enc2 = smart_read(license_path)
            if txt2:
                data2 = parse_ini(txt2)
                unl = data2.get("unlockables", {}) or {}
                changes_unlock: dict[str, str] = {}
                collect_to_write: str | None = None
                keys_to_delete_unlock: set[str] = set()
                suppress_unlocks = time.time() < _suppress_unlock_until

                for k_lower, v in unl.items():
                    old = last_unlock.get(k_lower, "0")
                    last_unlock[k_lower] = v

                    if suppress_unlocks:
                        continue
                    if k_lower in blacklist_lower:
                        continue

                    if old == "0" and v == "1":
                        if not _can_randomize_event():
                            log(
                                f"⏱️ Extra unlockable '{k_lower}' innerhalb "
                                f"{cooldown_sec:.1f}s cooldown – ignoriert."
                            )
                            continue

                        source_canonical = chars_by_lower.get(k_lower, k_lower)

                        candidates = [
                            n
                            for n in all_targets
                            if n.lower() not in blacklist_lower
                            and (n not in used_names or not avoid_repeats)
                        ]
                        if not candidates:
                            used_names.clear()
                            candidates = [
                                n for n in all_targets if n.lower() not in blacklist_lower
                            ]

                        target = random.choice(candidates)
                        if avoid_repeats:
                            used_names.add(target)

                        # Ursprüngliches Unlockable komplett entfernen
                        keys_to_delete_unlock.add(source_canonical)

                        if target.lower() in is_char_lower:
                            changes_unlock[target] = "1"
                            log(f"🎲 Unlockable {source_canonical} → Character {target}")
                            _write_event(source_canonical, target, "unlockable_to_char")
                        else:
                            collect_to_write = target
                            log(f"🎲 Unlockable {source_canonical} → Item {target}")
                            _write_event(source_canonical, target, "unlockable_to_item")

                if keys_to_delete_unlock or changes_unlock:
                    new_txt2 = txt2
                    for dk in keys_to_delete_unlock:
                        new_txt2 = _remove_key_from_section(new_txt2, "Unlockables", dk)
                    if changes_unlock:
                        new_txt2 = apply_values_in_section(
                            new_txt2,
                            "Unlockables",
                            changes_unlock,
                        )
                    _multi_smart_write(license_path, new_txt2, enc2)
                    if changes_unlock:
                        schedule_verification("license", {"Unlockables": changes_unlock})

                if collect_to_write:
                    txtw, encw = smart_read(savefile_path)
                    if txtw is None:
                        txtw, encw = "[Collectables]\n", False
                    new_txtw = apply_values_in_section(
                        txtw,
                        "Collectables",
                        {collect_to_write: "1"},
                    )
                    ach_key = achievement_key_by_lower.get(collect_to_write.lower(), collect_to_write)
                    new_txtw = apply_values_in_section(
                        new_txtw,
                        "Achievements",
                        {ach_key: "1"},
                    )
                    _multi_smart_write(savefile_path, new_txtw, encw)
                    schedule_verification(
                        "save",
                        {
                            "Collectables": {collect_to_write: "1"},
                            "Achievements": {ach_key: "1"},
                        },
                    )

            # used_names sichern
            try:
                state = {"used_names": sorted(used_names)}
                with open(item_randomizer_state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f)
            except Exception as e:
                log(f"⚠️ Failed to persist item randomizer state: {e}")

            time.sleep(poll_interval_sec)

        except Exception as e:
            log(f"⚠️ Item randomizer loop error: {e}")
            time.sleep(0.5)

    log("🛑 Item randomizer stopped.")
