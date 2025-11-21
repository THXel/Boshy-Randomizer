import threading
import time
from PY.end_stats import show_end_stats
stop_event = threading.Event()
print("Starte Endscreen-Test in 1s…")
time.sleep(1)
test_route_code = "R4-B6-T0-C2-P0-589563"
show_end_stats(
    stop_event=stop_event,
    route_code=test_route_code
)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    stop_event.set()
    print("Test beendet.")
