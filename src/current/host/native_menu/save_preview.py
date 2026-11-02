"""Compact native slot receipt, without the obsolete question-mark thumbnail."""

from PIL import ImageDraw
from native_menu import icons
from menu_host.draft import LEVELS, BOSSES
from menu_host.labels import stage


def draw(image, model, fonts, summary):
    d = ImageDraw.Draw(image)
    d.rounded_rectangle(
        (232, 196, 632, 313), radius=5, fill="#16232f", outline="#435767"
    )
    exists = summary["exists"]
    names = {
        **LEVELS,
        **{v[2]: v[0] for v in BOSSES.values()},
        "boss_solgryn.ini": "Solgryn",
    }
    spot = summary.get("spot", "")
    place = stage(names.get(spot, spot), model.language) if exists else model.t("empty")
    boss = spot.startswith("boss_")
    if exists:
        icons.paste(
            image,
            icons.artwork(
                names.get(spot, spot),
                frame=summary["frame"],
                kind="boss" if boss else "level",
            ),
            (240, 202, 268, 230),
        )
        icons.paste(
            image,
            icons.artwork(summary["character"], kind="character"),
            (596, 202, 624, 230),
        )
    if summary.get("test_run"):
        from native_menu.debug_actions import TEST_LABELS
        from native_menu.preferences import LANGUAGES
        place = TEST_LABELS[LANGUAGES.index(model.language)] + " · " + place
    title = f"{model.slot} · {place}"
    size = 14
    while size > 10 and d.textlength(title, font=fonts[size]) > 312:
        size -= 1
    d.text((274 if exists else 242, 203), title, font=fonts[size], fill="#edf5f6")
    details = model.t(model.draft.options["mode"])
    if exists:
        details += " · " + model.t("deaths") + f": {summary['deaths']}"
    d.text((242, 230), details, font=fonts[11], fill="#c3d2dc")
    d.text(
        (242, 247),
        model.t("current_seed") + ": " + summary.get("seed", model.draft.seed),
        font=fonts[11],
        fill="#a8bdc9",
    )
    tooltip = None
    for key, kind, y in (("items", "item", 267), ("characters", "character", 290)):
        badge = icons.symbol("chest" if kind == "item" else "person")
        badge = badge.resize((18, 18))
        image.alpha_composite(badge, (242, y))
        names = summary.get(key, [])
        if not names:
            d.text((266, y + 2), "—", font=fonts[11], fill="#71818d")
        for index, name in enumerate(names[:14]):
            x = 266 + 23 * index
            icons.paste(image, icons.artwork(name, kind=kind), (x, y, x + 20, y + 20))
            if (
                model.mouse
                and x <= model.mouse[0] < x + 22
                and y <= model.mouse[1] < y + 22
            ):
                tooltip = name
        if len(names) > 14:
            d.text((589, y + 2), f"+{len(names) - 14}", font=fonts[11], fill="#edf5f6")
    if tooltip:
        d.rectangle((240, 230, 629, 246), fill="#16232f")
        d.text((242, 230), tooltip, font=fonts[11], fill="#9aecd5")
