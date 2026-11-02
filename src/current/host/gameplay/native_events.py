"""Small native-event helpers with frame-local unique condition identifiers."""

import struct
from transition.events import (
    action,
    commands,
    event,
    expression,
    integer,
    string,
    compare_ini,
)


class Events:
    def __init__(self, sections, low=0xB000, high=0xCF00):
        used = {
            struct.unpack_from("<H", c[-1], 14)[0]
            for rows in sections
            for row in rows
            for c in commands(row)
            if c[0]
        }
        self.free = iter(n for n in range(low, high) if n not in used)

    def ident(self):
        return next(self.free)

    def start(self):
        return struct.pack("<HhhHHHBBH", 16, -3, -1, 0, 0, 0x20, 0, 0, self.ident())

    def eq(self, oi, group, key, value, comparison=0):
        return compare_ini(group, key, value, comparison, self.ident(), oi=oi)

    def cmp(self, left, right, comparison=0):
        p = expression(left) + expression(right, 23, comparison)
        return (
            struct.pack(
                "<HhhHHHBBH", 16 + len(p), -1, -3, 0, 0, 0x20, 2, 0, self.ident()
            )
            + p
        )

    def row(self, conditions, actions):
        return event(struct.pack("<hBB", -14, 0, 0) + bytes(10), conditions, actions)

    @staticmethod
    def load(oi, filename):
        path = (
            struct.pack("<hhH", -1, 8, 6)
            + struct.pack("<hhH", 0, 2, 6)
            + string(filename)
        )
        return action(33, 123, oi, [expression(path, 45), expression(integer(0))])

    @staticmethod
    def text(oi, group, key, tokens):
        return action(
            33,
            95,
            oi,
            [
                expression(string(group), 45),
                expression(string(key), 45),
                expression(tokens, 45),
            ],
        )

    @staticmethod
    def add(left, right):
        return left + struct.pack("<hhH", 0, 2, 6) + right

    @staticmethod
    def profile(sections):
        loads = [
            c
            for row in sections[0][:2]
            for c in commands(row)
            if c[1:3] == (33, 123) and b"onlineLicense.ini\0" in c[-1]
        ]
        assert len(loads) == 1, "Missing early local profile load"
        return loads[0][3]
