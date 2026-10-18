import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from test_normal_mode import options,ROOT
from run_settings import normalize,encode,decode,route
from run_extras import flags
from character_cycle import CharacterCycle,available,choose
from menu_model import Menu
class NormalCharacters(unittest.TestCase):
 def test_opt_in_survives_seed_and_keeps_world_original(self):
  o=options();o['characters']=True;o=normalize(o)
  self.assertTrue(o['characters']);self.assertFalse(o['levels']);self.assertFalse(o['items']);self.assertEqual(route('test',o),[]);self.assertEqual(flags(o)&1,1)
  self.assertEqual(decode(encode('test',o))[1],o)
 def test_menu_enter_toggles_but_arrows_only_navigate(self):
  with patch('menu_model.summary',return_value={'exists':False,'completed':False}):m=Menu(NS(base=ROOT))
  m.change_mode('normal');m.page='new';m.focus=3;self.assertFalse(m.options['characters']);m.key(39);self.assertFalse(m.options['characters']);m.focus=3;m.key(13);self.assertTrue(m.options['characters']);m.key(13);self.assertFalse(m.options['characters'])
 def test_rotation_has_no_death_hub_menu_loading_or_resume_rerolls(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);(root/'run').mkdir();s=NS(base=ROOT,root=root);m=dict(run_id='run',seed='s');c=CharacterCycle(s,m);c.prepare=Mock(return_value=dict(name='Kirby',id=1))
   observe=lambda f,deaths=0,settled=True:c.observe_normal(f,{'deaths':deaths},None,0,settled=settled)
   observe(3);observe(3);observe(4,settled=False);observe(21);observe(29);observe(3);c.prepare.assert_not_called()
   observe(4);c.prepare.assert_called_once_with(1,None,0)
   observe(4);observe(3,1);self.assertEqual(c.prepare.call_count,1)
   observe(5,1);self.assertEqual(c.prepare.call_args.args[0],2)
   resumed=CharacterCycle(s,m);resumed.prepare=Mock();resumed.observe_normal(3,{'deaths':1},None,0);resumed.prepare.assert_not_called();self.assertEqual(resumed.data['normal']['sequence'],2)
 def test_new_unlocks_join_existing_starters(self):
  before=available(ROOT,{});after=available(ROOT,{'kirby':'1'})
  self.assertNotIn('Kirby',[c['name'] for c in before]);self.assertIn('Kirby',[c['name'] for c in after]);self.assertTrue(set(c['name'] for c in before)<=set(c['name'] for c in after))
  self.assertTrue(any(choose('test',i,after)['name']=='Kirby' for i in range(100)))
if __name__=='__main__':unittest.main()
