import platform
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class NativeExit(unittest.TestCase):
    @unittest.skipUnless(
        platform.system() == 'Linux'
        and platform.machine() == 'x86_64'
        and shutil.which('gcc'),
        'Linux native harness requires gcc',
    )
    def test_real_c_control_flow(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / 'check'
            src = Path(__file__).with_name('fast_exit_harness.c')
            subprocess.run(
                ['gcc', '-w', '-no-pie', str(src), '-o', str(exe)], check=True
            )
            result = subprocess.run(
                [str(exe)], check=True, capture_output=True, text=True
            )
            self.assertIn('checks passed', result.stdout)
