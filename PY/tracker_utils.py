import time
import os
import sys
import subprocess
from pathlib import Path
try:
    from PY.config import ini_folder
except ModuleNotFoundError:
    from config import ini_folder
try:
    from PY.logger import log
except ModuleNotFoundError:
    from logger import log
BOOT_LOG = os.path.join(ini_folder, "live_tracker_boot.log")
MAX_BOOT_LOG_LINES = 3000
def _truncate_boot_log(path: str, max_lines: int = MAX_BOOT_LOG_LINES) -> None:
    try:
        if not os.path.exists(path):
            return
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        if len(lines) <= max_lines:
            return
        trimmed = lines[-max_lines:]
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", errors="ignore") as f:
            f.writelines(trimmed)
        os.replace(tmp, path)
    except Exception:
        pass
def _write_boot_log(message: str) -> None:
    try:
        os.makedirs(ini_folder, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(BOOT_LOG, "a", encoding="utf-8", errors="ignore") as f:
            f.write(f"[{ts}] {message}\n")
        _truncate_boot_log(BOOT_LOG)
    except Exception:
        pass
def _guess_project_root() -> Path:
\
\
\
    here = Path(__file__).resolve()
    return here.parent.parent
def _python_executable() -> str:
    if sys.executable:
        return sys.executable
    return "python"
def start_live_tracker_robust(max_attempts: int = 3) -> subprocess.Popen | None:
\
\
\
\
\
\
\
    project_root = _guess_project_root()
    python_exe = _python_executable()
    _write_boot_log("=== Live Tracker launcher called ===")
    _write_boot_log(f"Project root guess: {project_root}")
    _write_boot_log(f"Using interpreter: {python_exe}")
    cmd = [python_exe, "-m", "PY.live_tracker"]
    _write_boot_log(f"Command: {' '.join(cmd)}")
    for attempt in range(1, max_attempts + 1):
        try:
            log(f"🖥️  Starting Live Tracker (attempt {attempt}/{max_attempts})…")
            _write_boot_log(f"Attempt {attempt}: launching…")
            p = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
            )
            time.sleep(0.4)
            if p.poll() is None:
                log(f"📄 Live Tracker running (pid={p.pid})")
                _write_boot_log(f"Live Tracker running (pid={p.pid})")
                return p
            else:
                log("⚠️ Live Tracker exited immediately; retrying…")
                _write_boot_log("Process exited immediately after start.")
                time.sleep(1.0)
        except Exception as e:
            log(f"⚠️ Tracker launch failed: {e}")
            _write_boot_log(f"Launch failed: {e!r}")
            time.sleep(1.0)
    log("⛔ Live Tracker failed to start after multiple attempts. See INI\\live_tracker_boot.log.")
    _write_boot_log("Giving up after maximum attempts.")
    return None
