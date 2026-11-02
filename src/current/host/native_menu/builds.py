"""Hash-pinned private Fusion executables used by native menu integrations."""

from build_profiles import PREFIX
from app_paths import GAME

DYNAMIC_BASE = GAME
DYNAMIC_SHA = "64d299bdcc30b5875d4a91159e49e64a10f74f79e7b2ec5b56b119e8cd88c4a8"

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
