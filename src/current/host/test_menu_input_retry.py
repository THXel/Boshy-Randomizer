"""Native retry preserves the pending input instead of synthesizing another."""
import unittest
from native_menu.input_retry import transform
from native_menu.events import INPUT
from transition.events import commands

class MenuInputRetryTests(unittest.TestCase):
    def test_only_resends_the_existing_unacknowledged_command(self):
        result = transform([[]])
        self.assertEqual(result[0], [])
        row = result[-1][0]
        parsed = commands(row)
        self.assertEqual([(c[1], c[2], c[3]) for c in parsed if not c[0]], [(33, 124, INPUT)])
        for field in (b"Sequence\0", b"Ack\0", b"Schema\0"):
            self.assertIn(field, row)
        self.assertEqual(sum(c[0] for c in parsed), 2)
