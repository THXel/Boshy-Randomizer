import platform
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


class SpriteRuntime(unittest.TestCase):
    @unittest.skipUnless(
        platform.system() == 'Linux'
        and platform.machine() == 'x86_64'
        and shutil.which('gcc'),
        'Linux native harness',
    )
    def test_live_bank_survives_copy_on_write_and_same_scene_reset(self):
        with tempfile.TemporaryDirectory() as d:
            exe = Path(d) / 'sprite'
            src = Path(__file__).with_name('sprite_runtime_harness.c')
            subprocess.run(
                ['gcc', '-w', '-no-pie', str(src), '-o', str(exe)], check=True
            )
            out = subprocess.run([str(exe)], check=True, capture_output=True, text=True)
            self.assertIn('reused scene handles passed', out.stdout)
