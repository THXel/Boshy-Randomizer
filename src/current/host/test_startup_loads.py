"""Start-load coalescing must not cross observable mutations or control flow."""
import unittest
from gameplay.native_events import Events
from gameplay.startup_loads import transform
from transition.events import action, integer


class StartupLoadsTests(unittest.TestCase):
    def fixture(self):
        e = Events([])
        return e, e.row([e.start()], [e.load(109, 'SaveFile1.ini')])

    def test_only_duplicate_standalone_start_load_is_removed(self):
        e, load = self.fixture()
        read = e.row([e.start(), e.eq(109, 'Positions', 'frame', 35)],
                     [action(2, 26, 6000, [])])
        after, audit = transform(35, [[load, read, load], [load]])
        self.assertEqual(after, [[load, read], [load]])
        self.assertEqual(audit[0]['removed'], [2])

    def test_writes_other_files_and_ordinary_events_are_barriers(self):
        e, load = self.fixture()
        barriers = [
            e.row([e.start()], [e.text(109, 'Positions', 'xpos', integer(4))]),
            e.row([e.start()], [e.load(109, 'another.ini')]),
            e.row([e.eq(109, 'State', 'Pending', 1)], [action(2, 26, 6000, [])]),
            e.row([e.start()], [action(-1, 0, 0, [])]),
        ]
        for barrier in barriers:
            rows = [[load, barrier, load]]
            self.assertEqual(transform(35, rows), (rows, []))

    def test_conditional_load_cannot_establish_or_be_removed_from_cache(self):
        e, load = self.fixture()
        conditional = e.row([e.start(), e.eq(109, 'State', 'Pending', 1)],
                            [e.load(109, 'SaveFile1.ini')])
        for rows in ([[conditional, load]], [[load, conditional, load]]):
            self.assertEqual(transform(35, rows), (rows, []))

    def test_event_flags_cannot_establish_a_guaranteed_load(self):
        e, load = self.fixture()
        flagged = bytearray(load)
        flagged[4] = 1
        rows = [[bytes(flagged), load]]
        self.assertEqual(transform(35, rows), (rows, []))

    def test_non_save_files_and_mixed_action_rows_are_preserved(self):
        e, load = self.fixture()
        other = e.row([e.start()], [e.load(109, 'options.ini')])
        mixed = e.row([e.start()], [e.load(109, 'SaveFile1.ini'), action(2, 26, 6000, [])])
        for row in (other, mixed):
            rows = [[row, row]]
            self.assertEqual(transform(35, rows), (rows, []))


if __name__ == '__main__':
    unittest.main()
