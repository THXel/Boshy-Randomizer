"""One-time keyboard focus handoff after a loading window disappears."""
import time

def activate_game():
    from lab import game_window
    # No pointer movement, resizing or recurring focus enforcement.
    for _ in range(12):
        try:
            game=game_window();game.activate();time.sleep(.08)
            if game.isActive:return True
        except RuntimeError:pass
    raise RuntimeError('Das Spielfenster konnte nach dem Laden nicht aktiviert werden.')
