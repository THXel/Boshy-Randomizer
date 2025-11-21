from __future__ import annotations
import os
import time
import json
import traceback
try:
    from PY.logger import log
except ModuleNotFoundError:
    from logger import log
try:
    from PY.config import ini_folder, iwbtb_folder, save_enc, rc4_key, poll_interval
except ModuleNotFoundError:
    from config import ini_folder, iwbtb_folder, save_enc, rc4_key, poll_interval
try:
    from PY.rc4_utils import rc4_crypt
except ModuleNotFoundError:
    from rc4_utils import rc4_crypt
STATE_JSON = os.path.join(ini_folder, "live_tracker_state.json")
SAVEFILE_PATH = save_enc
LICENSE_PATH = os.path.join(iwbtb_folder, "onlineLicense.ini")
def _smart_read_text(path: str):
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
        log(f"[state_exporter] smart_read_text failed for {os.path.basename(path)}: {e}")
        return None, False
def _parse_ini(text: str):
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
            data.setdefault(sec, {})[k] = v
    return data
def _build_state_snapshot():
    save_txt, _ = _smart_read_text(SAVEFILE_PATH)
    lic_txt, _ = _smart_read_text(LICENSE_PATH)
    if not save_txt and not lic_txt:
        return None
    save_sections = _parse_ini(save_txt or "")
    lic_sections = _parse_ini(lic_txt or "")
    state = {
        "meta": {
            "generated_at": time.time(),
            "source": "state_exporter.py",
        },
        "save": {
            "raw": save_txt or "",
            "sections": save_sections,
        },
        "license": {
            "raw": lic_txt or "",
            "sections": lic_sections,
        },
    }
    try:
        from PY.rando_script import state as rstate
        route_list = rstate.get("route_list", [])
        route_index = rstate.get("route_index", 0)
        state["route"] = {
            "list": route_list,
            "index": route_index,
            "total": len(route_list),
        }
    except Exception:
        pass
    return state
def _write_state(state: dict):
\
\
\
\
\
\
\
    os.makedirs(ini_folder, exist_ok=True)
    tmp = STATE_JSON + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    try:
        with open(tmp, "r", encoding="utf-8") as f:
            json.load(f)
    except Exception as e:
        log(f"[state_exporter] ❗ TMP JSON invalid, skipping write: {e}")
        return
    delay = 0.02
    for attempt in range(5):
        try:
            os.replace(tmp, STATE_JSON)
            return
        except PermissionError as e:
            log(
                f"[state_exporter] replace blocked (attempt {attempt+1}/5): {e}; "
                f"retrying in {delay:.3f}s"
            )
            time.sleep(delay)
            delay *= 2
    try:
        log("[state_exporter] ❗ Using fallback overwrite (non-atomic).")
        with open(STATE_JSON, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"[state_exporter] ❗ Fallback overwrite failed: {e}")
def main(loop: bool = True, interval: float | None = None):
\
\
\
\
    log("[state_exporter] started")
    if interval is None:
        try:
            interval = float(poll_interval)
        except Exception:
            interval = 0.2
    else:
        try:
            interval = float(interval)
        except Exception:
            interval = 1.0
    if interval <= 0:
        interval = 1.0
    while True:
        try:
            state = _build_state_snapshot()
            if state is not None:
                _write_state(state)
        except Exception as e:
            log(f"[state_exporter] error: {e}\n{traceback.format_exc()}")
        if not loop:
            break
        time.sleep(interval)
if __name__ == "__main__":
    main(loop=True)
