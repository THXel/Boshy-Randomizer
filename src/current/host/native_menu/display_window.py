"""Select the native display backend without importing the other platform."""

import os

if os.name == "nt":
    from native_menu.display_windows import apply, tick, release
else:
    from native_menu.display_x11 import apply, tick, release, monitors, Backing
