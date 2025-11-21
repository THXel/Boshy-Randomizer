import os
import time
from .config import debug_log
MAX_LOG_LINES = 3000
def _truncate_log(path: str, max_lines: int = MAX_LOG_LINES) -> None:
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
def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(debug_log, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        _truncate_log(debug_log)
    except Exception:
        pass
