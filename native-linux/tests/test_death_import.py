import importlib.util,unittest
from pathlib import Path
from PIL import Image
spec=importlib.util.spec_from_file_location('death_import',Path(__file__).resolve().parents[2]/'packaging/import_death_visuals.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
class DeathImport(unittest.TestCase):
 def test_red_precedes_title_and_reset_frame_is_transparent(self):
  title=Image.new('RGBA',(100,50),'white');red=Image.new('RGBA',(32,32),(254,0,0,255))
  frames,fps,loop,ticks=module.screen_kamilia(title,red)
  self.assertIsNone(frames[0].getbbox())
  self.assertGreater(frames[5].getpixel((0,0))[3],0)
  self.assertEqual(frames[5].getpixel((320,240)),frames[5].getpixel((0,0)))
  self.assertEqual(frames[10].getpixel((320,240)),frames[10].getpixel((0,0)))
  self.assertGreater(frames[11].getpixel((320,240))[1],0)
  self.assertEqual(frames[loop].getpixel((320,240)),(255,255,255,255))
  self.assertLess(frames[loop].getpixel((0,0))[3],140)
  self.assertEqual(len(ticks),len(frames))
if __name__=='__main__':unittest.main()
