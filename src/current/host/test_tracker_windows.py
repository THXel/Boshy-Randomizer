"""Windows feed identity contract; native Windows execution is a separate gate."""

import unittest
from tracker.windows_process import alive, Identity


class WindowsTrackerTests(unittest.TestCase):
    def test_requires_both_lifetimes_and_exact_game_image_path(self):
        data = dict(
            host_pid=1,
            host_start="100",
            game_pid=2,
            game_start="200",
            game_dir=r"C:\Users\Test\Boshy\run",
        )
        processes = {
            1: Identity("100", r"C:\Apps\Randomizer.exe"),
            2: Identity("200", r"c:\users\test\boshy\run\Boshy.exe"),
        }
        self.assertTrue(alive(data, processes.get))
        for changes in (
            {"host_start": "99"},
            {"game_start": "99"},
            {"host_pid": True},
            {"game_pid": -1},
            {"game_dir": r"C:\Other"},
            {"game_dir": r"..\run"},
            {"game_dir": r"C:\Games\..\run"},
        ):
            self.assertFalse(alive({**data, **changes}, processes.get), changes)
        processes[2] = Identity("200", r"C:\Users\Test\Boshy\run\Other.exe")
        self.assertFalse(alive(data, processes.get))
        del processes[2]
        self.assertFalse(alive(data, processes.get))


if __name__ == "__main__":
    unittest.main()
