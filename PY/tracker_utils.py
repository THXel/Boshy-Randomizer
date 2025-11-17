# ======================================================
# tracker_utils.py
# Robust Live-Tracker launcher (writes boot log).
#
# Vereinfachte Version:
#  - Startet nur noch:  python -m PY.live_tracker
#  - Keine --watch SaveFile1.ini Argumente mehr
#  - Schreibt Boot-Log nach INI/live_tracker_boot.log
# ======================================================
from __future__ import annotations

import os
import sys
import time
import subprocess
from pathlib import Path

# Logger laden
try:
    from PY.logger import log
except ModuleNotFoundError:  # Fallback, wenn als Script gestartet
    from logger import log  # type: ignore

# INI-Pfad laden (für Boot-Log)
try:
    from PY.config import ini_folder
except ModuleNotFoundError:
    from config import ini_folder  # type: ignore

BOOT_LOG = os.path.join(ini_folder, "live_tracker_boot.log")


def _write_boot_log(message: str) -> None:
    """Schreibt eine Zeile in INI/live_tracker_boot.log."""
    try:
        os.makedirs(ini_folder, exist_ok=True)
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(BOOT_LOG, "a", encoding="utf-8", errors="ignore") as f:
            f.write(f"[{ts}] {message}\n")
    except Exception:
        # Wenn selbst das fehlschlägt, machen wir keinen zusätzlichen Lärm
        pass


def _guess_project_root() -> Path:
    """
    Versucht das Projekt-Root zu finden.
    Annahme: tracker_utils.py liegt in PY/, also ist das Root = parent.parent.
    """
    here = Path(__file__).resolve()
    return here.parent.parent


def _python_executable() -> str:
    """Ermittelt den Python-Interpreter für den Subprozess."""
    if sys.executable:
        return sys.executable
    return "python"


def start_live_tracker_robust(max_attempts: int = 3) -> subprocess.Popen | None:
    """
    Startet den Live Tracker robust als Subprozess.

    - Nutzt python -m PY.live_tracker
    - Setzt cwd auf das Projekt-Root
    - Versucht es bis zu `max_attempts` Mal
    - Gibt den Prozess zurück oder None bei Fehlern
    """
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

            # kurze Gnadenfrist, damit ein sofortiger Crash bemerkt wird
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
