"""A hover acknowledgement must not swallow a deliberate click or key."""

import unittest
from native_menu.input_buffer import transform, QUEUED, X, Y
from native_menu import events, hover
from transition.events import commands, integer, string, expression
from transition.router import params, value_parameter
from transition.boss_exits import split
import struct


class BufferTests(unittest.TestCase):
    def test_replay_keeps_sequence_last_and_captured_mouse_coordinates(self):
        initial, _ = events.transform([])
        initial = hover.transform(initial)
        after = transform(initial)
        self.assertEqual(len(after[-1]), 2 * (len(events.KEYS) + 1))
        for capture, replay in zip(after[-1][::2], after[-1][1::2]):
            cs, acts = split(capture)
            self.assertTrue(any(string("Key") in c and integer(1001) in c for c in cs))
            self.assertTrue(
                all(c[1:3] == (2, 31) for c in commands(capture) if not c[0])
            )
            cs, acts = split(replay)
            self.assertFalse(any(c[0] and c[1] == -6 for c in commands(replay)))
            assignments = [
                c for c in commands(replay) if not c[0] and c[1:3] == (33, 94)
            ]
            self.assertIn(string("Sequence"), assignments[-1][-1])
            key = struct.unpack_from(
                "<i", value_parameter(params(assignments[0][-1])[-1]), 6
            )[0]
            if key == 1000:
                for item, index in zip(assignments[1:3], (X, Y)):
                    self.assertEqual(
                        value_parameter(params(item[-1])[-1]),
                        events.alt(events.PANEL, index),
                    )
            self.assertEqual(struct.unpack_from("<hh", acts[-1], 2), (2, 31))
            self.assertIn(integer(0), acts[-1])
