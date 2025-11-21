from __future__ import annotations
import os, time, json
from typing import Dict, Tuple, Optional, List, Callable
try:
    from PY.logger import log
except ModuleNotFoundError:
    from logger import log
try:
    from PY.rc4_utils import decrypt_save, rc4_crypt
except ModuleNotFoundError:
    from rc4_utils import decrypt_save, rc4_crypt
try:
    from PY.config import ini_folder, iwbtb_folder, save_enc, rc4_key, poll_interval
except ModuleNotFoundError:
    from config import ini_folder, iwbtb_folder, save_enc, rc4_key, poll_interval
ALLOW_FIRST_PIXEL_TO_START = True
ACCEPT_PIXEL_WITHOUT_LEVEL = True
ENFORCE_TUTORIAL_FOR_FIRST_TRIGGER = True
FAST_PIXEL_MODE = True
ACHIEVEMENT_STAGE_DELAY_S: float = 2.0
ACHIEVEMENT_BLOCK_S: float = 5.0
def parse_ini_text(text: str) -> Dict[str, Dict[str, str]]:
    data, sec = {}, None
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
def read_online_license_ini() -> Dict[str, Dict[str, str]]:
    path = os.path.join(iwbtb_folder, "onlineLicense.ini")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "rb") as f:
            raw = f.read()
        if not raw:
            return {}
    except Exception:
        return {}
    try:
        head = raw[:400]
        if b"[" in head and b"=" in head:
            txt = raw.decode("latin-1", errors="ignore")
        else:
            txt = rc4_crypt(rc4_key, raw).decode("latin-1", errors="ignore")
        return parse_ini_text(txt)
    except Exception:
        try:
            txt = rc4_crypt(rc4_key, raw).decode("latin-1", errors="ignore")
            return parse_ini_text(txt)
        except Exception:
            return {}
