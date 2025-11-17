# ======================================================
# trigger_engine.py
# Centralized trigger logic for Boshy Randomizer
#  - Pixel trigger acceptance (incl. tutorial/level gating)
#  - Trophy/Achievement trigger checks with min_value support
#  - Cooldown handling for Randomizer & item triggers
# Depends on:
#   - PY.logger.log
#   - PY.rc4_utils.decrypt_save, rc4_crypt
#   - PY.config: ini_folder, iwbtb_folder, save_enc, rc4_key, poll_interval
#   - Pixel regions checker: supplied via callable 'pixel_check_fn'
# ======================================================

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


# ---------------- Configuration flags (kept here to be the single source) ----
ALLOW_FIRST_PIXEL_TO_START = True            # allow first valid pixel to start the route
ACCEPT_PIXEL_WITHOUT_LEVEL = True            # accept pixel triggers with no level set
ENFORCE_TUTORIAL_FOR_FIRST_TRIGGER = True    # the very first pixel must be tutorial/global/None

# ---------------- Achievement trigger timing (local to trigger_engine) -------
# ACHIEVEMENT_STAGE_DELAY_S:
#   Zeit, die nach einem Achievement-Trigger gewartet wird,
#   bevor der Trigger nach außen als "True" zurückgegeben wird.
#   -> Dadurch wird der Stage-Wechsel im Hauptscript verzögert.
#
# ACHIEVEMENT_BLOCK_S:
#   Zeitfenster, in dem nach einem Achievement-Trigger
#   keine weiteren Achievement-Trigger akzeptiert werden.
#   -> Verhindert, dass zwei Achievements direkt hintereinander
#      zwei Stage-Wechsel auslösen.
ACHIEVEMENT_STAGE_DELAY_S: float = 2.0
ACHIEVEMENT_BLOCK_S: float = 5.0


def parse_ini_text(text: str) -> Dict[str, Dict[str, str]]:
    """Tiny INI reader sufficient for our save + onlineLicense format."""
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
        # Last fallback – try text mode
        try:
            with open(path, "r", encoding="latin-1", errors="ignore") as f:
                return parse_ini_text(f.read())
        except Exception:
            return {}


def _all_targets(trigger_targets: Dict[str, list]) -> List[str]:
    res = []
    for name, entries in (trigger_targets or {}).items():
        if isinstance(entries, list):
            res.append(name.lower())
    return res


