from __future__ import annotations
import os
import json
import random
import threading
import time

from PY.logger import log
from PY.config import iwbtb_folder, ini_folder, save_enc
from PY.loading_overlay import is_loading_overlay_active

from PY.file_utils import smart_read, smart_write
from PY.ini_utils import parse_ini, apply_values_in_section

items_path = os.path.join(ini_folder, "items.json")
characters_path = os.path.join(ini_folder, "characters.json")

TMP_OLD = os.path.join(iwbtb_folder, "_old_plain.ini")
TMP_NEW = os.path.join(iwbtb_folder, "_new_plain.ini")

POLL_INTERVAL_SEC = 0.30
AVOID_REPEATS = True

BLACKLIST_SOURCES = {"Awesomesauce", "Dark Boshy"}
BLACKLIST_NAMES = BLACKLIST_SOURCES

EVENTS_PATH = os.path.join(ini_folder, "item_randomizer_events.json")


def _route_swap_in_progress():
    return os.path.exists(TMP_OLD)


def _load_json(path, label):
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


def _write_event(source_name, target_name, event_type):
    try:
        ev = {
            "source": str(source_name),
            "target": str(target_name),
            "type": str(event_type),
            "timestamp": time.time(),
        }
        with open(EVENTS_PATH, "w", encoding="utf-8") as f:
            json.dump(ev, f)
    except Exception as e:
        log(f"⚠️ Failed to write item randomizer event: {e}")


def monitor_items(stop_event, enable_popups=False):
    savefile_path = save_enc
    license_path = os.path.join(iwbtb_folder, "onlineLicense.ini")

    items_pool = _load_json(items_path, "items")
    chars_pool = _load_json(characters_path, "characters")

    all_pool = list(
        dict.fromkeys(list(items_pool.keys()) + list(chars_pool.keys()))
    )

    if not all_pool:
        log("⚠️ No item/character pool found.")
        return

    is_char = {name: True for name in chars_pool.keys()}

    last_collect = {}
    last_unlock = {}
    used_names = set()
    first_loop = True

    log(f"🔄 Item randomizer initialized (pool size: {len(all_pool)}).")

    while not stop_event.is_set():
        try:
            if _route_swap_in_progress():
                time.sleep(0.2)
                continue

            if is_loading_overlay_active():
                time.sleep(POLL_INTERVAL_SEC)
                continue

            txt, enc = smart_read(savefile_path)
            positions = {}
            if txt:
                data = parse_ini(txt)
                positions = data.get("positions", {}) or {}
                col = data.get("collectables", {}) or {}

                if not positions:
                    for k, v in col.items():
                        last_collect[k] = v

                    txt_idle, enc_idle = smart_read(license_path)
                    if txt_idle:
                        data_idle = parse_ini(txt_idle)
                        unl_idle = data_idle.get("unlockables", {}) or {}
                        for k, v in unl_idle.items():
                            last_unlock[k] = v

                    time.sleep(POLL_INTERVAL_SEC)
                    continue

                changes_collect = {}
                unlock_to_write = None

                for k, v in col.items():
                    old = last_collect.get(k, "0")
                    last_collect[k] = v

                    if k in BLACKLIST_NAMES:
                        continue

                    if first_loop:
                        continue

                    if old == "0" and v == "1":
                        candidates = [
                            n
                            for n in all_pool
                            if n not in BLACKLIST_NAMES
                            and (n not in used_names or not AVOID_REPEATS)
                        ]
                        if not candidates:
                            used_names.clear()
                            candidates = [
                                n for n in all_pool if n not in BLACKLIST_NAMES
                            ]

                        target = random.choice(candidates)
                        if AVOID_REPEATS:
                            used_names.add(target)

                        if is_char.get(target, False):
                            unlock_to_write = target
                            log(f"🎲 Collectable {k} → Character {target}")
                            _write_event(k, target, "collectable_to_char")
                        else:
                            changes_collect[target] = "1"
                            log(f"🎲 Collectable {k} → Item {target}")
                            _write_event(k, target, "collectable_to_item")

                if changes_collect:
                    new_txt = apply_values_in_section(
                        txt,
                        "Collectables",
                        changes_collect,
                    )
                    smart_write(savefile_path, new_txt, enc)

                if unlock_to_write:
                    txt2w, enc2w = smart_read(license_path)
                    if txt2w is None:
                        txt2w, enc2w = "[Unlockables]\n", False
                    new_txt2w = apply_values_in_section(
                        txt2w,
                        "Unlockables",
                        {unlock_to_write: "1"},
                    )
                    smart_write(license_path, new_txt2w, enc2w)

            txt2, enc2 = smart_read(license_path)
            if txt2:
                data2 = parse_ini(txt2)
                unl = data2.get("unlockables", {}) or {}
                changes_unlock = {}
                collect_to_write = None

                for k, v in unl.items():
                    old = last_unlock.get(k, "0")
                    last_unlock[k] = v

                    if k in BLACKLIST_NAMES:
                        continue

                    if first_loop:
                        continue

                    if old == "0" and v == "1":
                        candidates = [
                            n
                            for n in all_pool
                            if n not in BLACKLIST_NAMES
                            and (n not in used_names or not AVOID_REPEATS)
                        ]
                        if not candidates:
                            used_names.clear()
                            candidates = [
                                n for n in all_pool if n not in BLACKLIST_NAMES
                            ]

                        target = random.choice(candidates)
                        if AVOID_REPEATS:
                            used_names.add(target)

                        if is_char.get(target, False):
                            changes_unlock[target] = "1"
                            log(f"🎲 Unlockable {k} → Character {target}")
                            _write_event(k, target, "unlockable_to_char")
                        else:
                            collect_to_write = target
                            log(f"🎲 Unlockable {k} → Item {target}")
                            _write_event(k, target, "unlockable_to_item")

                if changes_unlock:
                    new_txt2 = apply_values_in_section(
                        txt2,
                        "Unlockables",
                        changes_unlock,
                    )
                    smart_write(license_path, new_txt2, enc2)

                if collect_to_write:
                    txtw, encw = smart_read(savefile_path)
                    if txtw is None:
                        txtw, encw = "[Collectables]\n", False
                    new_txtw = apply_values_in_section(
                        txtw,
                        "Collectables",
                        {collect_to_write: "1"},
                    )
                    smart_write(savefile_path, new_txtw, encw)

            first_loop = False

            time.sleep(POLL_INTERVAL_SEC)
        except Exception as e:
            log(f"⚠️ Item randomizer loop error: {e}")
            time.sleep(0.5)

    log("🛑 Item randomizer stopped.")
