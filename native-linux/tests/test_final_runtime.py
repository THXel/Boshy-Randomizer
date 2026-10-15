import json,struct,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import lab,run_extras,run_settings,seed_share,spider_randomizer
from test_compact_seeds import options
from test_ini_reset import Bridge
class FinalRuntime(unittest.TestCase):
 def test_spider_is_default_but_old_runs_do_not_acquire_it(self):
  self.assertTrue(run_extras.defaults()['spider'])
  old={'extras':run_settings._compact_defaults(6)['extras']}
  run_extras.upgrade(old);self.assertFalse(old['extras']['spider'])
 def test_spider_seed_is_independent_and_roundtrips_both_states(self):
  o=options();route=run_settings.route('test',o)
  for active in (False,True):
   o['extras']['spider']=active
   self.assertEqual(run_settings.decode(seed_share.encode('test',o,ROOT)),('test',run_settings.normalize(o)))
   self.assertEqual(run_settings.route('test',o),route)
   self.assertEqual(bool(run_extras.flags(o)&8192),active)
 def test_random_intervals_are_bounded_and_seeded(self):
  for i in range(2000):
   d=spider_randomizer.initial(str(i));self.assertTrue(300000<=d['remaining']<=1800000);self.assertEqual(d,spider_randomizer.initial(str(i)))
 def test_exports_are_resolved_from_actual_binary(self):
  from native_telemetry import export_rva
  values=[export_rva(ROOT/'native_menu_polished.dll',name) for name in ('SpiderState','MusicState','ExitState')]
  self.assertEqual(len(set(values)),3);self.assertTrue(all(0<x<1000000 for x in values))
 def tree(self):
  b=Bridge();obj=0x10000;state=0x20000;head=0x30000;root=0x40000;left=0x50000
  b.data[obj+0x168]=struct.pack('<I',state);b.data[state+20]=struct.pack('<I',head);b.data[head+4]=struct.pack('<I',root)
  for at,key,child in ((root,b'stats',left),(left,b'collectables',head)):
   raw=bytearray(64);struct.pack_into('<III',raw,0,child,head,head);struct.pack_into('<III',raw,16,at+100,len(key),len(key));b.data[at]=raw;b.data[at+100]=key
  return b,obj,root,left
 def test_group_lookup_returns_exact_node_and_missing_is_not_empty_data(self):
  b,obj,root,left=self.tree()
  with patch('lab.ini_objects',return_value={'Ini++':{'oi':109,'ptr':obj}}):
   self.assertEqual(lab._ini_group(b,109,'collectables'),b.data[left])
   with self.assertRaises(KeyError):lab._ini_group(b,109,'achievements')
 def test_zero_link_sentinel_is_an_absent_group(self):
  b,obj,root,left=self.tree();b.data[left]=bytes(64)
  with patch('lab.ini_objects',return_value={'Ini++':{'oi':109,'ptr':obj}}),self.assertRaises(KeyError):lab._ini_group(b,109,'achievements')
 def test_group_lookup_rejects_cycles_and_torn_strings(self):
  for bad in ('cycle','string'):
   b,obj,root,left=self.tree()
   if bad=='cycle':struct.pack_into('<I',b.data[root],0,root)
   else:struct.pack_into('<I',b.data[root],20,999999)
   with patch('lab.ini_objects',return_value={'Ini++':{'oi':109,'ptr':obj}}),self.assertRaises(lab.IniReadInProgress):lab._ini_group(b,109,'collectables')
if __name__=='__main__':unittest.main()

class SpiderPreference(unittest.TestCase):
 def test_disable_is_remembered_only_after_apply(self):
  from menu_model import Menu
  from types import SimpleNamespace
  with tempfile.TemporaryDirectory() as d,patch('menu_model.summary',return_value={'exists':False,'completed':False}):
   base=Path(d);(base/'INI').mkdir();m=Menu(SimpleNamespace(base=base));m.open_advanced();m.open_extras();m.focus=next(i for i,e in enumerate(run_extras.EXTRAS) if e[0]=='spider');m.extras_key(13)
   self.assertFalse((base/'INI/menu-preferences.json').exists());m.finish_advanced(False);m.focus=1;m.discard_key(13)
   self.assertTrue(m.options['extras']['spider']);self.assertFalse((base/'INI/menu-preferences.json').exists())
   m.open_advanced();m.open_extras();m.focus=next(i for i,e in enumerate(run_extras.EXTRAS) if e[0]=='spider');m.extras_key(13);m.finish_advanced(True)
   self.assertFalse(json.loads((base/'INI/menu-preferences.json').read_text())['spider']);self.assertFalse(Menu(SimpleNamespace(base=base)).options['extras']['spider'])
