import copy,hashlib,json,struct,sys,tempfile,unittest
from pathlib import Path
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import death_visuals
class DeathVisuals(unittest.TestCase):
 def fixture(self,base):
  root=base/'soundpacks/kamilia3';root.mkdir(parents=True);visual={'version':1}
  for role,size in [('screen',(640,480)),('blood',(3,4))]:
   rows=[]
   for i in range(2):
    f=root/f'{role}{i}.png';Image.new('RGBA',size,(255,0,0,i*255)).save(f);rows.append(dict(file=f.name,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
   visual[role]=dict(frames=rows,fps=10,loop=1)
  visual['blood'].update(size=[3,4],origin=[1,2]);return dict(death_visuals=visual)
 def test_immutable_frames_and_original_switch_clear_plan(self):
  with tempfile.TemporaryDirectory() as folder:
   b=Path(folder);d=self.fixture(b);self.assertTrue(death_visuals.prepare(b,'kamilia3',d));raw=(b/'menu-runtime/deathpack.bin').read_bytes();self.assertEqual(len(raw),72);h=struct.unpack('<4s9I32s',raw);self.assertEqual(h[1:7],(2,10,1,2,10,1));self.assertTrue((b/'menu-runtime/deathpacks'/h[-1].decode()/'screen/001.png').is_file())
   self.assertFalse(death_visuals.prepare(b,'original'));self.assertEqual(struct.unpack_from('<I',(b/'menu-runtime/deathpack.bin').read_bytes(),4)[0],0)
   self.assertFalse(json.loads((b/'menu-runtime/deathpack-map.json').read_text())['active'])
 def test_tampered_frame_disables_previous_pack(self):
  with tempfile.TemporaryDirectory() as folder:
   b=Path(folder);d=self.fixture(b);death_visuals.prepare(b,'kamilia3',d);(b/'soundpacks/kamilia3/screen0.png').write_bytes(b'corrupt')
   with self.assertRaises(ValueError):death_visuals.prepare(b,'kamilia3',d)
   self.assertEqual(struct.unpack_from('<I',(b/'menu-runtime/deathpack.bin').read_bytes(),4)[0],0)
 def test_paths_dimensions_and_timing_rejected(self):
  with tempfile.TemporaryDirectory() as folder:
   b=Path(folder);d=self.fixture(b)
   for field,value in [('fps',0),('fps',51),('loop',2),('loop',-1)]:
    bad=copy.deepcopy(d);bad['death_visuals']['screen'][field]=value
    with self.assertRaises(ValueError):death_visuals.prepare(b,'kamilia3',bad)
   d['death_visuals']['screen']['frames'][0]['file']='../outside.png'
   with self.assertRaises(ValueError):death_visuals.prepare(b,'kamilia3',d)
 def test_static_blood_variant_has_no_animation_clock(self):
  with tempfile.TemporaryDirectory() as folder:
   b=Path(folder);d=self.fixture(b);d['death_visuals']['blood']['random_static']=True;death_visuals.prepare(b,'kamilia3',d)
   self.assertEqual(struct.unpack_from('<I',(b/'menu-runtime/deathpack.bin').read_bytes(),20)[0],0)
 def test_variable_timeline_matches_fast_title_arrivals(self):
  with tempfile.TemporaryDirectory() as folder:
   b=Path(folder);d=self.fixture(b);d['death_visuals']['screen']['ticks']=[5,1]
   death_visuals.prepare(b,'kamilia3',d);raw=(b/'menu-runtime/deathpack.bin').read_bytes()
   self.assertEqual(struct.unpack_from('<I',raw,8)[0],0)
   self.assertEqual(struct.unpack_from('<2H',raw,72),(5,1))
   for invalid in ([5], [5,0], [5,501], [5,True]):
    d['death_visuals']['screen']['ticks']=invalid
    with self.assertRaises(ValueError):death_visuals.prepare(b,'kamilia3',d)
if __name__=='__main__':unittest.main()
