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

VIRTUAL_JSON = os.path.join(ini_folder, "item_randomizer_virtual.json")


# Mapping for odd achievement names (same logic as in item_randomizer)
ACHIEVEMENT_KEY_MAP = {
    "Awesomesauce": "AwesomeSauce",
}
# lowercase lookup
ACHIEVEMENT_KEY_MAP_LOWER = {
    k.lower(): v for k, v in ACHIEVEMENT_KEY_MAP.items()
}


def _load_virtual_state() -> dict:
    try:
        if not os.path.exists(VIRTUAL_JSON):
            return {}
        with open(VIRTUAL_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as e:
        try:
            log(f"[state_exporter] failed to load virtual item state: {e}")
        except Exception:
            pass
        return {}


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


def _deep_copy_sections(sections: dict | None) -> dict:
    if not isinstance(sections, dict):
        return {}
    out: dict[str, dict] = {}
    for sec_name, kv in sections.items():
        if isinstance(kv, dict):
            out[sec_name] = dict(kv)
        else:
            out[sec_name] = kv
    return out


def _remove_collectable_from_sections(
    save_sections: dict,
    source_name: str,
) -> None:
    src_l = source_name.lower()
    ach = save_sections.get("achievements") or {}
    col = save_sections.get("collectables") or {}

    keys_to_delete = []

    for k in ach.keys():
        k_l = k.lower()
        if k_l == src_l:
            keys_to_delete.append(k)
        else:
            mapped = ACHIEVEMENT_KEY_MAP_LOWER.get(src_l)
            if mapped and k == mapped:
                keys_to_delete.append(k)
    for k in keys_to_delete:
        ach.pop(k, None)

    keys_to_delete = []
    for k in col.keys():
        if k.lower() == src_l:
            keys_to_delete.append(k)
    for k in keys_to_delete:
        col.pop(k, None)

    save_sections["achievements"] = ach
    save_sections["collectables"] = col


def _add_item_to_sections(
    save_sections: dict,
    target_name: str,
) -> None:
    tgt_l = target_name.lower()
    ach = save_sections.setdefault("achievements", {})
    col = save_sections.setdefault("collectables", {})

    ach_key = ACHIEVEMENT_KEY_MAP_LOWER.get(tgt_l, target_name)
    if ach.get(ach_key, "0") != "1":
        ach[ach_key] = "1"

    if col.get(target_name, "0") != "1":
        col[target_name] = "1"


def _remove_unlockable_from_sections(
    lic_sections: dict,
    source_name: str,
) -> None:
    src_l = source_name.lower()
    unl = lic_sections.get("unlockables") or {}
    keys_to_delete = [k for k in unl.keys() if k.lower() == src_l]
    for k in keys_to_delete:
        unl.pop(k, None)
    lic_sections["unlockables"] = unl


def _add_character_to_sections(
    lic_sections: dict,
    target_name: str,
) -> None:
    unl = lic_sections.setdefault("unlockables", {})
    unl[target_name] = "1"


def _apply_virtual_rewards_to_sections(
    save_sections: dict,
    lic_sections: dict,
    virtual_state: dict,
) -> tuple[dict, dict]:
    save_v = _deep_copy_sections(save_sections)
    lic_v = _deep_copy_sections(lic_sections)

    events = virtual_state.get("events") or []
    if not isinstance(events, list):
        return save_v, lic_v

    for ev in events:
        if not isinstance(ev, dict):
            continue
        src = ev.get("source") or {}
        tgt = ev.get("target") or {}

        src_type = str(src.get("type", "")).strip().lower()
        src_name = str(src.get("name", "")).strip()
        tgt_type = str(tgt.get("type", "")).strip().lower()
        tgt_name = str(tgt.get("name", "")).strip()

        if not src_name or not tgt_name:
            continue

        # remove real source
        if src_type == "collectable":
            _remove_collectable_from_sections(save_v, src_name)
        elif src_type == "unlockable":
            _remove_unlockable_from_sections(lic_v, src_name)

        # add virtual target
        if tgt_type == "item":
            _add_item_to_sections(save_v, tgt_name)
        elif tgt_type == "character":
            _add_character_to_sections(lic_v, tgt_name)

    return save_v, lic_v


def _detect_route_and_item_flag() -> tuple[dict, bool]:
    route_list: list = []
    route_index = 0
    route_code: str | None = None
    item_rand_flag: int | None = None

    def _extract_route(rst: dict | None) -> None:
        nonlocal route_list, route_index, route_code, item_rand_flag
        if not isinstance(rst, dict):
            return
        try:
            route_list_local = list(rst.get("route_list", []) or [])
        except Exception:
            route_list_local = []
        if route_list_local:
            route_list = route_list_local
        try:
            route_index = int(rst.get("route_index", 0) or 0)
        except Exception:
            route_index = 0
        rc = rst.get("route_code")
        if isinstance(rc, str):
            route_code = rc
            try:
                parts = rc.split("-")
                for p in parts:
                    if p.startswith("P"):
                        item_rand_flag = int(p[1:] or "0")
                        break
            except Exception:
                pass

    try:
        import __main__ as main_mod
        rstate = getattr(main_mod, "state", None)
        _extract_route(rstate)
    except Exception:
        pass

    if not route_list:
        try:
            from PY.rando_script import state as rstate_mod
        except ModuleNotFoundError:
            from rando_script import state as rstate_mod
        _extract_route(rstate_mod)

    route_info = {
        "list": route_list,
        "index": route_index,
        "total": len(route_list),
    }
    if route_code is not None:
        route_info["code"] = route_code

    enabled = bool(item_rand_flag) if item_rand_flag is not None else False
    if item_rand_flag is not None:
        route_info["item_randomizer_enabled"] = enabled

    return route_info, enabled


def _build_state_snapshot() -> dict | None:
    save_txt = _decrypt_or_none(SAVEFILE_PATH, "save file")
    lic_txt = _decrypt_or_none(LICENSE_PATH, "onlineLicense")

    if save_txt is None and lic_txt is None:
        return None

    try:
        save_sections_raw = parse_ini(save_txt or "")
    except Exception as e:
        try:
            log(f"[state_exporter] parse_ini(save) failed: {e}")
        except Exception:
            pass
        time.sleep(1.0)
        return None

    try:
        lic_sections_raw = parse_ini(lic_txt or "")
    except Exception as e:
        try:
            log(f"[state_exporter] parse_ini(license) failed: {e}")
        except Exception:
            pass
        lic_sections_raw = {}

    if save_txt and (not isinstance(save_sections_raw, dict) or not save_sections_raw):
        try:
            log(
                "[state_exporter] parsed save has no sections – "
                "likely mid-write or corrupted, skipping snapshot"
            )
        except Exception:
            pass
        time.sleep(1.0)
        return None

    save_sections = save_sections_raw if isinstance(save_sections_raw, dict) else {}
    lic_sections = lic_sections_raw if isinstance(lic_sections_raw, dict) else {}

    route_info, item_rand_enabled = _detect_route_and_item_flag()

    virtual_state = _load_virtual_state() if item_rand_enabled else {}
    if item_rand_enabled and virtual_state:
        try:
            save_sections, lic_sections = _apply_virtual_rewards_to_sections(
                save_sections, lic_sections, virtual_state
            )
        except Exception as e:
            try:
                log(f"[state_exporter] apply_virtual_rewards failed: {e}")
            except Exception:
                pass

    state: dict = {
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
        "route": route_info,
        "item_randomizer": {
            "enabled": bool(item_rand_enabled),
            "virtual_events": len(virtual_state.get("events", []))
            if isinstance(virtual_state, dict)
            else 0,
        },
    }

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
