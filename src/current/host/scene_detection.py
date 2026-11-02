"""Distinguish the slot menu's white instructions on black from bright worlds."""


def is_slot_menu(image, reference):
    bright = []
    dark = []
    for y in range(36):
        for x in range(480, 640):
            rgb = reference.getpixel((x, y))
            if min(rgb) > 130:
                bright.append((x, y))
            elif max(rgb) < 25:
                dark.append((x, y))
    if not bright or not dark:
        raise ValueError("Invalid menu reference")
    return (
        sum(min(image.getpixel(pt)) > 110 for pt in bright) / len(bright) > 0.88
        and sum(max(image.getpixel(pt)) < 65 for pt in dark) / len(dark) > 0.85
    )
