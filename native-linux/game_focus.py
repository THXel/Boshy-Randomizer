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


def handoff_tracker_startup(root,timeout=20):
    """After Tk maps its window, hand keyboard focus back exactly once."""
    deadline=time.monotonic()+timeout
    def handoff():
        if time.monotonic()>=deadline:return
        try:
            activate_game()
        except RuntimeError:
            root.after(100,handoff)
    # The native controller also focuses the game when its window is ready.
    # This covers a tracker that maps later, without enforcing focus in a run.
    root.after(150,handoff)
