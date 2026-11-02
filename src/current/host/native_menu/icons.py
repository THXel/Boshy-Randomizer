"""Semantic menu symbols and original game/tracker artwork, with no generic portrait fallback."""

from functools import lru_cache
from PIL import Image, ImageDraw
from app_paths import REPO


@lru_cache(maxsize=1)
def assets():
    from tracker.server import Assets

    return Assets(REPO / "assets")


def artwork(name, *, frame=None, kind="item"):
    bank = assets()
    # Boss portraits take priority over shared world-frame artwork (e.g. Kracko).
    named = bank.names.get(name.casefold())
    path = (
        named
        if kind in ("boss", "character", "item") and named
        else bank.icon(dict(name=name, frame=frame))
    )
    return bank.files.get(path)


@lru_cache(maxsize=256)
def picture(path):
    if path is None:
        return None
    with Image.open(path) as image:
        return image.convert("RGBA")


def paste(image, path, box):
    source = picture(path)
    if source is None:
        return False
    graphic = source.copy()
    x, y, right, bottom = box
    graphic.thumbnail((right - x, bottom - y), Image.Resampling.NEAREST)
    image.alpha_composite(
        graphic,
        (x + (right - x - graphic.width) // 2, y + (bottom - y - graphic.height) // 2),
    )
    return True


def row_art(model, row):
    from menu_host.draft import BOSSES, LEVELS
    from transition.router import STAGES

    kind, _, key = row.key.partition(":")
    if kind == "boss_pool" and key in BOSSES:
        name, frame, _ = BOSSES[key]
        return artwork(name, frame=frame, kind="boss")
    if kind in ("level_pool", "preview") and key in STAGES:
        boss = next((b for b in BOSSES.values() if b[2] == key), None)
        return artwork(
            boss[0] if boss else LEVELS.get(key, key),
            frame=STAGES[key]["frame"],
            kind="boss" if boss else "level",
        )
    if kind == "character":
        name = "Boshy" if key == "Auto" else key
        return REPO / "assets/menu-character-icons" / f"{name}.png"
    if kind == "start_character":
        name = model.draft.options[kind]
        return (
            REPO
            / "assets/menu-character-icons"
            / f'{"Boshy" if name == "Auto" else name}.png'
        )
    if kind == "goal":
        group, name = key.split(":", 1)
        return artwork(
            BOSSES[name][0] if group == "bosses" else name,
            kind="boss" if group == "bosses" else "item",
        )
    return None


ALIASES = {
    "new": "play",
    "resume": "play",
    "route": "map",
    "preview": "map",
    "levels": "map",
    "level_count": "map",
    "level_pool": "map",
    "bosses": "boss",
    "boss_count": "boss",
    "route_boss_count": "boss",
    "loadout": "person",
    "characters": "person",
    "character": "person",
    "gameplay": "shield",
    "god_mode": "shield",
    "one_hp": "heart",
    "cosmetics": "palette",
    "sprite_scenery": "palette",
    "sprite_actors": "palette",
    "sprite_backgrounds": "landscape",
    "sprite_decor": "tree",
    "sprite_tiles": "tiles",
    "sprite_dim": "sun",
    "music": "music",
    "shots": "shot",
    "shot": "shot",
    "autofire": "shot",
    "shot_interval_seconds": "clock",
    "items": "chest",
    "fast_chests": "chest",
    "quiet_pickups": "chat",
    "tools": "tools",
    "font_size": "chat",
    "diagnostics": "tools",
    "presets": "save",
    "preset": "save",
    "user_preset": "save",
    "save_preset": "save",
    "use_preset": "save",
    "seed": "dice",
    "mode": "dice",
    "renew": "refresh",
    "copy": "copy",
    "paste": "paste",
    "targets": "target",
    "target_count": "target",
    "goal": "target",
    "difficulty": "difficulty",
    "updates": "history",
    "update": "history",
    "delete": "trash",
    "delete_preset": "trash",
    "confirm_delete_preset": "trash",
    "no_mouse_ghost": "cursor",
    "no_screen_shaking": "screen",
    "mirror": "mirror",
    "death_character": "refresh",
    "skip_intro": "skip",
    "spider": "spider",
    "back": "back",
}


@lru_cache(maxsize=64)
def symbol(key):
    """Small code-drawn symbols stay crisp at the game's native resolution."""
    image = Image.new("RGBA", (28, 28))
    d = ImageDraw.Draw(image)
    c, accent = "#9aecd5", "#f1cb80"

    def line(points, color=c, width=2):
        d.line(points, fill=color, width=width)

    def rect(box, color=c):
        d.rectangle(box, outline=color, width=2)

    def oval(box, color=c):
        d.ellipse(box, outline=color, width=2)

    if key in ("play", "skip"):
        d.polygon([(6, 4), (23, 14), (6, 24)], fill=c)
        if key == "skip":
            rect((23, 4, 25, 24), accent)
    elif key == "map":
        line(
            [
                (2, 6),
                (10, 3),
                (18, 7),
                (25, 3),
                (25, 22),
                (18, 25),
                (10, 21),
                (2, 25),
                (2, 6),
            ]
        )
        line([(10, 3), (10, 21)])
        line([(18, 7), (18, 25)])
        oval((15, 9, 22, 16), accent)
    elif key == "person":
        oval((9, 2, 19, 12))
        d.arc((3, 13, 25, 33), 180, 360, fill=c, width=3)
    elif key == "boss":
        d.polygon(
            [
                (4, 7),
                (3, 1),
                (10, 5),
                (19, 5),
                (25, 1),
                (24, 8),
                (24, 20),
                (19, 25),
                (9, 25),
                (4, 20),
            ],
            outline=c,
            width=2,
        )
        rect((7, 11, 10, 14), accent)
        rect((18, 11, 21, 14), accent)
        line([(10, 20), (18, 20)])
    elif key == "shield":
        d.polygon(
            [(3, 4), (14, 1), (25, 4), (23, 17), (14, 26), (5, 17)], outline=c, width=2
        )
        line([(8, 13), (12, 17), (21, 8)], accent, 3)
    elif key == "heart":
        d.polygon(
            [(14, 25), (2, 13), (2, 6), (7, 2), (14, 7), (21, 2), (26, 6), (26, 13)],
            fill=accent,
        )
    elif key == "palette":
        oval((2, 2, 25, 25))
        for x, y, col in [
            (8, 7, "#eb8a89"),
            (17, 6, accent),
            (21, 15, "#94bfff"),
            (10, 20, c),
        ]:
            d.ellipse((x - 2, y - 2, x + 2, y + 2), fill=col)
    elif key == "landscape":
        rect((1, 3, 26, 24))
        d.polygon([(3, 22), (11, 10), (17, 18), (21, 13), (25, 22)], fill=c)
        oval((19, 5, 23, 9), accent)
    elif key == "tree":
        line([(14, 15), (14, 26)], accent, 3)
        d.polygon([(14, 1), (3, 17), (25, 17)], outline=c, width=2)
    elif key == "tiles":
        for x, y in [(1, 9), (10, 9), (19, 9), (1, 18), (10, 18), (19, 18)]:
            rect((x, y, x + 7, y + 7))
        line([(1, 6), (26, 6)], accent)
    elif key == "sun":
        oval((8, 8, 20, 20), accent)
        for a, b in [
            ((14, 0), (14, 5)),
            ((14, 23), (14, 27)),
            ((0, 14), (5, 14)),
            ((23, 14), (27, 14)),
            ((3, 3), (6, 6)),
            ((22, 22), (25, 25)),
        ]:
            line([a, b])
    elif key == "music":
        line([(10, 21), (10, 5), (23, 2), (23, 18)], c, 3)
        line([(10, 9), (23, 6)], accent, 3)
        d.ellipse((3, 19, 11, 25), fill=c)
        d.ellipse((16, 16, 24, 22), fill=c)
    elif key == "shot":
        d.polygon(
            [(12, 8), (22, 8), (27, 14), (22, 20), (12, 20)], outline=accent, width=2
        )
        for y in (7, 14, 21):
            line([(1, y), (8, y)])
    elif key in ("clock", "history"):
        oval((3, 3, 25, 25))
        line([(14, 7), (14, 14), (20, 17)], accent)
    elif key == "chest":
        d.rounded_rectangle((2, 6, 26, 25), 4, outline=c, width=2)
        line([(2, 13), (26, 13)])
        rect((12, 11, 16, 18), accent)
    elif key == "chat":
        d.polygon(
            [(2, 3), (26, 3), (26, 20), (12, 20), (6, 26), (6, 20), (2, 20)],
            outline=c,
            width=2,
        )
        line([(7, 9), (21, 9)], accent)
        line([(7, 14), (18, 14)])
    elif key == "tools":
        line([(5, 24), (21, 8)], c, 5)
        d.arc((14, 0, 27, 13), 0, 270, fill=accent, width=3)
    elif key in ("save", "copy", "paste"):
        if key == "copy":
            rect((2, 2, 19, 20))
        rect((7, 6, 25, 26))
        rect((11, 10, 21, 14), accent)
        line([(11, 19), (21, 19)])
        line([(11, 23), (18, 23)])
    elif key == "dice":
        d.rounded_rectangle((2, 2, 26, 26), 4, outline=c, width=2)
        for x, y in [(8, 8), (20, 8), (14, 14), (8, 20), (20, 20)]:
            d.ellipse((x - 1, y - 1, x + 1, y + 1), fill=accent)
    elif key == "refresh":
        d.arc((3, 3, 25, 25), 30, 320, fill=c, width=3)
        d.polygon([(25, 2), (25, 13), (16, 7)], fill=accent)
    elif key == "target":
        for size in (11, 7, 2):
            oval(
                (14 - size, 14 - size, 14 + size, 14 + size), accent if size == 2 else c
            )
    elif key == "difficulty":
        for x, y in [(3, 19), (11, 12), (19, 4)]:
            d.rectangle((x, y, x + 5, 26), fill=accent if x == 19 else c)
    elif key == "trash":
        rect((6, 7, 22, 26))
        line([(3, 6), (25, 6)], accent, 3)
        line([(10, 2), (18, 2)], accent)
        line([(11, 11), (11, 22)])
        line([(17, 11), (17, 22)])
    elif key == "cursor":
        d.polygon(
            [(5, 2), (5, 24), (11, 18), (17, 25), (21, 22), (15, 16), (25, 15)],
            outline=c,
            width=2,
        )
    elif key == "screen":
        rect((2, 3, 26, 21))
        line([(14, 22), (14, 26)])
        line([(8, 26), (20, 26)], accent)
    elif key == "mirror":
        line([(14, 1), (14, 27)], accent)
        d.polygon([(2, 21), (10, 6), (10, 21)], outline=c, width=2)
        d.polygon([(26, 21), (18, 6), (18, 21)], outline=c, width=2)
    elif key == "spider":
        oval((9, 9, 19, 23))
        oval((11, 4, 17, 10), accent)
        for y in (11, 16, 21):
            line([(9, y), (3, y - 4), (1, y)])
            line([(19, y), (25, y - 4), (27, y)])
    elif key == "back":
        line([(17, 4), (7, 14), (17, 24)], c, 3)
    else:
        # Settings gear, never the unrelated Boshy portrait.
        oval((4, 4, 24, 24))
        oval((10, 10, 18, 18), accent)
        for a, b in [
            ((14, 0), (14, 5)),
            ((14, 23), (14, 27)),
            ((0, 14), (5, 14)),
            ((23, 14), (27, 14)),
        ]:
            line([a, b], c, 3)
    return image


def draw_row(image, model, row, box):
    path = row_art(model, row)
    if path and path.is_file() and paste(image, path, box):
        return
    graphic = symbol(ALIASES.get(row.key.split(":")[0], "settings")).copy()
    graphic.thumbnail((box[2] - box[0], box[3] - box[1]), Image.Resampling.NEAREST)
    image.alpha_composite(graphic, (box[0], box[1]))
