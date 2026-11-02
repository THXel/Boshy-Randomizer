"""Initial character through the game's local Ini++ profile, without runtime writes.

Auto preserves the original game's default. The explicit selection is seed-bound;
the normal dresser may subsequently change the character and unlocks in this run.
"""

import json
from pathlib import Path

from app_paths import REPO

ROSTER_PATH = REPO / "assets/INI/characters_rando.json"
ROSTER = {c["name"]: c["id"] for c in json.loads(ROSTER_PATH.read_text())["characters"]}
ROSTER["Dark Boshy"] = 84
CHOICES = ("Auto", *ROSTER)


def selected(options):
    name = options.get("start_character", "Auto")
    if name not in CHOICES:
        raise ValueError("Unknown native start character")
    return None if name == "Auto" else dict(name=name, id=ROSTER[name])


def profile_text(choice):
    if choice is None:
        return None
    if choice != selected({"start_character": choice["name"]}):
        raise ValueError("Character identity")
    return (
        "[License]\r\nName=Randomizer\r\nRandomizerStartCharacter=1\r\nNeverDoneItBefore=1\r\nCharacter="
        + str(choice["id"])
        + "\r\nCharacterName="
        + choice["name"]
        + "\r\n"
    )
