# ======================================================
# target_collect.py
# - Verwaltung von target_items.json
# - Auswahl zufälliger Target-Items aus items.json
# - Monitoring-Thread, der SaveFile1.ini + onlineLicense.ini
#   beobachtet und done_event setzt, sobald ALLE Targets = 1 sind
# ======================================================
from __future__ import annotations
import os
import json
import time
import random
from typing import List, Set

from PY.logger import log
from PY.config import ini_folder, iwbtb_folder, save_enc, rc4_key
from PY.rc4_utils import decrypt_save

TARGET_FILE = os.path.join(ini_folder, "target_items.json")
ITEMS_FILE = os.path.join(ini_folder, "items.json")
LICENSE_FILE = os.path.join(iwbtb_folder, "onlineLicense.ini")


# ------------------------------------------------------
# Helfer: INI-Parser (sehr simpel)
# ------------------------------------------------------
def _parse_ini_sections(plain: str) -> dict:
    data = {}
    sec = None
    for line in (plain or "").splitlines():
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


def _read_savefile_items() -> Set[str]:
    """
    Liest SaveFile1 (RC4) und gibt eine Menge von Item-Namen zurück,
    die in [Achievements] oder [Collectables] den Wert '1' haben.
    """
    names: Set[str] = set()
    try:
        plain = decrypt_save(save_enc, rc4_key)
    except Exception:
        return names

    data = _parse_ini_sections(plain)
    for sec_name in ("achievements", "collectables"):
        sec = data.get(sec_name, {})
        for k, v in sec.items():
            if str(v).strip() == "1":
                names.add(k.strip().lower())
    return names


def _read_license_items() -> Set[str]:
    """
    Liest onlineLicense.ini (RC4 oder Plain) und gibt eine Menge von
    Unlockable-Namen zurück, die in [Unlockables] den Wert '1' haben.
    """
    names: Set[str] = set()
    if not os.path.exists(LICENSE_FILE):
        return names

    try:
        # Erst versuchen wir RC4 → falls das fehlschlägt, plain lesen
        try:
            plain = decrypt_save(LICENSE_FILE, rc4_key)
        except Exception:
            with open(LICENSE_FILE, "r", encoding="latin-1", errors="ignore") as f:
                plain = f.read()
    except Exception:
        return names

    data = _parse_ini_sections(plain)
    sec = data.get("unlockables", {})
    for k, v in sec.items():
        if str(v).strip() == "1":
            names.add(k.strip().lower())
    return names


def _load_targets() -> List[str]:
    if not os.path.exists(TARGET_FILE):
        return []
    try:
        with open(TARGET_FILE, "r", encoding="utf-8") as f:
            js = json.load(f) or {}
        targets = js.get("targets") or []
        return [str(x) for x in targets]
    except Exception:
        return []


# ------------------------------------------------------
# Öffentliche API für rando_script
# ------------------------------------------------------
def _clear_target_file() -> None:
    """target_items.json leeren (Format, das der Live Tracker erwartet)."""
    try:
        os.makedirs(ini_folder, exist_ok=True)
        tmp = TARGET_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"targets": []}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, TARGET_FILE)
        log("🧹 target_items.json cleared.")
    except Exception as e:
        log(f"⚠️ Failed to clear target_items.json: {e}")


def _choose_targets(count: int) -> List[str]:
    """
    Wählt `count` zufällige Items aus items.json aus.
    items.json: {"Awesomesauce":1, "Orc":1, ...}
    → wir benutzen nur die Keys; ob SaveFile oder License ist egal,
      da der Monitor beide Dateien checkt.
    """
    try:
        if not os.path.exists(ITEMS_FILE):
            log("⚠️ items.json missing – cannot choose targets.")
            return []

        with open(ITEMS_FILE, "r", encoding="utf-8") as f:
            js = json.load(f) or {}

        all_items = list(js.keys())
        if not all_items:
            log("⚠️ items.json empty – cannot choose targets.")
            return []

        if count >= len(all_items):
            chosen = all_items[:]  # alle
        else:
            chosen = random.sample(all_items, count)

        log(f"🎯 Chosen target items: {', '.join(chosen)}")
        return chosen
    except Exception as e:
        log(f"⚠️ Failed to choose targets: {e}")
        return []


def _write_targets_file(targets: List[str]) -> None:
    """
    Schreibt die gewählten Targets nach target_items.json im Format:
    {"targets": ["Awesomesauce", "Orc", ...]}
    """
    try:
        os.makedirs(ini_folder, exist_ok=True)
        payload = {"targets": list(targets)}
        tmp = TARGET_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        os.replace(tmp, TARGET_FILE)
        log(f"📝 target_items.json written ({len(targets)} targets).")
    except Exception as e:
        log(f"⚠️ Failed to write target_items.json: {e}")


def _monitor_targets_thread(stop_event, done_event, poll_interval: float = 1.0):
    """
    Läuft im eigenen Thread.
    - Liest regelmäßig target_items.json
    - Prüft SaveFile1 + onlineLicense
    - Wenn ALLE Targets gefunden wurden → done_event.set()
    """
    try:
        log("👀 Target monitor thread started.")
        while not getattr(stop_event, "is_set", lambda: False)():
            if getattr(done_event, "is_set", lambda: False)():
                break

            targets = _load_targets()
            if not targets:
                # Noch nichts ausgewählt → kurz warten
                time.sleep(poll_interval)
                continue

            # Alles in lower-case vergleichen
            target_lc = [t.strip().lower() for t in targets]

            try:
                save_items = _read_savefile_items()
                lic_items = _read_license_items()
                all_collected = save_items | lic_items
            except Exception as e:
                log(f"⚠️ Target monitor read error: {e}")
                time.sleep(poll_interval)
                continue

            missing = [t for t in target_lc if t not in all_collected]
            if not missing:
                log("✅ All target items collected – Solgryn will be forced next.")
                try:
                    done_event.set()
                except Exception:
                    pass
                break

            time.sleep(poll_interval)
        log("👋 Target monitor thread stopped.")
    except Exception as e:
        log(f"⚠️ Target monitor crashed: {e}")
