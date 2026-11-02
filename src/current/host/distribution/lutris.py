"""Portable Lutris installer description using the reviewed original-game settings.

Lutris owns registration: do not edit its database behind a running GUI. Paths
are supplied by the installing user's account, never copied from the developer.
"""

from copy import deepcopy
from pathlib import Path
import json

TEMPLATE = Path(__file__).with_name("lutris-settings.json")


def settings():
    return json.loads(TEMPLATE.read_text(encoding="utf-8"))


def installer(executable, prefix):
    executable, prefix = Path(executable), Path(prefix)
    if not executable.is_absolute() or not prefix.is_absolute():
        raise ValueError("Lutris paths must be absolute")
    config = deepcopy(settings())
    config["game"] = {
        "arch": "win64",
        "args": "",
        "exe": str(executable),
        "prefix": str(prefix),
    }
    return {
        "name": "Boshy Randomizer",
        "game_slug": "boshy-randomizer",
        "slug": "boshy-randomizer-native",
        "runner": "wine",
        "version": "Randomizer",
        "script": {**config, "installer": []},
    }


def write_installer(path, executable, prefix):
    # JSON is also valid YAML and avoids adding a YAML runtime dependency.
    result = installer(executable, prefix)
    Path(path).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result
