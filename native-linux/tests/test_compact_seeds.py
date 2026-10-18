import base64,copy,hashlib,json,random,sys,unittest,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import run_settings as r
import seed_codec as codec
import seed_share as share
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
  self.assertEqual(r.route(seed,normal),r.route(*decoded))
  return code
 def test_frozen_standard_example(self):
  code=codec.pack('1234ABCD',options(),20261015,b'12345678')
  self.assertEqual(len(code),32)
  self.assertEqual(codec.unpack(code)[:2],('1234ABCD',r.normalize(options())))
  self.assertLess(len(code),len(old_code('1234ABCD',options()))//10)
 def test_defaults_match_complete_current_catalogue(self):
  self.assertEqual(codec.defaults(),r.normalize(options()))
  self.assertEqual(set(codec.LEVELS),set(r.LEVELS))
  self.assertEqual(set(codec.BOSSES),set(r.BOSSES))
 def test_seed_text_preserves_case_spaces_and_length(self):
  for seed in ('00000000','ffffffff','abcdEF12',' Seed with spaces ','x'*128,'A!z-_./?'):
   with self.subTest(seed=seed):self.roundtrip(seed,options())
 def test_old_formats_are_rejected(self):
  for code in (old_code('1234ABCD',options()), *('BR'+str(v)+'-ARI0q80AZSwBuA' for v in range(2,12))):
   with self.subTest(code=code),self.assertRaises(ValueError):r.decode(code)
 def test_old_option_shapes_cannot_be_relabelled(self):
  for o in ({'difficulty':1,'levels':True,'items':True,'characters':False}, {**options(),'route_version':7}):
   with self.assertRaises(ValueError):r.encode('test',o)
 def test_all_character_names(self):
  data=json.loads((ROOT/'INI/characters_rando.json').read_text())
  for name in ['Auto','Dark Boshy',*[c['name'] for c in data['characters']]]:
   with self.subTest(character=name):o=options();o['start_character']=name;self.roundtrip('1234ABCD',o)
 def test_random_settings(self):
  rng=random.Random(20261013)
  for i in range(1000):
   o=options();o['difficulty']=rng.randrange(4)
   o.update({k:bool(rng.randrange(2)) for k in ('levels','items','characters')})
   for pool,count in (('level_pool','level_count'),('boss_pool','route_boss_count')):
    o[pool]=rng.sample(o[pool],rng.randrange(len(o[pool])+1));o[count]=rng.randrange(len(o[pool])+1)
   if o['level_count']+o['route_boss_count']==0:continue
   o['mode']=rng.choice(('randomizer','target'));o['target_count']=rng.randrange(1,20);o['boss_count']=rng.randrange(len(r.catalogue(o))+1)
   o['extras'].update({k:bool(rng.randrange(2)) for k in codec.HACKS});o['extras']['shot_mode']=rng.choice(codec.SHOTS);o['extras']['shot_interval_seconds']=rng.choice((1,30,300,86400,rng.randrange(1,86401)))
   self.roundtrip('1234ABCD' if i%2 else 'custom-'+str(i),o)
 def test_damage_truncation_and_noncanonical_encoding_rejected(self):
  code=r.encode('1234ABCD',options())
  for i in range(4,len(code)):
   wrong=code[:i]+('A' if code[i]!='A' else 'B')+code[i+1:]
   with self.subTest(index=i),self.assertRaises(ValueError):r.decode(wrong)
  for wrong in (code[:-1],code+'=',code+'AAAA','BR3-','BR4-abc','BR3-'+('A'*2000)):
   with self.subTest(wrong=wrong[:30]),self.assertRaises(ValueError):r.decode(wrong)
 def test_checksum_valid_unknown_fields_rejected(self):
  def pack(payload):return 'BR12-'+base64.urlsafe_b64encode(payload+hashlib.sha256(b'BR12\0'+payload).digest()[:4]).decode().rstrip('=')
  good=r.encode('1234ABCD',options());body=good[len(codec.PREFIX):];raw=base64.urlsafe_b64decode(body+'='*(-len(body)%4))[:-4]
  for payload in (bytes([4])+raw[1:],raw[:15]+codec.number(1<<len(codec.FIELDS)),raw+b'EXTRA',raw[:15]+b'\x80\x00'):
   with self.assertRaises(ValueError):r.decode(pack(payload))
 def test_every_encoded_field_is_covered(self):
  current=codec.flatten(r.normalize(options()))
  self.assertEqual(set(current),set(codec.FIELDS))
 def test_metadata_survives_different_installation(self):
  code=codec.pack('1234ABCD',options(),20261015,b'12345678')
  self.assertEqual(share.metadata(code),{'release':20261015,'rules':b'12345678'.hex()})
  self.assertEqual(share.compatibility(code,ROOT)['status'],'different')
 def test_frozen_run_exports_identical_code(self):
  import shutil,tempfile
  from types import SimpleNamespace
  from native_session import assets_for,digest
  from runtime_versions import pin,MODULES,SUPPORT
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);root=base/'native-runs';run='1'*32;(root/run).mkdir(parents=True);(base/'IWBTB').mkdir()
   names=set(assets_for(options()))|set(SUPPORT)|{n+'.py' for n in MODULES}
   self.assertFalse(set(share.RULE_FILES)-names)
   for name in names:
    target=base/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
   m=dict(run_id=run,session_binding='test',assets={n:digest((base/n).read_bytes()) for n in assets_for(options())})
   rules=pin(SimpleNamespace(base=base,root=root),m)
   code=share.encode('1234ABCD',options(),base)
   self.assertNotEqual(share.metadata(code)['rules'],'0000000000000000')
   self.assertEqual(share.encode('1234ABCD',options(),rules.base),code)
   self.assertEqual(rules.module('seed_share').encode('1234ABCD',options()),code)
   self.assertEqual(rules.module('run_settings').decode(code),('1234ABCD',r.normalize(options())))
 def test_invalid_seed_input(self):
  for seed in ('','x'*129,'\n','日本語'):
   with self.assertRaises(ValueError):r.encode(seed,options())
 def test_menu_accepts_current_and_buttons_match(self):
  from menu_model import Menu,seed_layout
  from types import SimpleNamespace
  m=Menu.__new__(Menu);m.store=SimpleNamespace(base=ROOT)
  for code in (r.encode('1234ABCD',options()),):
   self.assertEqual(m.seed_value(code),('1234ABCD',r.normalize(options())))
   m.page='seed';m.seed_text=code;m.focus=0;m.dirty=False
   selected=[];m.seed_key=lambda key:selected.append((m.focus,key))
   field,buttons=seed_layout(code)
   m.click(700,(buttons[0]+buttons[1])//2);self.assertEqual(selected,[(3,13)])
if __name__=='__main__':unittest.main(verbosity=2)
