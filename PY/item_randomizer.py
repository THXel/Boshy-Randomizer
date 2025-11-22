import os
import json
import random
import threading
import time

from PY.logger import log
from PY.config import iwbtb_folder, ini_folder, rc4_key, save_enc
from PY.rc4_utils import rc4_crypt, encrypt_save

items_path = os.path.join(ini_folder, "items.json")
characters_path = os.path.join(ini_folder, "characters.json")

TMP_OLD = os.path.join(iwbtb_folder, "_old_plain.ini")
TMP_NEW = os.path.join(iwbtb_folder, "_new_plain.ini")

POLL_INTERVAL_SEC = 0.30
AVOID_REPEATS = True

BLACKLIST_SOURCES = {"Awesomesauce", "Dark Boshy"}

EVENTS_PATH = os.path.join(ini_folder, "item_randomizer_events.json")


def _smart_read_text(path):
    if not os.path.exists(path):
        return None, False
    try:
        with open(path, "rb") as f:
            raw = f.read()
        sample = raw[:400]
        if b"[" in sample and b"=" in sample:
            return raw.decode("latin-1", errors="ignore"), False
        return rc4_crypt(rc4_key, raw).decode("latin-1", errors="ignore"), True
    except Exception as e:
        log(f"⚠️ smart_read_text failed for {os.path.basename(path)}: {e}")
        return None, False


def _smart_write_text(path, text, was_encrypted):
    try:
        if was_encrypted:
            encrypt_save(text, path, rc4_key)
        else:
            with open(path, "w", encoding="latin-1", errors="ignore") as f:
                f.write(text)
    except Exception as e:
        log(f"⚠️ smart_write_text failed for {os.path.basename(path)}: {e}")


def _parse_ini(text):
    data = {}
    sec = None
    for line in (text or "").splitlines():
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
    return data


def _apply_values_in_section(original_text, section_name, kv_updates):
    lines = (original_text or "").splitlines()
    out = []
    sec = None
    section_l = (section_name or "").lower()

    seen_keys = set()
    in_section = False
    inserted_new = False

    # Prüfen, ob Section überhaupt existiert
    has_section = any(
        (ln.strip().lower() == f"[{section_l}]") for ln in lines
    )

    for line in lines:
        s = line.strip()

        # Neuer Abschnitt beginnt
        if s.startswith("[") and s.endswith("]"):
            # Wenn wir gerade aus unserer Section rauslaufen und noch
            # neue Keys übrig sind → jetzt einfügen
            if in_section and not inserted_new:
                for k, v in kv_updates.items():
                    if k not in seen_keys:
                        out.append(f"{k}={v}")
                inserted_new = True

            sec = s.strip("[]").lower()
            in_section = (sec == section_l)
            out.append(line)
            continue

        # Key-Value innerhalb unserer Ziel-Section
        if "=" in s and in_section:
            k, v = [x.strip() for x in s.split("=", 1)]
            if k in kv_updates:
                out.append(f"{k}={kv_updates[k]}")
                seen_keys.add(k)
            else:
                out.append(line)
        else:
            out.append(line)

    # Fall 1: Section existierte nicht → neue Section ans Ende
    if not has_section:
        out.append(f"[{section_name}]")
        for k, v in kv_updates.items():
            out.append(f"{k}={v}")
        return "\n".join(out)

    # Fall 2: Section existiert, aber wir haben noch keine neuen Keys eingefügt
    # (z.B. wenn Section am Ende steht oder sie keine alten Keys hatte)
    if has_section and not inserted_new:
        for k, v in kv_updates.items():
            if k not in seen_keys:
                out.append(f"{k}={v}")

    return "\n".join(out)

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
    first_loop = True  # erste Runde: nur Zustand merken

    log(f"🔄 Item randomizer initialized (pool size: {len(all_pool)}).")

    while not stop_event.is_set():
        try:
            if _route_swap_in_progress():
                time.sleep(0.2)
                continue

            # ----- SaveFile1.ini (Collectables) -----
            txt, enc = _smart_read_text(savefile_path)
            if txt:
                data = _parse_ini(txt)
                col = data.get("collectables", {}) or {}
                changes_collect = {}
                unlock_to_write = None

                for k, v in col.items():
                    old = last_collect.get(k, "0")
                    last_collect[k] = v

                    # Blacklist: diese Quellen nie als Trigger verwenden
                    if k in BLACKLIST_NAMES:
                        continue

                    # erste Schleife: nur Zustand übernehmen, nichts randomizen
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

                        changes_collect[k] = "0"

                        if is_char.get(target, False):
                            unlock_to_write = target
                            log(
                                f"🎲 Collectable {k} → Character {target} (write in onlineLicense)"
                            )
                            _write_event(k, target, "collectable_to_char")
                        else:
                            changes_collect[target] = "1"
                            log(
                                f"🎲 Collectable {k} → Item {target} (write in SaveFile)"
                            )
                            _write_event(k, target, "collectable_to_item")

                if changes_collect:
                    new_txt = _apply_values_in_section(
                        txt,
                        "Collectables",
                        changes_collect,
                    )
                    _smart_write_text(savefile_path, new_txt, enc)

                if unlock_to_write:
                    txt2w, enc2w = _smart_read_text(license_path)
                    if txt2w is None:
                        txt2w, enc2w = "[Unlockables]\n", False
                    new_txt2w = _apply_values_in_section(
                        txt2w,
                        "Unlockables",
                        {unlock_to_write: "1"},
                    )
                    _smart_write_text(license_path, new_txt2w, enc2w)

            # ----- onlineLicense.ini (Unlockables) -----
            txt2, enc2 = _smart_read_text(license_path)
            if txt2:
                data2 = _parse_ini(txt2)
                unl = data2.get("unlockables", {}) or {}
                changes_unlock = {}
                collect_to_write = None

                for k, v in unl.items():
                    old = last_unlock.get(k, "0")
                    last_unlock[k] = v

                    # Blacklist: auch hier keine Trigger
                    if k in BLACKLIST_NAMES:
                        continue

                    # erste Schleife: nur Zustand übernehmen, nichts randomizen
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

                        changes_unlock[k] = "0"

                        if is_char.get(target, False):
                            changes_unlock[target] = "1"
                            log(
                                f"🎲 Unlockable {k} → Character {target} (write in onlineLicense)"
                            )
                            _write_event(k, target, "unlockable_to_char")
                        else:
                            collect_to_write = target
                            log(
                                f"🎲 Unlockable {k} → Item {target} (write in SaveFile)"
                            )
                            _write_event(k, target, "unlockable_to_item")

                if changes_unlock:
                    new_txt2 = _apply_values_in_section(
                        txt2,
                        "Unlockables",
                        changes_unlock,
                    )
                    _smart_write_text(license_path, new_txt2, enc2)

                if collect_to_write:
                    txtw, encw = _smart_read_text(savefile_path)
                    if txtw is None:
                        txtw, encw = "[Collectables]\n", False
                    new_txtw = _apply_values_in_section(
                        txtw,
                        "Collectables",
                        {collect_to_write: "1"},
                    )
                    _smart_write_text(savefile_path, new_txtw, encw)

            # ab jetzt dürfen echte Trigger feuern
            first_loop = False

            time.sleep(POLL_INTERVAL_SEC)
        except Exception as e:
            log(f"⚠️ Item randomizer loop error: {e}")
            time.sleep(0.5)

    log("🛑 Item randomizer stopped.")
