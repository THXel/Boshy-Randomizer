import sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from old_sonic import Gate,confirm
from native_progress import Progress

def sample(hp=45,tick=100,alive=True,obj=123,generation=(11,22),frame=60):
 return dict(frame=frame,tick=tick,hp=hp,player_alive=alive,boss_object=obj,generation=list(generation))
class OldSonicHP(unittest.TestCase):
 def test_zero_hp_waits_full_three_seconds_and_fires_once(self):
  g=Gate();self.assertFalse(g.observe('boss23.ini',2,sample(),0,0))
  self.assertFalse(g.observe('boss23.ini',2,sample(0,101),0,1));self.assertEqual(g.remaining(1),3)
  self.assertFalse(g.observe('boss23.ini',2,sample(-1,102),0,3.99))
  self.assertTrue(g.observe('boss23.ini',2,sample(-1,103),0,4))
  self.assertFalse(g.observe('boss23.ini',2,sample(-1,104),0,7))
 def test_one_hp_boss_and_s_skip_do_not_require_a_long_fight(self):
  g=Gate();g.observe('boss23.ini',0,sample(1),0,0)
  self.assertFalse(g.observe('boss23.ini',0,sample(0,101),0,.1))
  self.assertTrue(g.observe('boss23.ini',0,sample(0,102),0,3.1))
 def test_initial_zero_missing_boss_and_wrong_stage_never_win(self):
  for spot,s in [('boss23.ini',sample(0)),('boss23.ini',sample(None,obj=None)),('boss9.ini',sample(0)),('boss23.ini',sample(0,frame=61))]:
   g=Gate();self.assertFalse(g.observe(spot,0,s,0,0));self.assertFalse(g.observe(spot,0,s,0,4))
 def test_death_reset_new_generation_and_boss_replacement_cancel(self):
  for s,deaths in [(sample(0,tick=1),0),(sample(0,tick=103),1),(sample(0,tick=103,alive=False),0),(sample(0,tick=103,generation=(33,44)),0),(sample(0,tick=103,obj=456),0)]:
   g=Gate();g.observe('boss23.ini',0,sample(),0,0);g.observe('boss23.ini',0,sample(0,tick=101),0,1)
   self.assertFalse(g.observe('boss23.ini',0,s,deaths,5));self.assertIsNone(g.since)
 def test_disappearing_sprite_keeps_only_previously_confirmed_death(self):
  g=Gate();g.observe('boss23.ini',0,sample(),0,0);g.observe('boss23.ini',0,sample(0,tick=101),0,1)
  self.assertTrue(g.observe('boss23.ini',0,sample(None,tick=104,obj=None),0,4))
  g=Gate();g.observe('boss23.ini',0,sample(),0,0)
  self.assertFalse(g.observe('boss23.ini',0,sample(None,tick=104,obj=None),0,4))
 def test_hp_recovery_and_leaving_room_cancel_cooldown(self):
  for s in [sample(45,tick=103),None,sample(0,tick=103,frame=61)]:
   g=Gate();g.observe('boss23.ini',0,sample(),0,0);g.observe('boss23.ini',0,sample(0,tick=101),0,1)
   self.assertFalse(g.observe('boss23.ini',0,s,0,5));self.assertIsNone(g.since)
 def test_both_modes_credit_only_old_sonic_after_cooldown(self):
  for mode in ('randomizer','target'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
    root=Path(d);(root/'run').mkdir();pool={'boss23.ini':dict(frame=60,x=100,y=100,category='bosses'),'save1.ini':dict(frame=3,x=30,y=40,category='rooms'),'boss_solgryn.ini':dict(frame=46,x=100,y=100,category='bosses')}
    m=dict(run_id='run',session_binding='test',seed='1234ABCD',options=dict(levels=True,mode=mode,route_version=5),pool=pool)
    with patch('native_progress.goals',return_value=dict(items=[],bosses=['oldsonic'])),patch('run_settings.route',return_value=list(pool)):
     p=Progress(SimpleNamespace(base=ROOT,root=root),m)
    g=Gate()
    for now,hp in [(0,1),(1,0),(3.99,0)]:
     with patch('old_sonic.time.monotonic',return_value=now):self.assertFalse(confirm(p,g,sample(hp,tick=100+int(now*10)),{}))
     self.assertNotIn('oldsonic',p.data.get('stage_bosses',{}))
    with patch('old_sonic.time.monotonic',return_value=4):self.assertTrue(confirm(p,g,sample(0,tick=140),{}))
    result=p.observe(frame=60,position=(100,100),collectables={},achievements={},disk_achievements={},stats={})
    if result is None:result=p.request({},60,'Old Sonic besiegt (HP 0)',{})
    self.assertEqual(result,'boss_solgryn.ini' if mode=='target' else 'save1.ini');self.assertEqual(p.data['stage_bosses']['oldsonic']['cooldown_seconds'],3);self.assertNotIn('sonic',p.data['stage_bosses'])
if __name__=='__main__':unittest.main()
