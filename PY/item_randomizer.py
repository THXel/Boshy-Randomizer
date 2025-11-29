from __future__ import annotations
import os
import json
import random
import time
from typing import Dict, Set, List

from PY.logger import log
from PY.config import iwbtb_folder, ini_folder, save_enc
from PY.loading_overlay import is_loading_overlay_active
from PY.file_utils import smart_read, smart_write
from PY.ini_utils import parse_ini, apply_values_in_section

ITEMS_PATH = os.path.join(ini_folder, "items.json")
CHARS_PATH = os.path.join(ini_folder, "characters.json")
STATE_PATH = os.path.join(ini_folder, "item_randomizer_state.json")
STAGE_SOURCES_PATH = os.path.join(ini_folder, "item_randomizer_stage_sources.json")
VIRTUAL_STATE_PATH = os.path.join(ini_folder, "item_randomizer_virtual.json")

POLL_INTERVAL = 0.30
COOLDOWN_SEC = 3.0
VERIFY_DELAY_SEC = 2.0
VERIFY_RETRIES = 3

BLACKLIST_SOURCES: Set[str] = {"Awesomesauce", "Dark Boshy"}

_last_event_ts: float = 0.0
_suppress_unlock_until: float = 0.0
_stage_sources: Set[str] = set()


def _route_swap_in_progress() -> bool:
    tmp_old = os.path.join(iwbtb_folder, "_old_plain.ini")
    return os.path.exists(tmp_old)


