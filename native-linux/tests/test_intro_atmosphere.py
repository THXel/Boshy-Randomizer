import random,struct,sys,tempfile,unittest
from pathlib import Path
from PIL import Image,ImageChops,ImageOps
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import intro_atmosphere as atmosphere

class IntroAtmosphereTests(unittest.TestCase):
 def test_all_themes_loop_without_geometry_or_alpha_changes(self):
  bg=Image.new('RGBA',(823,480),(80,100,120,255));mask=atmosphere.contrast_mask(bg)
  for theme in range(4):
   first=atmosphere.frame(bg,theme,0,mask);middle=atmosphere.frame(bg,theme,12,mask);end=atmosphere.frame(bg,theme,atmosphere.FRAMES,mask)
   self.assertEqual(first.size,bg.size);self.assertEqual(first.getchannel('A').getextrema(),(255,255));self.assertEqual(first.tobytes(),end.tobytes())
   self.assertIsNotNone(ImageChops.difference(first.convert('RGB'),middle.convert('RGB')).getbbox())
 def test_bright_backgrounds_receive_more_contrast(self):
  bright=atmosphere.contrast_mask(Image.new('RGBA',(823,480),'white'));dark=atmosphere.contrast_mask(Image.new('RGBA',(823,480),(20,20,20,255)))
  self.assertGreater(bright.getpixel((200,350)),dark.getpixel((200,350)))
  self.assertGreater(bright.getpixel((200,350)),bright.getpixel((700,350)))
  self.assertGreater(bright.getpixel((600,5)),bright.getpixel((600,100)))
 def test_updates_area_stays_dark_even_on_white_background(self):
  bg=Image.new('RGBA',(823,480),'white');mask=atmosphere.contrast_mask(bg)
  for theme in range(4):
   result=atmosphere.frame(bg,theme,9,mask)
   self.assertLessEqual(max(result.getpixel((200,350))[:3]),60)
 def test_effects_are_subtle_and_leave_gameplay_rng_untouched(self):
  bg=Image.new('RGBA',(823,480),(80,100,120,255));mask=atmosphere.contrast_mask(bg);state=random.getstate()
  for theme in range(4):
   a=atmosphere.frame(bg,theme,0,mask);b=atmosphere.frame(bg,theme,6,mask)
   diff=ImageChops.difference(a.convert('RGB'),b.convert('RGB'))
   self.assertLess(max(hi for lo,hi in diff.getextrema()),36)
  self.assertEqual(state,random.getstate())
 def test_effect_pack_is_bounded_and_matches_native_contract(self):
  bg=Image.new('RGBA',(823,480),(80,100,120,255))
  with tempfile.TemporaryDirectory() as path:
   folder=Path(path);fallback=atmosphere.prepare(folder,bg,2)
   self.assertEqual((folder/'effects.bin').read_bytes(),b'BRF1'+struct.pack('<5I',24,2,250,823,480))
   self.assertEqual(len(list(folder.glob('e*.png'))),24)
   with Image.open(folder/'e00.png') as first:self.assertEqual(first.tobytes(),fallback.tobytes())
if __name__=='__main__':unittest.main()
