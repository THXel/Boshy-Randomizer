"""A transient unloaded frame may be retried; ambiguous or broken state may not."""

import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from phase_state import State, RuntimeNotReady
from phase_inspect import Bridge, MemoryReadUnavailable
from live_route_session import LiveRouteSession


class RuntimeWaitTests(unittest.TestCase):
    def state(self, roots):
        state = State.__new__(State)
        state.unicode = True
        state.run_globals = list(range(len(roots)))
        state.b = SimpleNamespace(
            u32=lambda address: roots[address] if address < len(roots) else 20000
        )
        return state

    def test_unloaded_frame_is_distinct_from_ambiguous_root(self):
        with self.assertRaises(RuntimeNotReady):
            self.state([0]).refresh()
        with self.assertRaises(AssertionError):
            self.state([0x20000, 0x30000]).refresh()
        state = self.state([0x20000])
        state.refresh()
        self.assertEqual(state.run, 0x20000)

    def test_unloaded_memory_has_explicit_error_and_unknown_responses_fail(self):
        bridge = Bridge.__new__(Bridge)
        bridge.cmd = Mock(return_value={"error": "read"})
        with self.assertRaises(MemoryReadUnavailable):
            bridge.read(0x20000, 32)
        bridge.cmd = Mock(return_value={"error": "command"})
        with self.assertRaises(ValueError):
            bridge.read(0x20000, 32)

    def test_bounded_wait_retries_only_loading_state(self):
        session = LiveRouteSession.__new__(LiveRouteSession)
        predicate = Mock(side_effect=[RuntimeNotReady(), MemoryReadUnavailable(), True])
        with patch("live_route_session.time.sleep"):
            session.wait(predicate)
        self.assertEqual(predicate.call_count, 3)
        with self.assertRaisesRegex(AssertionError, "bad data"):
            session.wait(Mock(side_effect=AssertionError("bad data")))


if __name__ == "__main__":
    unittest.main()