def _norm_stage(name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    s = str(name).lower()
    return "".join(ch for ch in s if ch.isalnum())
def _region_level(region: dict) -> Optional[str]:
\
\
\
    lvl = (
        region.get("level")
        or region.get("Level")
        or region.get("stage")
        or region.get("Stage")
        or region.get("Region")
    )
    return lvl
def _is_tutorial_like_level(lvl: Optional[str]) -> bool:
    if lvl is None:
        return True
    s = str(lvl).lower().strip()
    return s in ("", "none", "null", "tutorial", "global")
def _filter_pixel_regions_for_stage(pixel_regions, current_stage: Optional[str]):
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
    if not pixel_regions:
        return pixel_regions
    if current_stage is None:
        if ENFORCE_TUTORIAL_FOR_FIRST_TRIGGER:
            filtered = []
            for r in pixel_regions:
                lvl = _region_level(r)
                if _is_tutorial_like_level(lvl):
                    filtered.append(r)
            if filtered:
                return filtered
        return pixel_regions
    cur_norm = _norm_stage(current_stage)
    if not cur_norm:
        return pixel_regions
    filtered = []
    for r in pixel_regions:
        lvl = _region_level(r)
        lvl_norm = _norm_stage(lvl)
        if lvl is None or _is_tutorial_like_level(lvl):
            filtered.append(r)
        elif lvl_norm == cur_norm:
            filtered.append(r)
    return filtered or pixel_regions
def check_achievements_trigger(
    trigger_targets: Dict[str, list],
    state: Dict,
) -> Tuple[bool, Optional[str]]:
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
\
\
\
\
\
\
\
    try:
        now = time.time()
        combined: Dict[str, str] = {}
        if os.path.exists(save_enc):
            plain = decrypt_save(save_enc, rc4_key)
            ini_data = parse_ini_text(plain)
            for sec, kv in ini_data.items():
                for k, v in kv.items():
                    combined[f"{sec.lower()}::{k.lower()}"] = v
        lic_data = read_online_license_ini()
        for sec, kv in lic_data.items():
            for k, v in kv.items():
                combined[f"{sec.lower()}::{k.lower()}"] = v
        if not state.get("last_trophies"):
            state["last_trophies"] = combined
            return (False, None)
        block_until = state.get("achievement_block_until", 0.0)
        if block_until and now < block_until:
            state["last_trophies"] = combined
            remaining = block_until - now
            if remaining > 0:
                log(
                    f"⏳ Achievement triggers suppressed for another "
                    f"{remaining:.1f}s."
                )
            return (False, None)
        last = state.get("last_trophies", {})
        for key, val in combined.items():
            old_val = last.get(key)
            sec, name = key.split("::", 1)
            name_l = name.lower()
            if name_l in trigger_targets:
                for entry in trigger_targets[name_l]:
                    min_v = entry.get("min_value")
                    val_int: Optional[int] = None
                    try:
                        val_int = int(val)
                    except Exception:
                        val_int = None
                    meets_min = False
                    if min_v is not None and val_int is not None:
                        try:
                            if val_int >= int(min_v):
                                meets_min = True
                        except Exception:
                            pass
                    if val != old_val or meets_min:
                        if meets_min and val_int is not None:
                            log(
                                f"🏆 Triggered by {sec.capitalize()}: {name}={val_int} "
                                f"(meets min_value={min_v})"
                            )
                        else:
                            log(f"🏆 Triggered by {sec.capitalize()}: {name}")
                        if ACHIEVEMENT_STAGE_DELAY_S > 0:
                            log(
                                f"⏳ Achievement trigger – delaying stage transition "
                                f"by {ACHIEVEMENT_STAGE_DELAY_S:.1f}s."
                            )
                            time.sleep(ACHIEVEMENT_STAGE_DELAY_S)
                        state["item_cooldown_until"] = time.time() + 3.0
                        state["achievement_block_until"] = time.time() + ACHIEVEMENT_BLOCK_S
                        log(
                            f"🚫 Achievement trigger cooldown active for "
                            f"{ACHIEVEMENT_BLOCK_S:.1f}s."
                        )
                        state["last_trophies"] = combined
                        return (True, f"achievement:{name_l}")
        state["last_trophies"] = combined
        return (False, None)
    except Exception as e:
        log(f"⚠️ Achievement trigger check failed: {e}")
        return (False, None)
def check_pixel_trigger(
    pixel_check_fn: Callable,
    pixel_regions,
    state: Dict,
    current_stage: Optional[str],
    cooldown_until: float,
) -> Tuple[bool, Optional[str], Optional[str], Optional[str]]:
\
\
\
\
\
\
\
    p_trig, p_region, p_level = False, None, None
    try:
        if FAST_PIXEL_MODE:
            try:
                state["pixel_required_frames"] = 1
            except Exception:
                pass
        regions_for_check = _filter_pixel_regions_for_stage(pixel_regions, current_stage)
        res = None
        try:
            import inspect
            sig = inspect.signature(pixel_check_fn)
            if "current_stage" in sig.parameters:
                res = pixel_check_fn(regions_for_check, state, current_stage=current_stage)
            else:
                res = pixel_check_fn(regions_for_check, state)
        except TypeError:
            res = pixel_check_fn(regions_for_check, state)
        if isinstance(res, dict):
            p_trig = bool(res.get("triggered"))
            p_region = res.get("region")
            p_level = res.get("level")
        elif isinstance(res, (list, tuple)):
            if len(res) == 3:
                p_trig, p_region, p_level = res
            elif len(res) == 2:
                p_trig, p_region = res
                p_level = None
            elif len(res) == 1:
                p_trig = bool(res[0])
                p_region = None
                p_level = None
        else:
            p_trig = bool(res)
        if not p_trig:
            return (False, None, None, None)
        if p_level is None and isinstance(p_region, str):
            p_level = p_region
        now = time.time()
        if cooldown_until and cooldown_until > now:
            log(
                f"⏳ Pixel trigger '{p_region}' ({p_level or 'no-level'}) "
                f"suppressed – cooldown {cooldown_until - now:.1f}s left."
            )
            return (False, None, p_region, p_level)
        lvl_lower = (str(p_level).lower() if p_level is not None else None)
        is_tutorial_like = _is_tutorial_like_level(lvl_lower)
        if current_stage is None and ALLOW_FIRST_PIXEL_TO_START:
            if ENFORCE_TUTORIAL_FOR_FIRST_TRIGGER and not is_tutorial_like:
                log(
                    f"⛔ Ignored first pixel '{p_region}' (level={p_level}) "
                    "because tutorial phase enforces tutorial/global."
                )
                return (False, None, p_region, p_level)
            return (True, "first_pixel", p_region, p_level)
        cur_norm = _norm_stage(current_stage)
        lvl_norm = _norm_stage(lvl_lower)
        if (
            (lvl_lower is None and ACCEPT_PIXEL_WITHOUT_LEVEL)
            or _is_tutorial_like_level(lvl_lower)
            or (
                current_stage is not None
                and (
                    lvl_lower == str(current_stage).lower()
                    or (cur_norm and lvl_norm and cur_norm == lvl_norm)
                )
            )
        ):
            log(f"🔥 Pixel-Trigger accepted: {p_region} @ {p_level or 'no-level'}")
            return (True, "pixel", p_region, p_level)
        log(
            f"⛔ Ignored pixel '{p_region}' (level={p_level}) – "
            f"current stage is {current_stage or 'None'}"
        )
        return (False, None, p_region, p_level)
    except Exception as e:
        log(f"⚠️ Pixel trigger check failed: {e}")
        return (False, None, None, None)
