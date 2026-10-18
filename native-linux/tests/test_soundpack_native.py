import platform,shutil,subprocess,tempfile,unittest
from pathlib import Path
class SoundpackNative(unittest.TestCase):
 @unittest.skipUnless(platform.system()=='Linux' and platform.machine()=='x86_64' and shutil.which('gcc'),'Linux native harness')
 def test_native_sound_actions_preserve_effects_and_channels(self):
  with tempfile.TemporaryDirectory() as folder:
   exe=Path(folder)/'soundpack';subprocess.run(['gcc','-w','-no-pie',str(Path(__file__).with_name('soundpack_harness.c')),'-o',str(exe)],check=True)
   result=subprocess.run([str(exe)],capture_output=True,text=True,check=True);self.assertIn('original fallback passed',result.stdout)
