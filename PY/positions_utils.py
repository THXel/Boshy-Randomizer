import os
import json
import time

try:
    from PY.logger import log
except ModuleNotFoundError:
    from logger import log

try:
    from PY.config import positions_json, save_enc, ini_folder
except ModuleNotFoundError:
    from config import positions_json, save_enc, ini_folder

try:
    from PY.save_utils import write_save_tagged
except ModuleNotFoundError:
    from save_utils import write_save_tagged

try:
    from PY.file_utils import smart_read
except ModuleNotFoundError:
    from file_utils import smart_read


def load_positions():
    if os.path.exists(positions_json):
        try:
            with open(positions_json, "r", encoding="utf-8") as f:
                _raw = json.load(f)

            rooms_dict = _raw.get("rooms") or _raw.get("Rooms") or {}
            bosses_dict = _raw.get("bosses") or _raw.get("Bosses") or {}

            pos_data = {
                "rooms": {str(k).lower(): v for k, v in rooms_dict.items()},
                "bosses": {str(k).lower(): v for k, v in bosses_dict.items()},
            }

            log(
                f"📄 positions.json loaded "
                f"({len(pos_data['rooms'])} Rooms, {len(pos_data['bosses'])} Bosses)."
            )
            return pos_data
        except Exception as e:
            log(f"⚠️ Failed to parse positions.json: {e}")
    else:
        log("⚠️ positions.json missing; stage transitions may fail.")

    return {"rooms": {}, "bosses": {}}


def _wait_for_savefile_ready(timeout_s: float = 3.0) -> bool:
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            if os.path.exists(save_enc) and os.path.getsize(save_enc) >= 40:
                return True
        except Exception:
            pass
        time.sleep(0.05)
    return os.path.exists(save_enc)


def apply_positions_to_save(stage_name: str, pos_data) -> bool:
    try:
        key = (stage_name or "").lower()
        if key.startswith("save"):
            data = pos_data.get("rooms", {}).get(key)
        else:
            data = pos_data.get("bosses", {}).get(key)

        if not data:
            log(f"⚠️ No position entry found for {stage_name} in positions.json.")
            return False

        _wait_for_savefile_ready(timeout_s=3.0)

        plaintext, _ = smart_read(save_enc)
        if plaintext is None:
            log("⚠️ apply_positions_to_save: could not read save file.")
            return False

        lines = plaintext.splitlines()
        out = []
        in_positions = False

        for ln in lines:
            s = ln.strip()
            if s.startswith("[") and s.endswith("]"):
                in_positions = (s.lower() == "[positions]")
                if not in_positions:
                    out.append(ln)
                continue
            if in_positions:
                continue
            out.append(ln)

        if out and out[-1] and not out[-1].endswith("\n"):
            out[-1] = out[-1] + "\n"

        out.append("[Positions]")
        for k, v in data.items():
            out.append(f"{str(k).strip()}={str(v).strip()}")

        new_plain = "\n".join(out) + "\n"
        write_save_tagged("positions_replace", new_plain)
        log(f"📍 Updated [Positions] from {stage_name} (safe replace)")
        return True
    except Exception as e:
        log(f"⚠️ Failed to apply positions for {stage_name}: {e}")
        return False
