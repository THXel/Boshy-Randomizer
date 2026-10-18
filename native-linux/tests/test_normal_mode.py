import copy,json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch,Mock
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from run_settings import normalize,defaults,route,character,encode,decode
from run_extras import defaults as hacks,EXTRAS,flags
from menu_model import Menu
from menu_controls import controls
from native_progress import Progress

def options():return dict(difficulty=1,levels=True,items=True,characters=False,mode='normal',target_count=5,boss_count=0,**defaults(),extras=hacks())
class NormalMode(unittest.TestCase):
 def menu(self):
  with patch('menu_model.summary',return_value={'exists':False,'completed':False}):return Menu(NS(base=ROOT))
 def test_normal_disables_routing_rewards_characters_and_f3_lock(self):
  o=normalize(options());self.assertFalse(o['levels']);self.assertFalse(o['items']);self.assertFalse(o['characters']);self.assertEqual(route('anything',o),[]);self.assertEqual(flags(o)&3,0)
 def test_default_and_explicit_character(self):
  o=normalize(options());self.assertEqual(character(ROOT,'seed',o)['name'],'Dark Boshy');o['start_character']='Kirby';self.assertEqual(character(ROOT,'seed',o)['name'],'Kirby')
 def test_every_hack_and_shot_mode_roundtrips(self):
  from run_extras import SHOT_MODES
  for mode in SHOT_MODES:
   o=options();o['start_character']='Kirby';o['extras'].update({k:True for k,_,_,_ in EXTRAS});o['extras'].update(shot_mode=mode,shot_interval_seconds=17)
   code=encode('NORMALSEED',o);seed,new=decode(code);self.assertEqual(seed,'NORMALSEED');self.assertEqual(new,normalize(o));self.assertEqual(encode(seed,new),code)
 def test_current_mode_encoding_is_frozen(self):
  import seed_codec as c
  for mode in ('randomizer','target'):
   o={**options(),'mode':mode,'characters':True};expected={'randomizer': 'BR12-AQmvMTIzNDU2NzgSNKvNCJfMdLM', 'target': 'BR12-AQmvMTIzNDU2NzgSNKvNHAECH7iP'}[mode]
   self.assertEqual(c.pack('1234ABCD',o,20261015,b'12345678'),expected)
 def test_mode_switch_remembers_drafts_and_enters_normal_with_hacks_off(self):
  m=self.menu();old=copy.deepcopy(m.options);m.change_mode('normal');self.assertTrue(all(not m.options['extras'][k] for k,_,_,_ in EXTRAS));self.assertEqual(m.options['extras']['shot_mode'],'off')
  m.options['start_character']='Kirby';m.options['extras']['god_mode']=True;m.change_mode('randomizer');self.assertEqual(m.options,old);m.change_mode('normal');self.assertEqual(m.options['start_character'],'Kirby');self.assertTrue(m.options['extras']['god_mode'])
 def test_normal_keyboard_controls_and_character_return(self):
  m=self.menu();m.change_mode('normal');m.page='new';ids=[i for i,_ in controls(m)];self.assertIn(3,ids);self.assertNotIn(4,ids);self.assertIn(5,ids);m.focus=ids[0]
  found=[]
  for _ in ids:found.append(m.focus);m.key(9)
  self.assertEqual(found,ids)
  m.focus=5;m.key(13);self.assertEqual(m.page,'characters');m.focus=m.character_names.index('Kirby');m.key(13);self.assertEqual((m.page,m.focus),('new',5));self.assertEqual(m.options['start_character'],'Kirby')
 def test_normal_hacks_and_seed_import_keep_normal_mode(self):
  m=self.menu();m.change_mode('normal');m.page='new';m.focus=7;m.key(13);self.assertEqual(m.page,'extras');m.focus=3;m.key(13);m.focus=len(EXTRAS);m.key(13);self.assertEqual(m.page,'new');self.assertTrue(m.options['extras']['god_mode'])
  code=encode('normal',m.options);m.import_seed(code);self.assertEqual(m.options['mode'],'normal');self.assertFalse(m.options['levels']);self.assertTrue(m.options['extras']['god_mode'])
 def test_normal_presets_cannot_enable_route_or_item_shuffle(self):
  for focus in range(3):
   m=self.menu();m.change_mode('normal');m.page='presets';m.focus=focus;m.key(13);self.assertFalse(m.options['levels']);self.assertFalse(m.options['items']);self.assertEqual(m.options['characters'],focus==1);self.assertEqual(m.options['mode'],'normal')
 def test_native_achievements_not_replaced_with_randomizer_receipts(self):
  from beta_catalogue import stage_achievements
  ach={'sonic':2,'megaman':2,'world1clear':1};self.assertEqual(stage_achievements(normalize(options()),{},ach),ach)
 def test_normal_room_and_boss_edges_never_request_random_destination(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'run').mkdir();o=normalize(options());m=dict(run_id='run',session_binding='binding',seed='seed',options=o,pool={'save1.ini':dict(frame=3,x=30,y=40,category='rooms')})
   p=Progress(NS(base=ROOT,root=root),m);p.request=Mock(side_effect=AssertionError('Unexpected random transition'))
   for frame in (3,4,5,29,5,6,7,8,9,8,60,61):
    self.assertIsNone(p.observe(frame=frame,position=(30,40),collectables={},achievements={'sonic':2},disk_achievements={'sonic':2},stats={'deaths':0},scene_tick=100))
   self.assertEqual(p.data['index'],0);self.assertEqual(p.data['limit'],0);self.assertEqual(p.data['history'],[])
 def test_offline_profile_name_is_initialized_and_existing_name_preserved(self):
  from native_profiles import make_profile
  from PY.ini_utils import parse_ini
  for existing in ('', 'My existing name'):
   with tempfile.TemporaryDirectory() as folder:
    root=Path(folder);(root/'run').mkdir()
    original='[License]\nName='+existing+'\nCharacter=0\nCharacterName=Dark Boshy\n[Unlockables]\n'
    store=NS(base=ROOT,root=root,read_save=lambda _:original,encode_save=lambda text:text.encode())
    make_profile(store,dict(run_id='run',slot=1,seed='seed',session_binding='binding',options=normalize(options())))
    data=parse_ini((root/'run/profile.ini').read_text())
    self.assertEqual({k.lower():v for k,v in data['license'].items()}['name'],existing or 'Player')
 def test_normal_solgryn_completion_still_creates_summary(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'run').mkdir();m=dict(run_id='run',slot=2,session_binding='binding',seed='seed',options=normalize(options()),pool={'save1.ini':dict(frame=3,x=30,y=40,category='rooms')});p=Progress(NS(base=ROOT,root=root),m)
   with patch('native_models.slot_summary',return_value=dict(deaths=0,seconds=0,run_id='run')):
    for value in (0,2):p.observe(frame=46,position=(100,100),collectables={},achievements={'solgryn':value},disk_achievements={'solgryn':value},stats={'deaths':7,'timeseconds':1234})
   result=json.loads((root/'run/summary.json').read_text());self.assertTrue(result['completed']);self.assertEqual(result['options']['mode'],'normal');self.assertEqual(result['deaths'],7);self.assertEqual(result['route'],[])
if __name__=='__main__':unittest.main()
