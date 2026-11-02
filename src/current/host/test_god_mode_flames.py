"""The God Mode indicator must be visual-only and opt in, in every source frame."""

import unittest
import struct
import recover_boshy_routes as source
from gameplay.god_mode_flames import transform
from gameplay.god_mode import GROUP, KEY
from transition.events import commands, ini_value, integer, expression
from transition.router import params


class FlameTests(unittest.TestCase):
    def test_original_events_unchanged_and_added_emitter_is_explicitly_guarded(self):
        frames = []
        for payload, frame in source.payloads.items():
            before = source.original_sections(payload)
            after, audit = transform(frame, before, source.objects)
            additions = {(r["section"], r["source_row"]): r for r in audit}
            used = {
                struct.unpack_from("<H", c[-1], 14)[0]
                for ss in before
                for row in ss
                for c in commands(row)
                if c[0]
            }
            for si, (old, new) in enumerate(zip(before, after)):
                cursor = iter(new)
                for ri, row in enumerate(old):
                    self.assertEqual(next(cursor), row)
                    entry = additions.get((si, ri))
                    if not entry:
                        continue
                    added = commands(next(cursor))
                    self.assertEqual(
                        params(added[0][-1], True),
                        [
                            (22, expression(ini_value(GROUP, KEY, 1, oi=entry["ini"]))),
                            (23, expression(integer(0), 23)),
                        ],
                    )
                    self.assertEqual(
                        struct.unpack_from("<H", params(added[1][-1], True)[1][1], 4)[
                            0
                        ],
                        1,
                    )
                    self.assertEqual(added[2][1:4], (2, -32, entry["player"]))
                    for c in added[:3]:
                        ident = struct.unpack_from("<H", c[-1], 14)[0]
                        self.assertNotIn(ident, used)
                        used.add(ident)
                    old_actions = [c for c in commands(row) if not c[0]]
                    self.assertEqual(len(added[3:]), len(old_actions))
                    for original, new_action in zip(old_actions, added[3:]):
                        if original[1:3] == (2, 59):
                            self.assertEqual(
                                struct.unpack_from(
                                    "<H", params(new_action[-1])[0][1], 6
                                )[0],
                                entry["player"],
                            )
                        else:
                            self.assertEqual(original, new_action)
                self.assertEqual(list(cursor), [])
            if audit:
                frames.append(frame)
        self.assertTrue({3, 14, 17, 45} <= set(frames))
        self.assertGreaterEqual(len(frames), 40)
