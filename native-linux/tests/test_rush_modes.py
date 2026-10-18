import sys,json,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import run_settings as r
from run_extras import defaults as extras
from menu_model import Menu
from menu_controls import controls
from tracker_presenter import overview,route_entries,progress

def options(mode):return dict(difficulty=1,levels=True,items=True,characters=False,mode=mode,target_count=5,boss_count=0,**r.defaults(),extras=extras())
class RushTests(unittest.TestCase):
 def menu(self):
  with patch('menu_model.summary',return_value={'exists':False,'completed':False}):return Menu(NS(base=ROOT))
 def test_tutorial_absent_from_current_selection_and_all_generated_pools(self):
  self.assertNotIn('tutorial',r.LEVELS)
  for mode in ('randomizer','target','boss_rush','level_rush'):
   o=r.normalize(options(mode));self.assertNotIn('tutorial',r.pool_names(o))
   for seed in range(200):self.assertNotIn('tutorial',r.route(str(seed),o))
 def test_rush_has_seven_selected_stages_then_solgryn_and_roundtrips(self):
  for mode,valid,other in [('boss_rush',{v[2] for v in r.BOSSES.values()},'level_count'),('level_rush',set(r.LEVELS),'route_boss_count')]:
   o=r.normalize(options(mode));self.assertEqual(o[other],0)
   for i in range(200):
    seed=str(i);plan=r.route(seed,o);self.assertEqual(len(plan),8);self.assertEqual(plan[-1],'boss_solgryn.ini');self.assertEqual(len(set(plan)),8);self.assertTrue(set(plan[:-1])<=valid)
    code=r.encode(seed,o);self.assertTrue(code.startswith('BR12-'));self.assertEqual(r.decode(code),(seed,o))
 def test_custom_pool_and_count_remain_strict(self):
  for mode,pool,count,names in [('boss_rush','boss_pool','route_boss_count',['ridley','kappa']),('level_rush','level_pool','level_count',['save2.ini','save9.ini'])]:
   o=options(mode);o.update({pool:names,count:2});n=r.normalize(o);self.assertEqual(len(r.route('x',n)),3)
   for bad in (0,3,-1,True):
    with self.subTest(mode=mode,count=bad),self.assertRaises(ValueError):r.normalize({**o,count:bad})
 def test_menu_keeps_drafts_exposes_count_and_only_valid_pool_controls(self):
  m=self.menu();original=deepcopy(m.options)
  for mode,count,forbidden in [('boss_rush','route_boss_count',range(3,3+len(r.LEVELS))),('level_rush','level_count',range(3+len(r.LEVELS),3+len(r.LEVELS)+len(r.BOSSES)))]:
   m.change_mode(mode);self.assertEqual(m.options[count],7);m.page='new';m.focus=3;m.key(13);self.assertEqual(m.page,'choice');self.assertEqual(m.choice_name,count);m.focus=0;m.key(13);self.assertEqual(m.options[count],1)
   m.open_advanced();ids=[i for i,_ in controls(m)];self.assertFalse(set(ids)&set(forbidden));before=deepcopy(m.options)
   for key in (37,38,39,40,9,4096):m.key(key)
   self.assertEqual(m.options,before)
   m.key(34);self.assertIn(m.focus,dict(controls(m)));self.assertNotIn(m.focus,forbidden)
   m.change_mode('randomizer');self.assertEqual(m.options,original);m.change_mode(mode);self.assertEqual(m.options[count],1)
 def test_tracker_goals_are_first_colored_and_use_confirmed_completion(self):
  d=dict(play_mode='target',goals=[dict(kind='item',name='Cake',done=False),dict(kind='boss',name='Mario',done=True)],items=[dict(kind='item',name='Cake',done=True),dict(kind='item',name='Timer',done=False)],bosses=[dict(kind='boss',name='Mario',done=True)])
  rows=overview(d);self.assertEqual([r['name'] for r in rows],['Cake','Mario','Timer']);self.assertFalse(rows[0]['done']);self.assertTrue(rows[0]['goal']);self.assertTrue(rows[1]['goal']);self.assertNotIn('goal',rows[2]);self.assertEqual(progress(d)[1],50)
 def test_rush_tracker_uses_seed_route_and_only_collected_extras(self):
  o=r.normalize(options('level_rush'));plan=r.route('x',o);player=NS(m=dict(options=o,pool={spot:dict(frame=3) for spot in plan}),progress=NS(plan=plan,data=dict(index=1)))
  route=route_entries(player);self.assertTrue(route[0]['done']);self.assertTrue(route[1]['current']);self.assertEqual(route[-1]['name'],'Solgryn');self.assertEqual(route[-1]['kind'],'boss')
  d=dict(play_mode='level_rush',route_stages=route,items=[dict(kind='item',name='Timer',done=True),dict(kind='item',name='Cake',done=False)])
  rows=overview(d);self.assertEqual(len(rows),9);self.assertEqual(rows[-1]['name'],'Timer');self.assertTrue(all(r['done'] for r in route_entries(player,True)))
if __name__=='__main__':unittest.main()
