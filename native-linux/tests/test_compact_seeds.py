import base64,copy,hashlib,json,random,sys,unittest,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import run_settings as r
from run_extras import defaults as extras_defaults,normalize as normalize_extras

def options():
 return dict(difficulty=1,levels=True,items=True,characters=False,mode='randomizer',target_count=5,boss_count=0,**r.defaults(),extras=extras_defaults())
def old_code(seed,settings):
 payload=json.dumps([2,seed,r.normalize(settings)],sort_keys=True,separators=(',',':')).encode()
 return 'BR2-'+base64.urlsafe_b64encode(zlib.compress(payload,9)).decode().rstrip('=')+'.'+hashlib.sha256(payload).hexdigest()[:12]
class CompactSeeds(unittest.TestCase):
 def roundtrip(self,seed,o):
  normal=r.normalize(o);code=r.encode(seed,o);decoded=r.decode(code)
  self.assertEqual(decoded,(seed,normal));self.assertEqual(r.encode(*decoded),code)
  self.assertEqual(r.decode(old_code(seed,o)),decoded)
  self.assertEqual(r.route(seed,normal),r.route(*decoded))
  return code
 def test_frozen_standard_example(self):
  o=options();o['extras']=r._br3_defaults()['extras'];o.update(r.defaults(5));code=self.roundtrip('1234ABCD',o);self.assertEqual(code,'BR3-ARI0q80AZSwBuA');self.assertEqual(len(code),18);self.assertEqual(len(old_code('1234ABCD',o)),603)
 def test_new_standard_is_still_short(self):
  o=options();o.update(r.defaults(6));code=self.roundtrip('1234ABCD',o);self.assertEqual(code,'BR7-ARI0q80AUnkEzA');self.assertEqual(len(code),18)
 def test_seed_text_preserves_case_spaces_and_length(self):
  for seed in ('00000000','ffffffff','abcdEF12',' Seed with spaces ','x'*128,'A!z-_./?'):
   with self.subTest(seed=seed):self.roundtrip(seed,options())
 def test_legacy_option_shapes_and_versions(self):
  core=dict(difficulty=1,levels=False,items=True,characters=False)
  for version in (None,2,3,4,5,6,7):
   for extras in (None,1,2,3):
    o=copy.deepcopy(core)
    if version:o.update(r.defaults(version))
    if extras:
     e=r._br3_defaults()['extras'];e['version']=extras
     if extras<3:e.pop('shot_interval_seconds')
     if extras<2:
      for k in ('shot_mode','skip_intro','fast_chests'):e.pop(k)
     o['extras']=e
    with self.subTest(route=version,extras=extras):self.roundtrip('Legacy seed',o)
 def test_all_character_names(self):
  data=json.loads((ROOT/'INI/characters_rando.json').read_text())
  for name in ['Auto','Dark Boshy',*[c['name'] for c in data['characters']]]:
   with self.subTest(character=name):o=options();o['start_character']=name;self.roundtrip('1234ABCD',o)
 def test_random_settings(self):
  rng=random.Random(20261013)
  for i in range(1000):
   o=options();v=rng.choice((2,3,4,5,6,7));o.update(r.defaults(v));o['difficulty']=rng.randrange(4)
   o.update({k:bool(rng.randrange(2)) for k in ('levels','items','characters')})
   for pool,count in (('level_pool','level_count'),('boss_pool','route_boss_count')):
    o[pool]=rng.sample(o[pool],rng.randrange(len(o[pool])+1));o[count]=rng.randrange(len(o[pool])+1)
   if o['level_count']+o['route_boss_count']==0:continue
   o['mode']=rng.choice(('randomizer','target'));o['target_count']=rng.randrange(1,20);o['boss_count']=rng.randrange(len(r.catalogue(o))+1)
   o['extras'].update({k:bool(rng.randrange(2)) for k in r._BR3_EXTRAS});o['extras']['shot_mode']=rng.choice(r._BR3_SHOTS);o['extras']['shot_interval_seconds']=rng.choice((1,30,300,86400,rng.randrange(1,86401)))
   self.roundtrip('1234ABCD' if i%2 else 'custom-'+str(i),o)
 def test_damage_truncation_and_noncanonical_encoding_rejected(self):
  code=r.encode('1234ABCD',options())
  for i in range(4,len(code)):
   wrong=code[:i]+('A' if code[i]!='A' else 'B')+code[i+1:]
   with self.subTest(index=i),self.assertRaises(ValueError):r.decode(wrong)
  for wrong in (code[:-1],code+'=',code+'AAAA','BR3-','BR4-abc','BR3-'+('A'*2000)):
   with self.subTest(wrong=wrong[:30]),self.assertRaises(ValueError):r.decode(wrong)
 def test_checksum_valid_unknown_fields_rejected(self):
  def pack(payload):return 'BR3-'+base64.urlsafe_b64encode(payload+hashlib.sha256(b'BR3\0'+payload).digest()[:4]).decode().rstrip('=')
  for payload in (b'\x04',b'\x01'+bytes.fromhex('1234ABCD')+r._varuint(1<<15),b'\x01'+bytes.fromhex('1234ABCD')+b'\x00EXTRA'):
   with self.assertRaises(ValueError):r.decode(pack(payload))
 def test_invalid_seed_input(self):
  for seed in ('','x'*129,'\n','日本語'):
   with self.assertRaises(ValueError):r.encode(seed,options())
 def test_menu_accepts_old_and_new_and_buttons_match(self):
  from menu_model import Menu,seed_layout
  from types import SimpleNamespace
  m=Menu.__new__(Menu);m.store=SimpleNamespace(base=ROOT)
  for code in (old_code('1234ABCD',options()),r.encode('1234ABCD',options())):
   self.assertEqual(m.seed_value(code),('1234ABCD',r.normalize(options())))
   m.page='seed';m.seed_text=code;m.focus=0;m.dirty=False
   selected=[];m.seed_key=lambda key:selected.append((m.focus,key))
   field,buttons=seed_layout(code)
   m.click(700,(buttons[0]+buttons[1])//2);self.assertEqual(selected,[(3,13)])
if __name__=='__main__':unittest.main(verbosity=2)
