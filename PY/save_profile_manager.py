from __future__ import annotations
import os
import json
from typing import Dict, List
try:
    from PY.config import ini_folder, iwbtb_folder, rc4_key
except ModuleNotFoundError:
    from config import ini_folder, iwbtb_folder, rc4_key
try:
    from PY.rc4_utils import encrypt_save
except ModuleNotFoundError:
    from rc4_utils import encrypt_save
try:
    from PY.logger import log
except ModuleNotFoundError:
    from logger import log
try:
    from PY.save_utils import mark_last_writer, audit_save, mirror_plain_for_tracker
except ModuleNotFoundError:
    try:
        from save_utils import mark_last_writer, audit_save, mirror_plain_for_tracker
    except ModuleNotFoundError:
        def mark_last_writer(tag: str, details: dict | None = None) -> None:
            pass
        def audit_save(reason: str, force: bool = False) -> None:
            pass
        def mirror_plain_for_tracker() -> None:
            pass
SAVE_PROFILES_JSON = os.path.join(ini_folder, "save_profiles.json")
SAVE_PATHS = {
    "SaveFile1": os.path.join(iwbtb_folder, "SaveFile1.ini"),
    "SaveFile2": os.path.join(iwbtb_folder, "SaveFile2.ini"),
    "SaveFile3": os.path.join(iwbtb_folder, "SaveFile3.ini"),
    "onlineLicense": os.path.join(iwbtb_folder, "onlineLicense.ini"),
}
def _load_profiles() -> Dict[str, List[str]]:
\
\
\
    if not os.path.exists(SAVE_PROFILES_JSON):
        raise FileNotFoundError(f"save_profiles.json not found at {SAVE_PROFILES_JSON}")
    with open(SAVE_PROFILES_JSON, "r", encoding="utf-8") as f:
        raw = json.load(f)
    profiles: Dict[str, List[str]] = {}
    for name, obj in raw.items():
        if isinstance(obj, dict) and "content" in obj and isinstance(obj["content"], list):
            profiles[name] = [str(line) for line in obj["content"]]
        else:
            raise ValueError(f"Invalid profile format for '{name}' in save_profiles.json")
    return profiles
def _lines_to_text(lines: List[str]) -> str:
\
\
\
\
    return "\r\n".join(lines)
def _write_single_profile(name: str, lines: List[str], path: str) -> None:
\
\
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = _lines_to_text(lines)
    encrypt_save(text, path, rc4_key)
    log(f"[save_profile_manager] wrote {name} -> {path}")
def write_all_saves_from_profiles(tag: str = "init") -> None:
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
        profiles = _load_profiles()
    except Exception as e:
        log(f"⚠️ [save_profile_manager] Failed to load profiles: {e}")
        return
    if "SaveFile1" in profiles:
        try:
            _write_single_profile("SaveFile1", profiles["SaveFile1"], SAVE_PATHS["SaveFile1"])
        except Exception as e:
            log(f"⚠️ [save_profile_manager] Failed to write SaveFile1: {e}")
    else:
        log("⚠️ [save_profile_manager] Profile 'SaveFile1' missing in save_profiles.json")
    if "SaveFile2" in profiles:
        for logical_name in ("SaveFile2", "SaveFile3"):
            try:
                _write_single_profile(logical_name, profiles["SaveFile2"], SAVE_PATHS[logical_name])
            except Exception as e:
                log(f"⚠️ [save_profile_manager] Failed to write {logical_name}: {e}")
    else:
        log("⚠️ [save_profile_manager] Profile 'SaveFile2' missing (used for SaveFile2 & SaveFile3)")
    if "onlineLicense" in profiles:
        try:
            _write_single_profile("onlineLicense", profiles["onlineLicense"], SAVE_PATHS["onlineLicense"])
        except Exception as e:
            log(f"⚠️ [save_profile_manager] Failed to write onlineLicense: {e}")
    else:
        log("⚠️ [save_profile_manager] Profile 'onlineLicense' missing in save_profiles.json")
    try:
        mark_last_writer("save_profile_manager", {"tag": str(tag)})
    except Exception:
        pass
    try:
        audit_save(f"save_profile_manager:{tag}", force=True)
    except Exception:
        pass
    try:
        mirror_plain_for_tracker()
    except Exception:
        pass
