import threading
import time

# Endscreen importieren
from PY.end_stats import show_end_stats

# Fake-stop-event erzeugen
stop_event = threading.Event()

print("Starte Endscreen-Test in 1s…")
time.sleep(1)

# Beispiel-Route-Code für den Test
test_route_code = "R4-B6-T0-C2-P0-589563"

# Endscreen starten
show_end_stats(
    stop_event=stop_event,
    route_code=test_route_code
)

# Fenster offen halten
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    stop_event.set()
    print("Test beendet.")
