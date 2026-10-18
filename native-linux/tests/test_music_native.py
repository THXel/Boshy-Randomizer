import platform,shutil,subprocess,tempfile,unittest
from pathlib import Path
class MusicNative(unittest.TestCase):
 @unittest.skipUnless(platform.system()=='Linux' and platform.machine()=='x86_64' and shutil.which('gcc'),'Linux native harness')
 def test_background_music_always_loops_and_other_audio_is_untouched(self):
  with tempfile.TemporaryDirectory() as folder:
   exe=Path(folder)/'music';subprocess.run(['gcc','-w','-no-pie',str(Path(__file__).with_name('music_harness.c')),'-o',str(exe)],check=True)
   result=subprocess.run([str(exe)],capture_output=True,text=True,check=True);self.assertIn('stop delegation passed',result.stdout)
