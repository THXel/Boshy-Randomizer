import struct, unittest
from types import SimpleNamespace
from unittest.mock import Mock
from phase_state import State


class PositionFixtureTests(unittest.TestCase):
    def state(self, changed_slot=False):
        state = State.__new__(State)
        state.run = 0x20000
        state.writes = []
        header = bytearray(32)
        struct.pack_into("<H", header, 0, 8 if changed_slot else 7)
        struct.pack_into("<I", header, 8, state.run)
        struct.pack_into("<H", header, 18, 42)
        struct.pack_into("<H", header, 24, 2)
        state.b = SimpleNamespace(
            read=Mock(return_value=bytes(header)),
            u32=Mock(return_value=100),
            cmd=Mock(
                side_effect=[{"written": False}, {"written": True}, {"written": True}]
            ),
        )
        return state, dict(ptr=0x30000, slot=7, oi=42, name="Bullet 2")

    def test_retry_moving_object_but_keep_cas(self):
        s, o = self.state()
        s.position(o, 320, 240)
        self.assertEqual(s.b.cmd.call_count, 3)
        self.assertEqual(len(s.writes), 2)
        self.assertEqual([w["new"] for w in s.writes], [320, 240])

    def test_reused_slot_never_written(self):
        s, o = self.state(True)
        with self.assertRaises(AssertionError):
            s.position(o, 320, 240)
        s.b.cmd.assert_not_called()


if __name__ == "__main__":
    unittest.main()
