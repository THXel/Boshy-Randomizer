import unittest
import sys
import struct
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from event_references import ROWS, indices, canonical


class References(unittest.TestCase):
    def test_all_verified_conditions_accept_only_resolved_cache_changes(self):
        for row in ROWS:
            original = row['data']
            changed = bytearray(original)
            allowed = set()
            table = {}
            for off, oi in indices(original):
                self.assertLess(oi, 32768)
                index = oi + 20
                struct.pack_into('<H', changed, off, index)
                table[index] = oi
                allowed.update((off, off + 1))
            self.assertTrue(allowed)
            self.assertEqual(canonical(bytes(changed), row, table.get), original)
            self.assertEqual(
                canonical(bytes(changed), row, lambda _: None), bytes(changed)
            )
            for off in set(range(len(original))) - allowed:
                wrong = bytearray(changed)
                wrong[off] ^= 1
                self.assertEqual(
                    canonical(bytes(wrong), row, table.get), bytes(wrong), off
                )

    def test_truncated_record_stays_rejected(self):
        for row in ROWS:
            self.assertEqual(
                canonical(row['data'][:-1], row, lambda _: None), row['data'][:-1]
            )
