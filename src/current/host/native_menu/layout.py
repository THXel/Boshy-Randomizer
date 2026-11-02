"""Shared geometry and navigation for the native 640 x 480 menu.

Cards are read left-to-right. Long history/route lists retain full-width rows.
Drawing, mouse hit targets and keyboard movement use this same coordinate map.
"""

SIZE = (640, 480)
PAGE_SIZE = 8
PANEL = (12, 196, 628, 455)
BACK = (20, 202, 120, 230)
PREVIOUS = (500, 202, 536, 230)
NEXT = (584, 202, 620, 230)
LIST_PAGES = frozenset(("updates", "preview", "targets"))
PARENTS = {
    "character_picker": "loadout",
    "shots": "cosmetics",
    "levels": "route",
    "bosses": "route",
    "targets": "route",
    "seed": "settings",
    "presets": "tools",
    "preset_details": "presets",
    "preset_delete": "preset_details",
    "updates": "tools",
}


def columns(page):
    return (
        4
        if page == "character_picker"
        else 1 if page in LIST_PAGES or page == "home" else 2
    )


def contains(rect, x, y):
    a, b, c, d = rect
    return a <= x < c and b <= y < d


def row_rect(page, visible_index):
    if page == "character_picker":
        x, y = 20 + visible_index % 4 * 151, 235 + visible_index // 4 * 74
        return x, y, x + 147, y + 70
    if page == "home":
        if visible_index < 3:
            x = 514 + visible_index * 36
            return x, 218, x + 32, 246
        y = 308 + (visible_index - 3) * 29
        return 382, y, 620, y + 25
    if page in LIST_PAGES:
        y = 235 + visible_index * 26
        return 20, y, 620, y + 24
    x, y = 20 + visible_index % 2 * 302, 235 + visible_index // 2 * 37
    return x, y, x + 298, y + 34


def hit(page, count, x, y):
    return next((i for i in range(count) if contains(row_rect(page, i), x, y)), None)


def move(page, focus, count, key):
    if key in (38, 40):
        # Stay in the current column when the final row is incomplete.
        width = columns(page)
        column = list(range(focus % width, count, width))
        return column[(column.index(focus) + (-1 if key == 38 else 1)) % len(column)]
    return (focus + (-1 if key == 37 else 1)) % count


def adjust_rect(page, index, direction):
    x, y, right, bottom = row_rect(page, index)
    return (
        right - 48 if direction < 0 else right - 24,
        y + 18,
        right - 24 if direction < 0 else right,
        bottom,
    )
