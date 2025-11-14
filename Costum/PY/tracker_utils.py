
# ======================================================
# tracker_utils.py
# Robust Live-Tracker launcher (writes boot log).
# ======================================================
import os, subprocess, sys, time

try:
    from PY.logger import log
except ModuleNotFoundError:
    from logger import log

try:
    from PY.config import ini_folder
except ModuleNotFoundError:
    from config import ini_folder


def start_live_tracker_robust():
    """Starts the Live Tracker, writes boot log to INI/live_tracker_boot.log."""
    here = os.path.dirname(os.path.abspath(__file__))
    pkg = "PY"
    in_pkg = os.path.basename(here).lower() == pkg.lower()
    project_root = os.path.dirname(here) if in_pkg else here

    mod = f"{pkg}.live_tracker" if not in_pkg else "live_tracker"
    wd  = project_root if not in_pkg else here

    lt_boot_log = os.path.join(ini_folder, "live_tracker_boot.log")
    os.makedirs(os.path.dirname(lt_boot_log), exist_ok=True)

    creation = 0
    try:
        creation = subprocess.CREATE_NO_WINDOW  # Windows-only
    except Exception:
        pass

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([project_root, os.path.join(project_root, "PY"), env.get("PYTHONPATH", "")])

    for attempt in range(1, 4):
        try:
            with open(lt_boot_log, "a", encoding="utf-8", errors="ignore") as lf:
                lf.write(f"[try {attempt}] starting tracker in '{wd}' with -m {mod}\n")
                p = subprocess.Popen(
                    [sys.executable, "-u", "-m", mod, "--watch", "SaveFile1.ini"],
                    cwd=wd,
                    env=env,
                    creationflags=creation,
                    stdout=lf, stderr=lf
                )
            time.sleep(0.4)
            if p.poll() is None:
                log(f"📄 Live Tracker running (pid={p.pid})")
                return p
            else:
                log("⚠️ Live Tracker exited immediately; retrying…")
                time.sleep(1.0)
        except Exception as e:
            log(f"⚠️ Tracker launch failed: {e}")
            time.sleep(1.0)

    log("⛔ Live Tracker failed to start after 3 attempts. See INI\\live_tracker_boot.log.")
    return None
