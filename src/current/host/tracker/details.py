"""Bounded presentation settings for the standalone tracker, without game imports."""

import json
from pathlib import Path

LABELS = json.loads(Path(__file__).with_name("setting-labels.json").read_text())
PACKS = {"original", "kamilia3", "wannafest22"}
SHOT_MODES = {"off", "random_interval", "spot", "death", "death_and_spot"}


def present(data):
    extras = []
    rows = data.get("active_extras", [])
    if isinstance(rows, list):
        seen = set()
        for row in rows[:64]:
            if not isinstance(row, dict):
                continue
            key = row.get("key")
            if not isinstance(key, str) or key not in LABELS or key in seen:
                continue
            seen.add(key)
            icon = row.get("icon", "✓")
            extras.append(
                dict(
                    key=key,
                    icon=icon if isinstance(icon, str) and len(icon) <= 4 else "✓",
                    labels=LABELS[key],
                )
            )
    source = data.get("run_settings", {})
    if not isinstance(source, dict):
        source = {}
    settings = {
        key: source.get(key)
        if isinstance(source.get(key), str) and source.get(key) in PACKS
        else "original"
        for key in ("music_pack", "blood_pack")
    }
    settings["music_enabled"] = source.get("music_enabled") is True
    mode = source.get("shot_mode", "off")
    if not isinstance(mode, str) or mode not in SHOT_MODES:
        mode = "off"
    settings["shot_labels"] = LABELS["shot_" + mode]
    interval = source.get("shot_interval_seconds", 300)
    settings["shot_interval_seconds"] = (
        interval if type(interval) is int and 1 <= interval <= 86400 else 300
    )
    return dict(active_extras=extras, run_settings=settings)
