import copy,json,random,struct,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import sprite_chaos as chaos
from run_extras import defaults,normalize,flags,EXTRAS,GRAPHICS_DEFAULTS,GRAPHICS_ROWS
from seed_codec import defaults as options
from seed_share import encode,decode
class Expansion(unittest.TestCase):
 def test_all_styles_preserve_every_alpha_pixel_and_size(self):
  original=Image.new('RGBA',(7,5),(95,180,220));original.putalpha(Image.frombytes('L',original.size,bytes([0,1,127,128,254,255,0]*5)))
  source=Image.new('RGBA',(3,3),(200,100,50))
  for category in (1,2,4,8):
   for dim in (0,20,40,60):
    out=chaos.render(original,chaos.PALETTES[1] if category==8 else source,category,dim)
    self.assertEqual(out.size,original.size);self.assertEqual(out.getchannel('A').tobytes(),original.getchannel('A').tobytes())
 def test_dimming_works_without_shuffle_and_does_not_dim_actors_or_floors(self):
  original=Image.new('RGBA',(3,3),(200,150,100,255));source=Image.new('RGBA',(2,2),'red')
  plain=chaos.render(original,source,1,0,shuffle=False);dim=chaos.render(original,source,1,60,shuffle=False)
  self.assertEqual(plain.tobytes(),original.tobytes());self.assertLess(dim.getpixel((1,1))[0],plain.getpixel((1,1))[0])
  for c in (2,4,8):self.assertEqual(chaos.render(original,'#ef95ba' if c==8 else source,c,0).tobytes(),chaos.render(original,'#ef95ba' if c==8 else source,c,60).tobytes())
 def test_each_category_can_be_selected_independently(self):
  for category,key in chaos.CATEGORY_KEYS.items():
   opt={k:False for k in chaos.CATEGORY_KEYS.values()};opt.update(sprite_dim=0);opt[key]=True
   for c in chaos.CATEGORY_KEYS:self.assertEqual(chaos.selected({'category':c},opt),c==category)
 def test_styles_are_stable_per_actor_and_floor_material(self):
  rows=chaos.catalogue();before=random.getstate()
  for oi in {r['oi'] for r in rows if r['category']==8}:
   self.assertEqual(len({chaos.choice('SEED',r) for r in rows if r['oi']==oi}),1)
  floors=[r for r in rows if r['category']==4 and min(r['frames'])==5]
  self.assertEqual(len({chaos.choice('SEED',r) for r in floors}),1)
  for seed in range(32):
   for world in {min(r['frames']) for r in rows if r['category']==4}:
    self.assertEqual(len({chaos.choice(str(seed),r) for r in rows if r['category']==4 and min(r['frames'])==world}),1)
  self.assertEqual(before,random.getstate());self.assertNotEqual([chaos.choice('A',r) for r in rows],[chaos.choice('B',r) for r in rows])
 def test_all_visual_settings_roundtrip_in_each_mode(self):
  for mode in ('normal','target','randomizer'):
   for mask in range(32):
    for dim in (0,20,40,60):
     o=options();o['mode']=mode
     for i,key in enumerate(('sprite_scenery','sprite_backgrounds','sprite_decor','sprite_tiles','sprite_actors')):o['extras'][key]=bool(mask&(1<<i))
     o['extras']['sprite_dim']=dim
     from run_settings import normalize as normal
     self.assertEqual(decode(encode('X',o))[1],normal(o))
 def test_legacy_and_current_flags_have_separate_paths(self):
  o=options();o['extras']['sprite_scenery']=True;self.assertEqual(flags(o)&49152,32768)
  old={k:v for k,v in o['extras'].items() if k not in GRAPHICS_DEFAULTS};old['version']=6;self.assertEqual(normalize(old),old);o['extras']=old;self.assertEqual(flags(o)&49152,16384)
 def test_invalid_values_rejected(self):
  for key,value in [('sprite_dim',True),('sprite_dim',50),('sprite_tiles',1),('sprite_actors','yes')]:
   o=defaults();o[key]=value
   with self.assertRaises(ValueError):normalize(o)
 def test_submenu_navigation_click_and_discard(self):
  from menu_model import Menu
  from menu_controls import controls
  with patch('menu_model.summary',return_value={'exists':False,'completed':False}):m=Menu(SimpleNamespace(base=ROOT))
  m.page='new';before=copy.deepcopy(m.options);m.open_extras();m.focus=len(EXTRAS)-1;m.key(13);self.assertEqual(m.page,'graphics')
  for i,rect in controls(m):
   old=copy.deepcopy(m.options);m.hover(rect[0]+2,rect[1]+2);m.key(39);self.assertEqual(m.options,old)
  m.focus=0;m.key(13);self.assertTrue(m.options['extras']['sprite_scenery']);m.focus=3;m.key(13);self.assertTrue(m.options['extras']['sprite_tiles'])
  m.focus=5;m.key(13);self.assertEqual(m.options['extras']['sprite_dim'],40)
  m.key(27);m.key(27);self.assertEqual(m.page,'discard');m.focus=1;m.key(13);self.assertEqual(m.options,before)
 def test_preview_lists_every_visual_setting(self):
  from menu_help import preview_rows
  a=options();b=copy.deepcopy(a)
  for key in GRAPHICS_DEFAULTS:b['extras'][key]=60 if key=='sprite_dim' else not b['extras'][key]
  rows=preview_rows('A',a,'A',b);self.assertGreaterEqual(sum(r[3] for r in rows),5)
 def test_disabled_or_failed_plan_never_reuses_stale_files(self):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)/'menu-runtime';p.mkdir();plan=p/'scenery.bin';plan.write_bytes(b'old')
   self.assertFalse(chaos.prepare(d,{'options':options()}));self.assertEqual(plan.read_bytes(),b'BRV2'+bytes(40))
   o=options();o['extras']['sprite_scenery']=True
   with self.assertLogs(level='ERROR'):self.assertFalse(chaos.prepare(d,dict(options=o,run_id='a'*32,seed='A')))
   self.assertEqual(plan.read_bytes(),b'BRV2'+bytes(40))
 def test_native_catalogue_matches_exact_metadata(self):
  fields=('oi','type','category','size','obstacle','width','height','hx','hy','ax','ay','anim','direction','frame','offset','bank_size','anim_count','nframes','low','high')
  source=(ROOT/'sprite_chaos_catalogue.h').read_text()
  self.assertNotIn(1119,{r['oi'] for r in chaos.catalogue()})
  for r in chaos.catalogue():
   entry='{'+','.join(str(r[k]) if r[k]<2147483648 else str(r[k])+'U' for k in fields)+'}';self.assertIn(entry,source)
   self.assertTrue(all(3<=f<=60 and f not in (19,42,46,48,49,57) for f in r['frames']))
 def test_languages_include_submenu_and_help(self):
  for lang in ('de','en','es','ru','ja'):
   data=json.loads((ROOT/f'locales/{lang}.json').read_text())
   for _,title,hint in GRAPHICS_ROWS:self.assertTrue(data[title]);self.assertTrue(data[hint])
if __name__=='__main__':unittest.main()
