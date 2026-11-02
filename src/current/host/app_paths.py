"""Installation paths shared by the host, asset readers and package tooling.

Without a package configuration the existing private lab remains unchanged.
A packaged installation supplies absolute paths in BOSHY_RUNTIME_CONFIG; no
per-user developer paths need rewriting inside application modules.
"""

import json
import os
from pathlib import Path

LAB = Path(__file__).resolve().parent
ROOT = LAB.parents[1]


def load_config():
    path = os.environ.get("BOSHY_RUNTIME_CONFIG")
    if not path:
        if os.name == "nt":
            raise RuntimeError("Start Boshy Randomizer through its application launcher")
        return {}
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    required = {"prefix", "original", "soundpacks", "game", "wine", "repository"}
    if cfg.get("schema") != 1 or set(cfg) != required | {"schema"}:
        raise ValueError("Incomplete runtime installation configuration")
    for key in required:
        if not isinstance(cfg[key], str) or not Path(cfg[key]).is_absolute():
            raise ValueError("Runtime paths must be absolute: " + key)
    return cfg


CONFIG = load_config()
PREFIX = Path(CONFIG.get("prefix", str(Path.home() / "Games/clickteam-fusion-developer")))
ORIGINAL = Path(
    CONFIG.get(
        "original",
        str(Path.home() / ".local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe"),
    )
)
SOUNDPACKS = Path(CONFIG.get("soundpacks", str(ORIGINAL.parents[1] / "soundpacks")))
GAME = Path(
    CONFIG.get("game", str(PREFIX / "drive_c/BoshyTransitions/Boshy-dynamic-v60.exe"))
)
WINE = CONFIG.get(
    "wine",
    str(Path.home() / ".local/share/lutris/runners/wine/wine-staging-11.2-x86_64/bin/wine"),
)
REPO = Path(CONFIG.get("repository", str(ROOT / "work/Boshy-Randomizer")))

# Packaged Windows runs live beside the user's profile, never under Program Files.
RUNS = (
    Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "BoshyRandomizer/runs"
    if os.name == "nt"
    else PREFIX / "drive_c/BoshySceneTests"
)
PROFILE = (
    RUNS.parent / "profile"
    if os.name == "nt"
    else ROOT / "outputs/Fusion-NativeMenu-20261024/profile"
)
