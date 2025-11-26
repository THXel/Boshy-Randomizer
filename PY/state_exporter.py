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
    from PY.config import ini_folder, iwbtb_folder, save_enc, poll_interval, rc4_key
except ModuleNotFoundError:
    from config import ini_folder, iwbtb_folder, save_enc, poll_interval, rc4_key

try:
    from PY.ini_utils import parse_ini
except ModuleNotFoundError:
    from ini_utils import parse_ini

try:
    from PY.rc4_utils import decrypt_save
except ModuleNotFoundError:
    from rc4_utils import decrypt_save


STATE_JSON = os.path.join(ini_folder, "live_tracker_state.json")
SAVEFILE_PATH = save_enc
LICENSE_PATH = os.path.join(iwbtb_folder, "onlineLicense.ini")


def _decrypt_or_none(path: str, label: str) -> str | None:
    try:
        return decrypt_save(path, rc4_key)
    except PermissionError as e:
        try:
            log(f"[state_exporter] PermissionError reading {label}: {e}")
        except Exception:
            pass
        time.sleep(1.0)
        return None
    except FileNotFoundError:
        return ""
    except Exception as e:
        try:
            log(f"[state_exporter] failed to decrypt {label}: {e}")
        except Exception:
            pass
        time.sleep(1.0)
        return None


def _build_state_snapshot() -> dict | None:
    save_txt = _decrypt_or_none(SAVEFILE_PATH, "save file")
    lic_txt = _decrypt_or_none(LICENSE_PATH, "onlineLicense")

    if save_txt is None and lic_txt is None:
        return None

    try:
        save_sections = parse_ini(save_txt or "")
    except Exception as e:
        try:
            log(f"[state_exporter] parse_ini(save) failed: {e}")
        except Exception:
            pass
        time.sleep(1.0)
        return None

    try:
        lic_sections = parse_ini(lic_txt or "")
    except Exception as e:
        try:
            log(f"[state_exporter] parse_ini(license) failed: {e}")
        except Exception:
            pass
        lic_sections = {}

    if save_txt and (not isinstance(save_sections, dict) or not save_sections):
        try:
            log(
                "[state_exporter] parsed save has no sections – "
                "likely mid-write or corrupted, skipping snapshot"
            )
        except Exception:
            pass
        time.sleep(1.0)
        return None

    state: dict = {
        "meta": {
            "generated_at": time.time(),
            "source": "state_exporter.py",
        },
        "save": {
            "raw": save_txt or "",
            "sections": save_sections if isinstance(save_sections, dict) else {},
        },
        "license": {
            "raw": lic_txt or "",
            "sections": lic_sections if isinstance(lic_sections, dict) else {},
        },
    }

    try:
        route_list = []
        route_index = 0

        try:
            import __main__ as main_mod

            rstate = getattr(main_mod, "state", None)
            if isinstance(rstate, dict):
                route_list = list(rstate.get("route_list", []) or [])
                route_index = int(rstate.get("route_index", 0) or 0)
        except Exception:
            rstate = None

        if not route_list:
            try:
                from PY.rando_script import state as rstate_mod
            except ModuleNotFoundError:
                from rando_script import state as rstate_mod

            route_list = list(rstate_mod.get("route_list", []) or [])
            route_index = int(rstate_mod.get("route_index", 0) or 0)

        state["route"] = {
            "list": route_list,
            "index": route_index,
            "total": len(route_list),
        }
    except Exception as e:
        try:
            log(f"[state_exporter] route export failed: {e}")
        except Exception:
            pass

    return state


def _write_state(state: dict) -> None:
    os.makedirs(ini_folder, exist_ok=True)
    tmp = STATE_JSON + ".tmp"

    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    try:
        with open(tmp, "r", encoding="utf-8") as f:
            json.load(f)
    except Exception as e:
        try:
            log(f"[state_exporter] TMP JSON invalid, skipping write: {e}")
        except Exception:
            pass
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass
        return

    delay = 0.02
    last_err: Exception | None = None
    max_attempts = 30

    for attempt in range(1, max_attempts + 1):
        try:
            os.replace(tmp, STATE_JSON)
            return
        except PermissionError as e:
            last_err = e
            if attempt == 1 or attempt % 5 == 0 or attempt == max_attempts:
                try:
                    log(
                        f"[state_exporter] replace blocked (attempt "
                        f"{attempt}/{max_attempts}): {e}; retrying in {delay:.3f}s"
                    )
                except Exception:
                    pass
            time.sleep(delay)
            if delay < 0.5:
                delay *= 1.5
        except Exception as e:
            last_err = e
            try:
                log(
                    f"[state_exporter] unexpected error on replace "
                    f"(attempt {attempt}/{max_attempts}): {e}"
                )
            except Exception:
                pass
            break

    try:
        try:
            log("[state_exporter] Using fallback overwrite (non-atomic).")
        except Exception:
            pass

        try:
            if os.path.exists(STATE_JSON):
                os.remove(STATE_JSON)
        except Exception as e_rm:
            try:
                log(f"[state_exporter] Failed to remove old state file: {e_rm}")
            except Exception:
                pass

        if os.path.exists(tmp):
            os.replace(tmp, STATE_JSON)
    except Exception as e:
        try:
            log(
                f"[state_exporter] Fallback overwrite failed: {e} "
                f"(last error={last_err})"
            )
        except Exception:
            pass
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def main(loop: bool = True, interval: float | None = None) -> None:
    try:
        log("[state_exporter] started")
    except Exception:
        pass

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
            try:
                log(f"[state_exporter] error: {e}\n{traceback.format_exc()}")
            except Exception:
                pass

        if not loop:
            break

        time.sleep(interval)


if __name__ == "__main__":
    main(loop=True)
