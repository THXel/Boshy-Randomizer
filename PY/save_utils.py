from __future__ import annotations
import os
import time
import json
import shutil
import tempfile
import hashlib
from typing import Optional
try:
    from PY.logger import log
except ModuleNotFoundError:
    from logger import log
try:
    from PY.config import ini_folder, iwbtb_folder, save_enc, rc4_key
except ModuleNotFoundError:
    from config import ini_folder, iwbtb_folder, save_enc, rc4_key
try:
    from PY.rc4_utils import decrypt_save, encrypt_save
except ModuleNotFoundError:
    from rc4_utils import decrypt_save, encrypt_save
LAST_WRITER_MARKER = os.path.join(ini_folder, "state_last_writer.json")
SNAPSHOT_DIR       = os.path.join(ini_folder, "_snapshots")
os.makedirs(SNAPSHOT_DIR, exist_ok=True)
def _short_stack(max_lines=4) -> str:
    import traceback
    try:
        stack = "".join(traceback.format_stack(limit=max_lines+2)[-max_lines-1:-1]).strip()
        return stack
    except Exception:
        return ""
def _file_hash(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()
def size_or_zero(p: str) -> int:
    try:
        return os.path.getsize(p) if os.path.exists(p) else 0
    except Exception:
        return 0
def mark_last_writer(tag: str, details: dict | None = None) -> None:
    try:
        size = os.path.getsize(save_enc) if os.path.exists(save_enc) else -1
        payload = {
            "ts": time.time(),
            "tag": str(tag),
            "size_after_bytes": size,
            "details": details or {},
            "stack": _short_stack(),
        }
        with open(LAST_WRITER_MARKER, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"⚠️ last-writer marker failed ({tag}): {e}")
def encrypt_save_atomic(plain_text: str, target_path: str, key: bytes,
                        retries: int = 4, min_bytes: int = 64) -> bool:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            dirn = os.path.dirname(target_path)
            os.makedirs(dirn, exist_ok=True)
            fd, tmp = tempfile.mkstemp(prefix=".tmp_save_", suffix=".ini", dir=dirn)
            os.close(fd)
            try:
                encrypt_save(plain_text, tmp, key)
                try:
                    with open(tmp, "rb") as f:
                        f.flush(); os.fsync(f.fileno())
                except Exception:
                    pass
                os.replace(tmp, target_path)
            finally:
                try:
                    if os.path.exists(tmp):
                        os.remove(tmp)
                except Exception:
                    pass
            try:
                sz = os.path.getsize(target_path)
                if sz >= min_bytes:
                    return True
            except Exception:
                pass
            time.sleep(0.05)
        except Exception as e:
            last_err = e
            time.sleep(0.08)
    if last_err:
        raise last_err
    return False
def write_save_tagged(tag: str, new_plain: str) -> None:
    try:
        encrypt_save_atomic(new_plain, save_enc, rc4_key)
        mark_last_writer(tag, {"plain_len": len(new_plain)})
        audit_save(f"post_write:{tag}", force=True)
        mirror_plain_for_tracker()
    except Exception as e:
        log(f"⚠️ write_save_tagged '{tag}' failed: {e}")
def snapshot_plain(prefix: str, plain: str) -> Optional[str]:
    try:
        ts = time.strftime("%Y%m%d-%H%M%S")
        p = os.path.join(SNAPSHOT_DIR, f"{prefix}_{ts}.ini")
        with open(p, "w", encoding="latin-1", errors="ignore") as f:
            f.write(plain)
        try:
            files = [
                os.path.join(SNAPSHOT_DIR, fn)
                for fn in os.listdir(SNAPSHOT_DIR)
                if fn.lower().endswith(".ini")
            ]
            files.sort(key=os.path.getmtime, reverse=True)
            for old in files[10:]:
                try:
                    os.remove(old)
                except Exception:
                    pass
        except Exception:
            pass
        return p
    except Exception:
        return None
def parse_ini_text(text: str) -> dict:
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
_last_audit = 0.0
def audit_save(reason: str, force: bool = False) -> None:
\
\
    global _last_audit
    now = time.time()
    if not force and (now - _last_audit) < 5.0:
        return
    _last_audit = now
    try:
        if not os.path.exists(save_enc):
            log(f"🔎 Audit({reason}): save missing")
            return
        size = os.path.getsize(save_enc)
        if size < 40:
            log(f"🔎 Audit({reason}): suspicious size={size} bytes")
        plain = decrypt_save(save_enc, rc4_key)
        data = parse_ini_text(plain)
        has_pos_section = "positions" in data
        pos_values = data.get("positions", {})
        has_stats = "stats" in data and bool(data["stats"])
        if pos_values:
            head = (plain[:300].replace("\r", "").replace("\n", "\\n")).strip()
            log(f"❗ Audit({reason}): Positions section has unexpected values (len={len(pos_values)}) – this may break fresh start, head='{head[:200]}...'")
            snap = snapshot_plain(f"audit_{reason}_positions_nonempty", plain)
            if snap:
                log(f"🧾 Snapshot written: {snap}")
        if not has_pos_section or not has_stats:
            head = (plain[:300].replace("\r", "").replace("\n", "\\n")).strip()
            log(
                f"❗ Audit({reason}): missing sections -> "
                f"PositionsSection={has_pos_section}, Stats={has_stats}, "
                f"size={size}, head='{head[:200]}...'"
            )
            snap = snapshot_plain(f"audit_{reason}", plain)
            if snap:
                log(f"🧾 Snapshot written: {snap}")
        else:
            log(f"🔎 Audit({reason}): OK (size={size}, PositionsSection={has_pos_section}, Stats={has_stats})")
    except Exception as e:
        log(f"⚠️ Audit({reason}) failed: {e}")
def mirror_plain_for_tracker() -> None:
    try:
        if not os.path.exists(save_enc):
            return
        plain = decrypt_save(save_enc, rc4_key)
        outp  = os.path.join(iwbtb_folder, "_new_plain.ini")
        tmp   = outp + ".tmp"
        with open(tmp, "w", encoding="latin-1", errors="ignore") as f:
            f.write(plain)
        os.replace(tmp, outp)
    except Exception as e:
        log(f"⚠️ mirror_plain failed: {e}")
def restore_if_save_shrunk(before_size: int, min_expected: int = 96, window_s: float = 3.0) -> bool:
\
\
\
    t0 = time.time()
    best_snapshot = None
    try:
        cands = []
        for fn in os.listdir(SNAPSHOT_DIR):
            if fn.startswith("route_backup_") or fn.startswith("pre_transition_") or fn.startswith("audit_post_transition_"):
                cands.append(os.path.join(SNAPSHOT_DIR, fn))
        cands.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        if cands:
            best_snapshot = cands[0]
    except Exception:
        pass
    while time.time() - t0 < window_s:
        now_sz = size_or_zero(save_enc)
        if now_sz == 0 or now_sz < min_expected or (before_size and now_sz < max(48, int(before_size * 0.5))):
            if best_snapshot and os.path.exists(best_snapshot):
                try:
                    with open(best_snapshot, "r", encoding="latin-1", errors="ignore") as f:
                        plain = f.read()
                    encrypt_save_atomic(plain, save_enc, rc4_key)
                    mark_last_writer("auto_restore_after_shrink", {
                        "restored_from": os.path.basename(best_snapshot),
                        "size_before": before_size,
                        "size_now": now_sz
                    })
                    log(f"🛡️ Save shrunk (now {now_sz}B). Restored from snapshot: {os.path.basename(best_snapshot)}")
                    mirror_plain_for_tracker()
                    return True
                except Exception as e:
                    log(f"⚠️ Restore failed: {e}")
            return False
        time.sleep(0.05)
    return False
def initialize_saves() -> dict[int, str]:
\
\
\
\
    ref_hash: dict[int, str] = {}
    for i in (1, 2, 3):
        src = os.path.join(ini_folder, f"SaveFile{i}.ini")
        dst = os.path.join(iwbtb_folder, f"SaveFile{i}.ini")
        if os.path.exists(src):
            shutil.copy2(src, dst)
            if i in (2, 3):
                ref_hash[i] = _file_hash(src)
            log(f"Initial copy: {src} -> {dst}")
        else:
            log(f"⚠️ WARNING: {src} missing – not copied")
    try:
        mirror_plain_for_tracker()
        audit_save("startup_init", force=True)
    except Exception as e:
        log(f"⚠️ Post-initialize audit/mirror failed: {e}")
    return ref_hash
def check_auto_restore(ref_hash: dict[int, str]) -> None:
    for i in (2, 3):
        src = os.path.join(ini_folder, f"SaveFile{i}.ini")
        dst = os.path.join(iwbtb_folder, f"SaveFile{i}.ini")
        try:
            if os.path.exists(dst):
                if ref_hash.get(i) and os.path.exists(src):
                    cur = _file_hash(dst)
                    if cur != ref_hash[i]:
                        shutil.copy2(src, dst)
                        log(f"Auto-restore: SaveFile{i}.ini changed → restored")
            elif os.path.exists(src):
                shutil.copy2(src, dst)
                log(f"Auto-restore: SaveFile{i}.ini missing → recreated")
        except Exception as e:
            log(f"⚠️ Auto-restore SaveFile{i}.ini failed: {e}")
def reset_savefile() -> None:
\
\
\
    src = os.path.join(ini_folder, "SaveFile1.ini")
    if os.path.exists(src):
        try:
            shutil.copy2(src, save_enc)
            mark_last_writer("reset_restore", {"src": src})
            audit_save("post_reset_restore", force=True)
            mirror_plain_for_tracker()
            log("SaveFile1.ini has been reset.")
        except Exception as e:
            log(f"⚠️ reset_savefile() failed: {e}")
    else:
        log("⚠️ reset_savefile(): INI/SaveFile1.ini missing")
