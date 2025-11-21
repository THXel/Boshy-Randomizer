from __future__ import annotations
import os
import json
import time
import random
from typing import List, Set, Optional
from PY.logger import log
from PY.config import ini_folder, iwbtb_folder, save_enc, rc4_key
from PY.rc4_utils import decrypt_save
TARGET_FILE = os.path.join(ini_folder, "target_items.json")
ITEMS_FILE = os.path.join(ini_folder, "items.json")
LICENSE_FILE = os.path.join(iwbtb_folder, "onlineLicense.ini")
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
\
\
\
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
\
\
\
    names: Set[str] = set()
    if not os.path.exists(LICENSE_FILE):
        return names
    try:
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
def _clear_target_file() -> None:
    try:
        os.makedirs(ini_folder, exist_ok=True)
        tmp = TARGET_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"targets": []}, f, ensure_ascii=False, indent=2)
        os.replace(tmp, TARGET_FILE)
        log("🧹 target_items.json cleared.")
    except Exception as e:
        log(f"⚠️ Failed to clear target_items.json: {e}")
def _choose_targets(count: int, seed: Optional[int] = None) -> List[str]:
\
\
\
\
\
\
\
\
\
\
\
\
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
            chosen = all_items[:]
        else:
            if seed is not None:
                rnd = random.Random(int(seed))
                items = list(all_items)
                rnd.shuffle(items)
                chosen = items[:count]
                log(f"🎯 Chosen target items (seed={seed}): {', '.join(chosen)}")
                return chosen
            else:
                chosen = random.sample(all_items, count)
        log(f"🎯 Chosen target items: {', '.join(chosen)}")
        return chosen
    except Exception as e:
        log(f"⚠️ Failed to choose targets: {e}")
        return []
def _write_targets_file(targets: List[str]) -> None:
\
\
\
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
\
\
\
\
\
    try:
        log("👀 Target monitor thread started.")
        while not getattr(stop_event, "is_set", lambda: False)():
            if getattr(done_event, "is_set", lambda: False)():
                break
            targets = _load_targets()
            if not targets:
                time.sleep(poll_interval)
                continue
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
