import sys,json,random,struct,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import background_sets as bg
class BackgroundSets(unittest.TestCase):
 def test_deterministic_and_no_random_state_side_effects(self):
  state=random.getstate();self.assertEqual(bg.mapping('A'),bg.mapping('A'));self.assertEqual(state,random.getstate());self.assertNotEqual(bg.mapping('A'),bg.mapping('B'))
 def test_collision_layers_keep_their_scroll_speed(self):
  sets=bg.catalogue()['sets']
  for seed in range(100):
   result=bg.mapping(str(seed))
   for i,source in enumerate(result):
    self.assertNotEqual(i,source)
    if sets[i]['locked']:self.assertEqual(sets[i]['coefficient'],sets[source]['coefficient'])
 def test_cloud_speed_matches_original_world_events(self):
  objects={r['oi']:r for r in bg.catalogue()['objects']}
  for oi,speed in {220:-3,221:-1,222:-2,455:-3,456:-1,457:-2,1790:-3,1791:-2,1792:-3,1913:-3,1914:-1,1915:-2}.items():
   self.assertTrue(objects[oi]['cloud']);self.assertEqual(objects[oi]['speed'],speed)
 def test_dimming_only_uses_original_sets(self):self.assertEqual(bg.mapping('ANY',False),list(range(9)))
 def test_original_world_one_and_three_planes_are_complete(self):
  data=bg.catalogue();sets={r['scene']+1:r for r in data['sets']}
  def ids(frame):return {data['objects'][r['object']]['oi'] for r in sets[frame]['instances']}
  self.assertEqual(ids(3),{220,221,222,223,224});self.assertEqual(ids(8),{617,681});self.assertNotIn(673,ids(8))
  self.assertTrue(sets[8]['locked']);self.assertTrue(sets[35]['locked'])
 def test_disabled_and_failed_preparation_clear_stale_plan(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'menu-runtime';p.mkdir();(p/'background-sets.bin').write_bytes(b'stale')
   self.assertFalse(bg.prepare(folder,dict(options={})))
   self.assertEqual((p/'background-sets.bin').read_bytes(),bg.MAGIC+bytes(76))
   m=dict(run_id='a'*32,seed='A',options=dict(extras=dict(version=7,sprite_scenery=True,sprite_backgrounds=True,sprite_dim=20)))
   with self.assertLogs(level='ERROR'):self.assertFalse(bg.prepare(folder,m))
   self.assertEqual((p/'background-sets.bin').read_bytes(),bg.MAGIC+bytes(76))
 def test_wrong_game_rejected_before_decoding(self):
  with tempfile.TemporaryDirectory() as folder:
   p=Path(folder)/'game';p.write_bytes(b'not the game')
   with patch.object(bg,'chunks',side_effect=AssertionError('must not decode')):
    with self.assertRaisesRegex(ValueError,'checksum'):bg.assets(p,'0'*64)
 def test_parallax_uses_colour_key_without_alpha(self):
  from PIL import Image,ImageEnhance
  source=Image.new('RGBA',(5,2),(77,88,99,0));source.putpixel((2,0),(100,120,140,255));source.putpixel((3,1),(150,160,170,255))
  for dim in (0,20,40,60):
   result=bg.parallax_texture(ImageEnhance.Brightness(source).enhance(1-dim/100))
   self.assertEqual(result.mode,'RGB');self.assertEqual(result.getpixel((0,0)),(0,0,0))
   self.assertEqual([p!=(0,0,0) for p in result.getdata()],[p[3]==255 for p in source.getdata()])
 def test_parallax_rejects_soft_mask(self):
  from PIL import Image
  with self.assertRaisesRegex(ValueError,'binary'):bg.parallax_texture(Image.new('RGBA',(1,1),(100,100,100,128)))
 def test_frozen_parallax_repair_preserves_plan(self):
  from PIL import Image
  from types import SimpleNamespace
  from runtime_versions import repair_parallax_visuals
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)/'menu-runtime';assets=root/'background-sets';assets.mkdir(parents=True)
   def prepare(base,manifest):
    (root/'background-sets.bin').write_bytes(b'same seeded plan')
    for n in ('o10.png','10.png'):
     image=Image.new('RGBA',(583,296),(20,30,40,255));image.putpixel((0,20),(33,44,55,0));image.save(assets/n)
    return True
   mod=SimpleNamespace(prepare=prepare);repair_parallax_visuals('background_sets',mod);wrapped=mod.prepare
   repair_parallax_visuals('background_sets',mod);self.assertIs(mod.prepare,wrapped)
   self.assertTrue(mod.prepare(folder,{}));self.assertEqual((root/'background-sets.bin').read_bytes(),b'same seeded plan')
   for n in ('o10.png','10.png'):
    with Image.open(assets/n) as image:
     self.assertEqual(image.mode,'RGB');self.assertEqual(image.getpixel((0,20)),(0,0,0));self.assertEqual(image.getpixel((3,3)),(20,30,40))
 def test_frozen_parallax_failure_invalidates_plan(self):
  from types import SimpleNamespace
  from runtime_versions import repair_parallax_visuals
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)/'menu-runtime';root.mkdir();(root/'background-sets.bin').write_bytes(b'old plan')
   mod=SimpleNamespace(prepare=lambda *a:True);repair_parallax_visuals('background_sets',mod)
   with self.assertLogs(level='ERROR'):self.assertFalse(mod.prepare(folder,{}))
   self.assertEqual((root/'background-sets.bin').read_bytes(),bg.MAGIC+bytes(76))
if __name__=='__main__':unittest.main()
