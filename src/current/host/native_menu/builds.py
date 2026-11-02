"""Hash-pinned private Fusion executables used by native menu integrations."""

from build_profiles import PREFIX
from app_paths import GAME

DYNAMIC_BASE = GAME
DYNAMIC_SHA = "db20c6a0da6662ea348288ecf6512df82472bc8e6566d07ec148930a202389db"

EXTRAS_BASE = PREFIX / "drive_c/BoshyTransitions/Boshy-native-extras-v4.exe"
EXTRAS_SHA = "d4f7518fdf6e17a2bf9831010d3c05f2533aaef767b9f2b3e079b732d9c15ba3"

# Native scenery passed source, compiled-bank and same-process live checks.
DYNAMIC_SCENERY = True

# Camera source rectangle and per-save isolation verified live at Hello Kitty.
DYNAMIC_SCREEN_SHAKE = True

# Native shot artwork and sound selection, persisted in the run-local profile.
DYNAMIC_SHOTS = True

# Native optional spider support; private build verification accompanies each release.
DYNAMIC_SPIDER = True