def check_achievements_trigger(
    trigger_targets: Dict[str, list],
    state: Dict,
) -> Tuple[bool, Optional[str]]:
    """
    Looks at SaveFile1.ini (encrypted) and onlineLicense.ini (maybe RC4) and
    checks whether any keys in 'trigger_targets' have changed or met min_value.

    Returns (triggered, reason_text)
    Updates state['last_trophies'] snapshot.

    WICHTIG:
    - Es wird nur getriggert, wenn der KEY-NAME in trigger_targets steht
      (also in deiner triggers.json).
    - Die INI-Section (Achievements, Unlockables, Collectables, ...) ist egal.

    NEU:
    - Nach einem erfolgreichen Achievement-Trigger:
        * ACHIEVEMENT_STAGE_DELAY_S Sekunden warten (time.sleep),
          bevor (True, "achievement:<name>") zurückgegeben wird
          → verzögerter Stage-Wechsel im Hauptscript.
        * Weitere Achievement-Trigger werden für ACHIEVEMENT_BLOCK_S Sekunden
          geblockt (state["achievement_block_until"]).
    """
    try:
        now = time.time()
        combined: Dict[str, str] = {}

        # SaveFile1.ini
        if os.path.exists(save_enc):
            plain = decrypt_save(save_enc, rc4_key)
            ini_data = parse_ini_text(plain)
            for sec, kv in ini_data.items():
                for k, v in kv.items():
                    combined[f"{sec.lower()}::{k.lower()}"] = v

        # onlineLicense.ini
        lic_data = read_online_license_ini()
        for sec, kv in lic_data.items():
            for k, v in kv.items():
                combined[f"{sec.lower()}::{k.lower()}"] = v

        # First snapshot?
        if not state.get("last_trophies"):
            state["last_trophies"] = combined
            return (False, None)

        # Achievement-Block aktiv?
        block_until = state.get("achievement_block_until", 0.0)
        if block_until and now < block_until:
            # Snapshot trotzdem aktualisieren, damit wir nach dem Block
            # mit dem aktuellen Stand weitermachen können.
            state["last_trophies"] = combined
            remaining = block_until - now
            if remaining > 0:
                log(
                    f"⏳ Achievement triggers suppressed for another "
                    f"{remaining:.1f}s."
                )
            return (False, None)

        # Compare with last snapshot
        last = state.get("last_trophies", {})
        for key, val in combined.items():
            old_val = last.get(key)
            sec, name = key.split("::", 1)
            # sec_l = sec.lower()   # Section wird absichtlich NICHT mehr hart verglichen
            name_l = name.lower()

            # Nur Keys, die in triggers.json vorkommen
            if name_l in trigger_targets:
                for entry in trigger_targets[name_l]:
                    # Section-Filter entfernt:
                    # entry_section = entry.get("section", "").lower()
                    # if entry_section and entry_section != sec_l:
                    #     continue

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

                    # Trigger, wenn sich der Wert geändert hat ODER min_value erreicht wurde
                    if val != old_val or meets_min:
                        if meets_min and val_int is not None:
                            log(
                                f"🏆 Triggered by {sec.capitalize()}: {name}={val_int} "
                                f"(meets min_value={min_v})"
                            )
                        else:
                            log(f"🏆 Triggered by {sec.capitalize()}: {name}")

                        # ⏳ 2s Verzögerung vor dem Level-Wechsel im Hauptscript
                        if ACHIEVEMENT_STAGE_DELAY_S > 0:
                            log(
                                f"⏳ Achievement trigger – delaying stage transition "
                                f"by {ACHIEVEMENT_STAGE_DELAY_S:.1f}s."
                            )
                            time.sleep(ACHIEVEMENT_STAGE_DELAY_S)

                        # Item-Cooldown (wie bisher, z.B. für Item-Rando)
                        state["item_cooldown_until"] = time.time() + 3.0

                        # 🚫 5s Block für weitere Achievement-Trigger
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
    """
    Wraps any pixel_detector.check_pixel_regions signature; enforces tutorial/level gating
    and first-pixel rules.

    Returns (triggered, reason, region, level)
    - reason is "first_pixel" for the very first accepted pixel (route start)
               or "pixel" for normal stage-change triggers.
    """
    p_trig, p_region, p_level = False, None, None
    try:
        # Compatible wrapper (dict, tuple etc.)
        res = None
        try:
            import inspect
            sig = inspect.signature(pixel_check_fn)
            if "current_stage" in sig.parameters:
                res = pixel_check_fn(pixel_regions, state, current_stage=current_stage)
            else:
                res = pixel_check_fn(pixel_regions, state)
        except TypeError:
            # Fallback: call with the old signature
            res = pixel_check_fn(pixel_regions, state)

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
            # Any other truthy value ⇒ triggered without region info
            p_trig = bool(res)

        if not p_trig:
            return (False, None, None, None)

        # 🔑 WICHTIG: Wenn kein Level explizit gesetzt ist,
        # aber die Region ein String ist → Regionname als Level verwenden.
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
        is_tutorial_like = (
            p_level is None
            or lvl_lower in ("", "none", "null", "global", "tutorial")
        )

        # 🔰 Erste Route-Aktivierung: nur Tutorial/Global
        if current_stage is None and ALLOW_FIRST_PIXEL_TO_START:
            if ENFORCE_TUTORIAL_FOR_FIRST_TRIGGER and not is_tutorial_like:
                log(
                    f"⛔ Ignored first pixel '{p_region}' (level={p_level}) "
                    "because tutorial phase enforces tutorial/global."
                )
                return (False, None, p_region, p_level)
            return (True, "first_pixel", p_region, p_level)

        # Levelnamen normalisieren (z.B. boss5.ini -> boss5ini)
        def _norm(name: Optional[str]) -> Optional[str]:
            if not name:
                return None
            s = str(name).lower()
            return "".join(ch for ch in s if ch.isalnum())

        cur_norm = _norm(current_stage)
        lvl_norm = _norm(lvl_lower)

        # ✅ Erlaubte Fälle:
        #  - keine Level-Angabe + global erlaubt
        #  - Tutorial/Global (immer)
        #  - Level entspricht der aktuellen Stage (normalisiert)
        if (
            (lvl_lower is None and ACCEPT_PIXEL_WITHOUT_LEVEL)
            or (lvl_lower in ("global", "tutorial", ""))
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
