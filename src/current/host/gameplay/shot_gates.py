"""Enable original special-shot handlers independently of character selection.

The effective license guard is forced only inside shot artwork/sound events.
The saved option and every other character/license handler remain untouched.
"""

import struct
from gameplay.native_extras import group, operator
from gameplay.shot_plan import GROUP
from transition.events import expression, integer, ini_value
from transition.router import params


def effective_license(raw, save):
    if struct.unpack_from("<hh", raw, 2) != (-1, -3):
        return raw
    ps = params(raw, True)
    if len(ps) != 2 or b"OnlineLicenseCharacter\0" not in ps[0][1]:
        return raw
    old = ps[0][1][6:-4]
    enabled = ini_value(GROUP, "Enabled", oi=save)
    value = (
        group(old)
        + operator(6)
        + group(integer(1) + operator(4) + enabled)
        + operator(2)
        + enabled
    )
    body = expression(value) + ps[1][1]
    return struct.pack("<H", 16 + len(body)) + raw[2:16] + body