def _load_pool(path: str, label: str) -> Dict[str, dict]:
    if not os.path.exists(path):
        log(f"[item_randomizer] {label} file missing: {os.path.basename(path)}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            log(f"[item_randomizer] loaded {len(data)} {label} from {os.path.basename(path)}.")
            return data
    except Exception as e:
        log(f"[item_randomizer] failed to load {label}: {e}")
    return {}


def _multi_write(path: str, text: str, encrypted: bool, attempts: int = 3, delay: float = 0.02) -> None:
    for i in range(max(1, attempts)):
        smart_write(path, text, encrypted)
        if i + 1 < attempts and delay > 0:
            time.sleep(delay)


def _schedule_verification(
    pending: List[dict],
    file_key: str,
    sections: Dict[str, Dict[str, str]],
    retries: int = VERIFY_RETRIES,
) -> None:
    if not sections:
        return
    pending.append(
        {
            "time": time.time() + VERIFY_DELAY_SEC,
            "file": file_key,
            "sections": sections,
            "retries": int(retries),
        }
    )


def _process_verifications(pending: List[dict], savefile_path: str, license_path: str) -> None:
    """
    Only performs verification rewrites for the license file.
    SaveFile1.ini is never written here.
    """
    if not pending:
        return

    now = time.time()
    due = [c for c in pending if c.get("time", 0) <= now]
    if not due:
        return

    remaining = [c for c in pending if c.get("time", 0) > now]
    pending[:] = remaining

    for check in due:
        file_key = check.get("file")
        sections = check.get("sections") or {}
        retries = int(check.get("retries", 0))

        if not sections:
            continue

        if file_key != "license":
            # We never verify or rewrite the save file.
            continue

        path = license_path

        txt_cur, enc_cur = smart_read(path)
        if not txt_cur:
            log(f"[item_randomizer] verification: could not read {os.path.basename(path)}")
            if retries > 0:
                pending.append(
                    {
                        "time": time.time() + VERIFY_DELAY_SEC,
                        "file": file_key,
                        "sections": sections,
                        "retries": retries - 1,
                    }
                )
            continue

        data_cur = parse_ini(txt_cur)
        ok = True
        missing = []

        for sec_name, kvs in sections.items():
            sec = data_cur.get(sec_name.lower(), {}) or {}
            for k, expected in kvs.items():
                cur_val = sec.get(k, None)
                if cur_val != expected:
                    ok = False
                    missing.append((sec_name, k, expected, cur_val))

        if ok:
            log(f"[item_randomizer] ✅ verification OK for {file_key} ({os.path.basename(path)})")
            continue

        log(f"[item_randomizer] ⚠️ verification failed for {file_key} ({os.path.basename(path)}), rewriting:")
        for sec_name, k, expected, cur_val in missing:
            log(f"[item_randomizer]    {sec_name}.{k}: expected={expected!r}, found={cur_val!r}")

        new_txt = txt_cur
        for sec_name, kvs in sections.items():
            new_txt = apply_values_in_section(new_txt, sec_name, kvs)

        _multi_write(path, new_txt, enc_cur)

        if retries > 0:
            pending.append(
                {
                    "time": time.time() + VERIFY_DELAY_SEC,
                    "file": file_key,
                    "sections": sections,
                    "retries": retries - 1,
                }
            )
        else:
            log(f"[item_randomizer] ❌ verification retries exhausted for {file_key}.")


def _reset_virtual_state() -> None:
    try:
        state = {
            "version": 1,
            "run_started_at": time.time(),
            "events": [],
        }
        with open(VIRTUAL_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        log("[item_randomizer] virtual state reset.")
    except Exception as e:
        log(f"[item_randomizer] failed to reset virtual state: {e}")


def _append_virtual_reward(
    source_type: str,
    source_name: str,
    target_type: str,
    target_name: str,
) -> None:
    """
    Append a virtual reward entry to item_randomizer_virtual.json.
    """
    try:
        if os.path.exists(VIRTUAL_STATE_PATH):
            with open(VIRTUAL_STATE_PATH, "r", encoding="utf-8") as f:
                state = json.load(f)
            if not isinstance(state, dict):
                state = {}
        else:
            state = {}

        events = state.setdefault("events", [])
        events.append(
            {
                "time": time.time(),
                "source": {"type": source_type, "name": source_name},
                "target": {"type": target_type, "name": target_name},
            }
        )
        if "version" not in state:
            state["version"] = 1

        with open(VIRTUAL_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        log(
            f"[item_randomizer] virtual reward logged: "
            f"{source_type} '{source_name}' -> {target_type} '{target_name}'"
        )
    except Exception as e:
        log(f"[item_randomizer] failed to append virtual reward: {e}")


def suppress_unlock_randomizer_for(seconds: float = 1.0) -> None:
    global _suppress_unlock_until
    try:
        secs = float(seconds)
    except Exception:
        secs = 1.0
    now = time.time()
    until = now + max(0.0, secs)
    if until > _suppress_unlock_until:
        _suppress_unlock_until = until


def notify_stage_transition() -> None:
    global _stage_sources
    if not _stage_sources:
        return
    try:
        with open(STAGE_SOURCES_PATH, "w", encoding="utf-8") as f:
            json.dump(sorted(_stage_sources), f, indent=2)
        log(f"[item_randomizer] wrote {len(_stage_sources)} stage source items.")
    except Exception as e:
        log(f"[item_randomizer] failed to write stage sources: {e}")
    _stage_sources = set()


def _can_fire_event() -> bool:
    global _last_event_ts
    now = time.time()
    if now - _last_event_ts < COOLDOWN_SEC:
        return False
    _last_event_ts = now
    return True


def monitor_items(stop_event, enable_popups: bool = False) -> None:
    global _stage_sources

    savefile_path = save_enc
    license_path = os.path.join(iwbtb_folder, "onlineLicense.ini")

    items = _load_pool(ITEMS_PATH, "items")
    chars = _load_pool(CHARS_PATH, "characters")

    item_names = list(items.keys())
    char_names = list(chars.keys())
    if not item_names and not char_names:
        log("[item_randomizer] no items/characters loaded, aborting.")
        return

    _reset_virtual_state()

    all_targets = list(dict.fromkeys(item_names + char_names))
    blacklist_lower = {s.lower() for s in BLACKLIST_SOURCES}
    char_names_lower = {name.lower() for name in char_names}

    achievement_key_map = {
        "Awesomesauce": "AwesomeSauce",
    }
    achievement_key_by_lower = {k.lower(): v for k, v in achievement_key_map.items()}

    used_names: Set[str] = set()
    last_collect: Dict[str, str] = {}
    last_unlock: Dict[str, str] = {}
    first_loop = True
    pending_checks: List[dict] = []

    log(
        f"[item_randomizer] initialized (items={len(item_names)}, "
        f"chars={len(char_names)}, pool={len(all_targets)})."
    )

    # Restore used names from previous state file
    try:
        if os.path.exists(STATE_PATH):
            with open(STATE_PATH, "r", encoding="utf-8") as f:
                st = json.load(f)
            if isinstance(st, dict):
                restored = st.get("used_names") or []
                for n in restored:
                    if n in all_targets:
                        used_names.add(str(n))
                if used_names:
                    log(f"[item_randomizer] restored {len(used_names)} used names.")
    except Exception as e:
        log(f"[item_randomizer] failed to restore state: {e}")

    while not stop_event.is_set():
        try:
            if _route_swap_in_progress():
                time.sleep(0.2)
                continue

            _process_verifications(pending_checks, savefile_path, license_path)

            if is_loading_overlay_active():
                time.sleep(POLL_INTERVAL)
                continue

            # SaveFile1.ini is read-only here
            txt, enc = smart_read(savefile_path)
            if not txt:
                time.sleep(POLL_INTERVAL)
                continue

            data = parse_ini(txt)
            positions = data.get("positions", {}) or {}
            col = data.get("collectables", {}) or {}

            txt_lic, enc_lic = smart_read(license_path)
            lic_data = parse_ini(txt_lic) if txt_lic else {}
            unl = lic_data.get("unlockables", {}) or {}

            col_lower = {k.lower(): v for k, v in col.items()}
            unl_lower = {k.lower(): v for k, v in unl.items()}

            if first_loop:
                last_collect = dict(col_lower)
                last_unlock = dict(unl_lower)
                first_loop = False
                log(f"[item_randomizer] baseline collectables: {list(col.keys())}")
                log(f"[item_randomizer] baseline unlockables: {list(unl.keys())}")
                time.sleep(POLL_INTERVAL)
                continue

            if not positions:
                for k_l, v in col_lower.items():
                    last_collect[k_l] = v
                for k_l, v in unl_lower.items():
                    last_unlock[k_l] = v
                time.sleep(POLL_INTERVAL)
                continue

            # Collectables (only virtual)
            for k_l, v in col_lower.items():
                old = last_collect.get(k_l, "0")
                if old != v:
                    log(f"[item_randomizer] collectable change '{k_l}': {old} -> {v}")
                last_collect[k_l] = v

                if k_l in blacklist_lower:
                    continue

                if old == "0" and v == "1":
                    if not _can_fire_event():
                        log(
                            f"[item_randomizer] cooldown: collectable '{k_l}' "
                            f"ignored (cooldown {COOLDOWN_SEC:.1f}s)."
                        )
                        continue

                    source_canonical = None
                    for name in item_names:
                        if name.lower() == k_l:
                            source_canonical = name
                            break
                    if not source_canonical:
                        log(f"[item_randomizer] unknown collectable key '{k_l}', skipping.")
                        continue

                    _stage_sources.add(source_canonical)

                    candidates = [
                        n
                        for n in all_targets
                        if n.lower() not in blacklist_lower and n not in used_names
                    ]
                    if not candidates:
                        used_names.clear()
                        candidates = [
                            n for n in all_targets if n.lower() not in blacklist_lower
                        ]
                    target = random.choice(candidates)
                    used_names.add(target)

                    if target.lower() in char_names_lower:
                        target_type = "character"
                        log(
                            f"[item_randomizer] 🎲 collectable {source_canonical} "
                            f"-> virtual character {target}"
                        )
                    else:
                        target_type = "item"
                        ach_key = achievement_key_by_lower.get(target.lower(), target)
                        log(
                            f"[item_randomizer] 🎲 collectable {source_canonical} "
                            f"-> virtual item {ach_key}"
                        )

                    _append_virtual_reward(
                        source_type="collectable",
                        source_name=source_canonical,
                        target_type=target_type,
                        target_name=target,
                    )

            # Unlockables (characters only, real + virtual)
            changes_unlock: Dict[str, str] = {}
            suppress_unlocks = time.time() < _suppress_unlock_until

            for k_l, v in unl_lower.items():
                old = last_unlock.get(k_l, "0")
                if old != v:
                    log(f"[item_randomizer] unlockable change '{k_l}': {old} -> {v}")
                last_unlock[k_l] = v

                if suppress_unlocks:
                    continue
                if k_l in blacklist_lower:
                    continue
                if old == "0" and v == "1":
                    if not _can_fire_event():
                        log(
                            f"[item_randomizer] cooldown: unlockable '{k_l}' "
                            f"ignored (cooldown {COOLDOWN_SEC:.1f}s)."
                        )
                        continue

                    source_canonical = None
                    for name in char_names:
                        if name.lower() == k_l:
                            source_canonical = name
                            break
                    if not source_canonical:
                        log(f"[item_randomizer] unknown unlockable key '{k_l}', skipping.")
                        continue

                    candidates = [
                        n
                        for n in char_names
                        if n.lower() not in blacklist_lower and n not in used_names
                    ]
                    if not candidates:
                        used_names.clear()
                        candidates = [
                            n for n in char_names if n.lower() not in blacklist_lower
                        ]
                    target = random.choice(candidates)
                    used_names.add(target)

                    changes_unlock[target] = "1"
                    log(
                        f"[item_randomizer] 🎲 unlockable {source_canonical} "
                        f"-> character {target}"
                    )

                    _append_virtual_reward(
                        source_type="unlockable",
                        source_name=source_canonical,
                        target_type="character",
                        target_name=target,
                    )

            # Apply unlock changes to onlineLicense.ini only
            if changes_unlock:
                txt2u, enc2u = smart_read(license_path)
                if not txt2u:
                    txt2u, enc2u = "[Unlockables]\n", False

                new_txt2u = apply_values_in_section(
                    txt2u,
                    "Unlockables",
                    changes_unlock,
                )

                _multi_write(license_path, new_txt2u, enc2u)
                _schedule_verification(
                    pending_checks,
                    "license",
                    {"Unlockables": changes_unlock},
                )

            time.sleep(POLL_INTERVAL)

        except Exception as e:
            log(f"[item_randomizer] loop error: {e}")
            time.sleep(0.5)

    # Save used_names on exit
    try:
        state = {"used_names": sorted(used_names)}
        with open(STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        log(f"[item_randomizer] saved state with {len(used_names)} used names.")
    except Exception as e:
        log(f"[item_randomizer] failed to save state: {e}")
