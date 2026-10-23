import platform
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class DeathNative(unittest.TestCase):
    @unittest.skipUnless(
        platform.system() == 'Linux'
        and platform.machine() == 'x86_64'
        and shutil.which('gcc'),
        'Linux native harness',
    )
    def test_animation_timeline_and_scale_isolation(self):
        with tempfile.TemporaryDirectory() as folder:
            exe = Path(folder) / 'death'
            subprocess.run(
                [
                    'gcc',
                    '-w',
                    '-no-pie',
                    '-ffunction-sections',
                    '-Wl,--gc-sections',
                    str(Path(__file__).with_name('death_visuals_harness.c')),
                    '-o',
                    str(exe),
                ],
                check=True,
            )
            result = subprocess.run(
                [str(exe)], capture_output=True, text=True, check=True
            )
            self.assertIn('isolated no-bounce action passed', result.stdout)
