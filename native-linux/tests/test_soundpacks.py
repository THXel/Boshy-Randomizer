import json,sys,tempfile,unittest,struct,hashlib
from pathlib import Path
from unittest.mock import patch
from types import SimpleNamespace as NS
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import soundpacks
from menu_model import Menu
from menu_controls import controls,navigate

class Packs(unittest.TestCase):
 def fixture(self,base):
  (base/'INI').mkdir();root=base/'soundpacks/kamilia3';root.mkdir(parents=True)
  tracks=[]
  for name,seconds,roles in [('short.ogg',30,[]),('long.ogg',30.01,[]),('long2.ogg',70,[]),('Opening.ogg',114,['opening']),('Option.ogg',20,['menu']),('Death.ogg',2,['death'])]:
   path=root/name;path.write_bytes(name.encode());tracks.append(dict(file=name,name=name,seconds=seconds,roles=roles,shuffle=not roles and seconds>30,sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
  (root/'pack.json').write_text(json.dumps(dict(version=1,id='kamilia3',title='Kamilia 3',tracks=tracks)));return tracks
 def test_seed_mapping_excludes_short_music_and_role_cues(self):
  with tempfile.TemporaryDirectory() as d:
   rows=self.fixture(Path(d));a=soundpacks.mapping('seed',rows)
   self.assertEqual(a,soundpacks.mapping('seed',rows));self.assertEqual(set(a.values()),{'long.ogg','long2.ogg'});self.assertNotEqual(a,soundpacks.mapping('different',rows))
 def test_missing_and_invalid_preference_fall_back_to_original(self):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);self.fixture(base);self.assertEqual(soundpacks.selected(base),'original')
   (base/'INI/soundpack-preferences.json').write_text('{"pack":"../../bad"}');self.assertEqual(soundpacks.selected(base),'original')
 def test_persistence_and_disabled_shuffle_still_prepare_intro_and_death(self):
  with tempfile.TemporaryDirectory() as d,patch('soundpacks.audio',return_value='..\\menu-runtime\\music\\abc.wav'):
   base=Path(d);self.fixture(base);soundpacks.select(base,'kamilia3');self.assertEqual(soundpacks.selected(base),'kamilia3')
   self.assertFalse(soundpacks.prepare_music(base,dict(options={'extras':{'music':False}})))
   record=json.loads((base/'menu-runtime/soundpack-map.json').read_text());self.assertIn('Death 3',{r['cue'] for r in record['rows']});self.assertIn('select',{r['cue'] for r in record['rows']})
   soundpacks.select(base,'original');raw=(base/'menu-runtime/soundpack.bin').read_bytes();self.assertEqual(struct.unpack_from('<I',raw,8)[0],0)
 def test_shuffle_binary_and_telemetry_match(self):
  with tempfile.TemporaryDirectory() as d,patch('soundpacks.audio',return_value='..\\menu-runtime\\music\\abc.wav'):
   base=Path(d);self.fixture(base);soundpacks.select(base,'kamilia3');m=dict(run_id='a'*32,seed='SAME',options={'extras':{'music':True}})
   self.assertTrue(soundpacks.prepare_music(base,m));raw=(base/'menu-runtime/music.bin').read_bytes();self.assertEqual(raw[:36],b'BRM1'+b'a'*32);self.assertEqual(len(raw),40+45*168)
   record=json.loads((base/'menu-runtime/music-map.json').read_text());self.assertEqual(record['pack'],'kamilia3');self.assertEqual(len(record['tracks']),45)
 def test_manifest_rejects_traversal_and_short_shuffle(self):
  with tempfile.TemporaryDirectory() as d:
   base=Path(d);self.fixture(base);path=base/'soundpacks/kamilia3/pack.json';data=json.loads(path.read_text())
   data['tracks'][0]['shuffle']=True;path.write_text(json.dumps(data))
   with self.assertRaises(ValueError):soundpacks.catalogue(base,'kamilia3')
   data['tracks'][0]['shuffle']=False;data['tracks'][0]['file']='../bad.ogg';path.write_text(json.dumps(data))
   with self.assertRaises(ValueError):soundpacks.catalogue(base,'kamilia3')
 def test_pack_is_global_and_navigation_does_not_toggle_it(self):
  with tempfile.TemporaryDirectory() as d,patch('menu_model.summary',return_value={'exists':False,'completed':False}),patch('soundpacks.audio',return_value='..\\menu-runtime\\music\\abc.wav'):
   base=Path(d);self.fixture(base);m=Menu(NS(base=base));before=json.dumps(m.options,sort_keys=True);m.focus=7;m.key(13);self.assertEqual(m.page,'music')
   self.assertTrue(navigate(m,40));self.assertEqual(m.music_pack,'original');m.focus=2;m.key(13);self.assertEqual(m.music_pack,'kamilia3');m.key(27);self.assertEqual(soundpacks.selected(base),'original')
   m.open_music();m.focus=2;m.key(13);m.focus=len(m.music_packs)+1;m.key(13);self.assertEqual(soundpacks.selected(base),'kamilia3');self.assertEqual(json.dumps(m.options,sort_keys=True),before)
 def test_hack_submenu_still_controls_seeded_shuffle(self):
  with tempfile.TemporaryDirectory() as d,patch('menu_model.summary',return_value={'exists':False,'completed':False}),patch('soundpacks.audio',return_value='..\\menu-runtime\\music\\abc.wav'):
   base=Path(d);self.fixture(base);m=Menu(NS(base=base));m.open_extras();m.focus=9;m.key(13);self.assertEqual(m.page,'music');m.focus=0;m.key(13);self.assertTrue(m.options['extras']['music']);m.focus=len(m.music_packs)+1;m.key(13);self.assertEqual(m.page,'extras')
if __name__=='__main__':unittest.main()
