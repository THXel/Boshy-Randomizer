"""Update the original animated author wordmark and its native hyperlink."""

import struct
from gameplay.native_events import Events
from transition.events import action, event, commands, expression, string

WEBSITE = "grynsoft.com"
URL = "https://grynsoft.com/"


def transform(frame, sections):
    if frame != 1:
        return sections, []
    result = []
    click_row = None
    for rows in sections:
        changed = []
        for row in rows:
            cs = commands(row)
            acts = []
            updated = False
            for c in cs:
                if c[0]:
                    continue
                if c[1:4] == (40, 80, 7) and b"http://www.solgryn.org" in c[-1]:
                    acts.append(action(40, 80, 7, [expression(string(URL), 45)]))
                    updated = True
                else:
                    acts.append(c[-1])
            new = event(row, [c[-1] for c in cs if c[0]], acts)
            changed.append(new)
            if updated:
                assert click_row is None
                click_row = new
        result.append(changed)
    assert click_row is not None, "Original intro hyperlink missing"
    e = Events(result, low=0xF800, high=0xF900)
    cs = commands(click_row)
    conds = []
    for c in cs:
        if not c[0]:
            continue
        data = bytearray(c[-1])
        struct.pack_into("<H", data, 14, e.ident())
        if c[1:3] == (-6, -7):
            assert struct.unpack_from("<H", data, 32)[0] == 14
            struct.pack_into("<H", data, 32, 13)
        conds.append(bytes(data))
    # The original emblem remains clickable, as does the website beneath it.
    result[4].append(e.row(conds, [c[-1] for c in cs if not c[0]]))
    return result, [
        dict(
            frame=1,
            website=WEBSITE,
            url=URL,
            original_animation=True,
            original_pixel_style=True,
            menu_credit=False,
        )
    ]


def image_loader(original):
    from native_menu.pixel_wordmark import update_bank

    def load(app):
        return update_bank(original(app))

    return load
