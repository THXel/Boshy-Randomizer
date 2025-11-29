import os, json, time
try:
    from PY.logger import log
except ModuleNotFoundError:
    from logger import log
try:
    from PY.config import positions_json, save_enc, rc4_key, ini_folder
except ModuleNotFoundError:
    from config import positions_json, save_enc, rc4_key, ini_folder
try:
    from PY.rc4_utils import decrypt_save
except ModuleNotFoundError:
    from rc4_utils import decrypt_save
try:
    from PY.save_utils import write_save_tagged
except ModuleNotFoundError:
    from save_utils import write_save_tagged

POS_DATA = None


def load_positions():
    global POS_DATA
    if POS_DATA is not None:
        return POS_DATA
    path = positions_json
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                _raw = json.load(f)
            rooms_dict = _raw.get("rooms") or _raw.get("Rooms") or {}
            bosses_dict = _raw.get("bosses") or _raw.get("Bosses") or {}
            POS_DATA = {
                "rooms": {str(k).lower(): v for k, v in rooms_dict.items()},
                "bosses": {str(k).lower(): v for k, v in bosses_dict.items()},
            }
            log(
                f"📄 positions.json loaded ({len(POS_DATA['rooms'])} Rooms, {len(POS_DATA['bosses'])} Bosses)."
            )
            return POS_DATA
        except Exception as e:
            log(f"⚠️ Failed to parse positions.json: {e}")
    else:
        log("⚠️ positions.json missing; stage transitions may fail.")
    return {"rooms": {}, "bosses": {}}


def _wait_for_savefile_ready(timeout_s: float = 3.0, stable_s: float = 0.25) -> bool:
    t0 = time.time()
    last_size = None
    last_head = None
    last_change = time.time()

    while time.time() - t0 < timeout_s:
        try:
            if os.path.exists(save_enc):
                try:
                    with open(save_enc, "rb") as f:
                        head = f.read(128)
                except Exception:
                    head = b""
                sz = os.path.getsize(save_enc)

                if last_size is None:
                    last_size = sz
                    last_head = head
                    last_change = time.time()
                else:
                    if sz != last_size or head != last_head:
                        last_size = sz
                        last_head = head
                        last_change = time.time()
                    else:
                        if time.time() - last_change >= stable_s:
                            return True
        except Exception:
            pass

        time.sleep(0.05)

    return os.path.exists(save_enc)


def apply_positions_to_save(stage_name: str, POS_DATA):
    try:
        key = (stage_name or "").lower()
        if key.startswith("save"):
            data = POS_DATA.get("rooms", {}).get(key)
        else:
            data = POS_DATA.get("bosses", {}).get(key)
        if not data:
            log(f"⚠️ No position entry found for {stage_name} in positions.json.")
            return False
        if not _wait_for_savefile_ready(timeout_s=3.0, stable_s=0.25):
            log(
                f"⚠️ Save file not ready for {stage_name} (timeout) – skipping positions update."
            )
            return False
        plaintext = decrypt_save(save_enc, rc4_key)
        if "[Stats]" not in plaintext or "TimeSeconds" not in plaintext:
            log(
                f"⚠️ Decrypted save for {stage_name} looks invalid (missing Stats/TimeSeconds) – skipping positions update."
            )
            return False
        lines = plaintext.splitlines()
        out = []
        in_positions = False
        for ln in lines:
            s = ln.strip()
            if s.startswith("[") and s.endswith("]"):
                in_positions = s.lower() == "[positions]"
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
