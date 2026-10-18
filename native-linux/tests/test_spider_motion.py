import sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from PIL import Image
from spider_randomizer import prepare_orientations
from runtime_versions import repair_spider_visuals

class SpiderMotion(unittest.TestCase):
 def test_feet_face_target_and_body_pivot_stays_fixed(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);folder=root/'menu-runtime';folder.mkdir()
   im=Image.new('RGBA',(128,85));im.putpixel((64,28),(255,0,0,255));im.putpixel((64,80),(0,255,0,255));im.save(folder/'spider.png')
   prepare_orientations(root)
   self.assertEqual(len(list(folder.glob('spider-??.png'))),32)
   for facing,(dx,dy) in [(0,(0,52)),(8,(52,0)),(16,(0,-52)),(24,(-52,0))]:
    with Image.open(folder/f'spider-{facing:02d}.png') as rotated:
     self.assertEqual(rotated.size,(192,192))
     green=[(x,y) for y in range(192) for x in range(192) if rotated.getpixel((x,y))[1]>200]
     red=[(x,y) for y in range(192) for x in range(192) if rotated.getpixel((x,y))[0]>200]
     self.assertEqual(len(green),1);self.assertEqual(len(red),1)
     self.assertLessEqual(abs(red[0][0]-96),1);self.assertLessEqual(abs(red[0][1]-96),1)
     self.assertLessEqual(abs(green[0][0]-(96+dx)),1);self.assertLessEqual(abs(green[0][1]-(96+dy)),1)
 def test_saved_runs_receive_images_without_enabling_disabled_hack(self):
  calls=[];mod=types.SimpleNamespace(prepare=lambda base,m:calls.append('original'))
  with patch('spider_randomizer.prepare_orientations',side_effect=lambda base:calls.append('images')):
   repair_spider_visuals('spider_randomizer',mod);first=mod.prepare;repair_spider_visuals('spider_randomizer',mod);self.assertIs(first,mod.prepare)
   mod.prepare('unused',{'options':{'extras':{'spider':False}}});self.assertEqual(calls,['original'])
   mod.prepare('unused',{'options':{'extras':{'spider':True}}});self.assertEqual(calls,['original','original','images'])
if __name__=='__main__':unittest.main()
