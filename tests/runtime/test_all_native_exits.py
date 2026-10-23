import platform
import shutil
import subprocess
import tempfile
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native_triggers import EXITS, BOSS_EXITS


class AllNativeExits(unittest.TestCase):
    @unittest.skipUnless(
        platform.machine() == 'x86_64' and shutil.which('gcc'), 'native Linux harness'
    )
    def test_all_configured_room_destinations(self):
        pairs = sorted(
            {
                (a - 1, b - 1)
                for rules in (EXITS, BOSS_EXITS)
                for a, values in rules.items()
                for b in values
            }
        )
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder) / 'audit'
            subprocess.run(
                [
                    'gcc',
                    '-w',
                    '-no-pie',
                    str(Path(__file__).with_name('all_exits_harness.c')),
                    '-o',
                    str(exe),
                ],
                check=True,
            )
            result = subprocess.run(
                [str(exe), *[str(v) for pair in pairs for v in pair]],
                capture_output=True,
                text=True,
                check=True,
            )
            self.assertIn(
                f'Verified {len(pairs)} configured native exits', result.stdout
            )
