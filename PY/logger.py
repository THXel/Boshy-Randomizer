import time
from .config import debug_log

def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    with open(debug_log, "a", encoding="utf-8") as f:
        f.write(line + "\n")
