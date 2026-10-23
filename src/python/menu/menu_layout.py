"""Local presentation preferences and reversible display/input transforms."""

import json
from pathlib import Path
from native_session import write_json

SIZES = ('small', 'standard', 'large')
FACTORS = {'small': 0.9, 'standard': 1.0, 'large': 1.15}


def load(base):
    try:
        value = json.loads(
            (Path(base) / 'INI/menu_preferences.json').read_text(encoding='utf-8')
        ).get('font_size')
        return value if value in SIZES else 'standard'
    except (OSError, ValueError, AttributeError):
        return 'standard'


def save(base, value):
    if value not in SIZES:
        raise ValueError('Invalid menu font size')
    write_json(
        Path(base) / 'INI/menu_preferences.json', dict(version=1, font_size=value)
    )


def viewport(page, size):
    width, height = size
    # Preserve the original arrangement at 1100x825 and above. Smaller windows
    # use the otherwise empty space above the panels, with contextual help hidden.
    effective = min(width, height * 4 / 3)
    maximum = 1.5 if page == 'slots' else 1.35
    scale = min(maximum, max(1.0, 1100 / max(320, effective)))
    sx = width / 880
    sy = height / 660
    if scale <= 1.01 and abs(sx / sy - 1) < 0.01:
        return None
    source = (
        ((318, 264, 876, 656) if page == 'slots' else (237, 254, 866, 651))
        if scale > 1.01
        else (0, 0, 880, 660)
    )
    # Keep text and click targets proportional even in a widescreen window.
    w = round((source[2] - source[0]) * scale * min(1, sy / sx))
    h = round((source[3] - source[1]) * scale * min(1, sx / sy))
    target = ((880 - w) // 2, (660 - h) // 2, (880 + w) // 2, (660 + h) // 2)
    return source, target


def inverse(point, view):
    if view is None:
        return point
    x, y = point
    src, dst = view
    if not (dst[0] <= x < dst[2] and dst[1] <= y < dst[3]):
        return None
    return (
        src[0] + (x - dst[0]) * (src[2] - src[0]) / (dst[2] - dst[0]),
        src[1] + (y - dst[1]) * (src[3] - src[1]) / (dst[3] - dst[1]),
    )
