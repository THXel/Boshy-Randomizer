import platform,shutil,subprocess,tempfile,unittest
from pathlib import Path
class SpiderNative(unittest.TestCase):
 @unittest.skipUnless(platform.machine()=='x86_64' and shutil.which('gcc'),'native Linux harness')
 def test_lifecycle_and_lethal_hit(self):
  with tempfile.TemporaryDirectory() as folder:
   exe=Path(folder)/'spider';subprocess.run(['gcc','-w','-no-pie',str(Path(__file__).with_name('spider_harness.c')),'-o',str(exe)],check=True)
   result=subprocess.run([str(exe)],capture_output=True,text=True,check=True);self.assertIn('one lethal hit passed',result.stdout)
