"""Context help shared by pointer hover, keyboard focus and run summary."""

from native_menu.help_labels import TEXT
from menu_host.labels import LANGUAGES

ALIASES = {
    "route": "mode",
    "loadout": "start_character",
    "gameplay": "god_mode",
    "cosmetics": "sprite_scenery",
    "seed": "copy",
    "tools": "presets",
    "levels": "pool",
    "bosses": "pool",
    "level_pool": "pool",
    "boss_pool": "pool",
    "level_count": "count",
    "route_boss_count": "count",
    "boss_count": "goals",
    "target_count": "goals",
    "targets": "goals",
    "goal": "goals",
    "sprite_backgrounds": "background",
    "character": "start_character",
    "preset": "presets",
    "user_preset": "presets",
    "save_preset": "presets",
    "use_preset": "presets",
    "delete_preset": "presets",
    "confirm_delete_preset": "presets",
    "update": "updates",
    "shot": "shots",
}


def summary(model, *, compact=False):
    from native_menu.model import RULES

    d = model.draft.options
    character = (
        model.t("auto_character")
        if d["start_character"] == "Auto"
        else d["start_character"]
    )
    mode = model.t(d["mode"])
    if d["mode"] == "normal":
        counts = model.t("normal")
    elif d["mode"] == "target":
        counts = f"{model.t('target_count')}: {d['target_count']} · {model.t('boss_count')}: {d['boss_count']}"
    else:
        counts = f"{model.t('summary_levels')}: {d['level_count']} · {model.t('summary_bosses')}: {d['route_boss_count']} + Solgryn"
    hacks = [model.t(k) for k in RULES if d["extras"].get(k) and k != "spider"]
    if compact:
        return f"{mode} · {character}", (
            f"{model.t('summary_levels')}: {d['level_count']} · {model.t('summary_bosses')}: {d['route_boss_count']} · {model.t('hacks')}: {len(hacks)}"
            if d["mode"] not in ("normal", "target")
            else counts
        )
    return f"{mode} · {character}. {counts}. {model.t('hacks')}: " + (
        ", ".join(hacks) or model.t("no_hacks")
    )


def explanation(model, row):
    if model.message:
        return model.message
    if model.page in ("preset_details", "preset_delete"):
        try:
            selected = next(
                p for p in model.presets.read() if p["id"] == model.preset_id
            )
            if row.enabled:
                return (
                    selected["name"]
                    + ": "
                    + (
                        model.t("preset_delete")
                        if row.key in ("delete_preset", "confirm_delete_preset")
                        else TEXT["presets"][LANGUAGES.index(model.language)]
                    )
                )
        except (OSError, ValueError, KeyError, TypeError, StopIteration):
            return model.t("presets_unreadable")
    if not row.enabled:
        if model.saved():
            return model.t("locked")
        mode = model.draft.options["mode"]
        key = (
            "locked_normal"
            if mode == "normal"
            else "locked_target" if mode == "target" else "locked_rush"
        )
    elif row.key in ("new", "run_summary"):
        return summary(model)
    else:
        if row.key.startswith("shot:"):
            mode = row.key.split(":", 1)[1]
            return (
                model.t("shot_" + mode)
                + ": "
                + TEXT["shots"][LANGUAGES.index(model.language)]
            )
        key = row.key.split(":", 1)[0]
        key = ALIASES.get(key, key)
    return TEXT.get(key, TEXT["back"])[LANGUAGES.index(model.language)]


def wrapped(draw, text, font, width, language):
    """Wrap all Unicode scripts; even a single long name cannot overflow."""
    tokens = list(text) if language == "ja" else text.split(" ")
    sep = "" if language == "ja" else " "
    lines, line = [], ""
    for token in tokens:
        trial = (line + sep + token) if line else token
        if line and draw.textlength(trial, font=font) > width:
            lines.append(line)
            line = ""
        trial = (line + sep + token) if line else token
        if draw.textlength(trial, font=font) <= width:
            line = trial
        else:
            for char in token:
                if line and draw.textlength(line + char, font=font) > width:
                    lines.append(line)
                    line = ""
                line += char
    if line:
        lines.append(line)
    return lines
