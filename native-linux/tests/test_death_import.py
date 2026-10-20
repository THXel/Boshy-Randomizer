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
 def test_wannafest_cubes_rotate_and_keep_texture_colors(self):
  texture=Image.new('RGBA',(8,8),(255,25,25,255))
  frames=module.blood_wannafest(texture)
  self.assertEqual(len(frames),32)
  self.assertGreater(len({f.tobytes() for f in frames}),12)
  for frame in frames:
   self.assertEqual(frame.size,(20,20))
   self.assertIsNotNone(frame.getbbox())
   self.assertEqual(frame.getpixel((0,0))[3],0)
   self.assertGreater(sum(a>0 for a in frame.getchannel('A').getdata()),50)
   self.assertEqual(frame.getpixel((10,10)),(255,25,25,255))
if __name__=='__main__':unittest.main()
