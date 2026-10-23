"""One-time keyboard focus handoff after a loading window disappears."""

import time


def activate_game():
    """Focus is a best-effort convenience, never a startup requirement.

    Windows may deny SetForegroundWindow without setting GetLastError;
    PyGetWindow then raises its own Exception even for error code zero.
    """
    from lab import game_window

    for _ in range(12):
        try:
            game = game_window()
        except RuntimeError:
            time.sleep(0.08)
            continue
        try:
            if game.isActive:
                return True
            game.activate()
        except Exception:
            # Restrict recovery to the external window API, not the game loop.
            pass
        time.sleep(0.08)
        try:
            if game.isActive:
                return True
        except Exception:
            pass
    return False


def handoff_tracker_startup(root, timeout=20):
    """After Tk maps its window, hand keyboard focus back exactly once."""
    deadline = time.monotonic() + timeout

    def handoff():
        if time.monotonic() >= deadline:
            return
        try:
            if not activate_game():
                root.after(100, handoff)
        except RuntimeError:
            root.after(100, handoff)

    # The native controller also focuses the game when its window is ready.
    # This covers a tracker that maps later, without enforcing focus in a run.
    root.after(150, handoff)
