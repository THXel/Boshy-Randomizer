"""Native room boundary, arrival/reset safety and seed compatibility."""
import sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from test_kid_icarus import options,pool
from native_triggers import CompletionGate,stage_frames,exits_for
from native_progress import Progress
import run_settings as r

class RandomWorldSplit(unittest.TestCase):
 def observe(self,g,spot,frame,now,*,version=7,deaths=0,tick=100,restart=False):
  with patch('native_triggers.time.monotonic',return_value=now):
   return g.observe(spot,pool(version)[spot],frame,{},{},{'deaths':deaths},tick=tick,restart_pressed=restart)
 def test_live_capture_and_legacy_semantics(self):
  p=pool(7);self.assertEqual((p['save10.ini']['frame'],p['save10.ini']['x'],p['save10.ini']['y']),(23,16,1679))
  self.assertEqual(stage_frames('save9.ini',p['save9.ini']),(22,));self.assertEqual(stage_frames('save10.ini',p['save10.ini']),(23,))
  for version in (5,6):
   p=pool(version);self.assertEqual(stage_frames('save9.ini',p['save9.ini']),(22,23));self.assertEqual(exits_for('save9.ini',p['save9.ini']),(24,53));self.assertEqual((p['save10.ini']['x'],p['save10.ini']['y']),(20,1650))
   g=CompletionGate()
   for frame,t in [(22,0),(23,1),(23,5)]:self.assertIsNone(self.observe(g,'save9.ini',frame,t,version=version))
 def test_boundary_requires_origin_then_triggers_immediately(self):
  g=CompletionGate()
  for frame,t in [(23,0),(23,5),(22,6)]:self.assertIsNone(self.observe(g,'save9.ini',frame,t))
  self.assertEqual(self.observe(g,'save9.ini',23,6.01),'Level-Ausgang')
 def test_direct_arrival_does_not_chain_and_part_two_has_own_exit(self):
  g=CompletionGate()
  for frame,t in [(23,0),(23,10),(23,11)]:self.assertIsNone(self.observe(g,'save10.ini',frame,t))
  self.assertEqual(self.observe(g,'save10.ini',24,11.01),'Level-Ausgang')
 def test_death_reset_and_wrong_room_never_count_as_exit(self):
  for event in ('death','reset','tick','wrong'):
   with self.subTest(event=event):
    g=CompletionGate();self.observe(g,'save9.ini',22,0)
    if event=='tick':
     self.assertIsNone(self.observe(g,'save9.ini',22,1,tick=1,restart=True))
     continue
    changed={'deaths':1} if event=='death' else {'restart':True} if event=='reset' else {}
    self.assertIsNone(self.observe(g,'save9.ini',25 if event=='wrong' else 23,1,**changed))
    self.assertIsNone(self.observe(g,'save9.ini',23,8,deaths=1 if event=='death' else 0))
 def test_boss_and_secret_routes_remain_available(self):
  for spot in ('save9.ini','save10.ini'):
   for exit_frame in (24,53):
    g=CompletionGate();self.observe(g,spot,pool(7)[spot]['frame'],0)
    self.assertEqual(self.observe(g,spot,exit_frame,.01),'Level-Ausgang')
 def test_seed_and_loading_support_each_section(self):
  from loading_destination import for_selection
  self.assertEqual(r.defaults()['route_version'],9)
  for spot,frame in [('save9.ini',22),('save10.ini',23)]:
   o=options(9);o.update(level_pool=[spot],level_count=1,boss_pool=[],route_boss_count=0)
   code=r.encode('1234ABCD',o);seed,decoded=r.decode(code);self.assertEqual(decoded,r.normalize(o));self.assertEqual(r.route(seed,decoded),[spot,'boss_solgryn.ini'])
   with patch('loading_destination.for_frame',side_effect=lambda base,frame:frame):
    self.assertEqual(for_selection(SimpleNamespace(base=ROOT),2,'new',dict(seed=code,options=o)),frame)
 def test_progress_both_modes_one_transition_and_target_checkpoint_protection(self):
  for mode in ('randomizer','target'):
   with self.subTest(mode=mode),tempfile.TemporaryDirectory() as d:
    root=Path(d);(root/'run').mkdir();o=options(7,mode);o.update(level_pool=['save9.ini','save10.ini'],level_count=2,boss_pool=[],route_boss_count=0)
    m=dict(run_id='run',session_binding='test',seed='1234ABCD',options=o,pool=pool(7));p=Progress(SimpleNamespace(base=ROOT,root=root),m)
    p.goals={'items':['Awesomesauce'],'bosses':[]};p.data.update(spot='save9.ini',index=0);p.data['checkpoints']={'23':[2000,3000]}
    # A deterministic next part tests Progress's usual pending/arrival protocol.
    if mode=='randomizer':p.plan=['save9.ini','save10.ini','boss_solgryn.ini']
    else:m['pool']={k:v for k,v in m['pool'].items() if k in ('save10.ini','boss_solgryn.ini','save9.ini')}
    def observe(frame,t):
     with patch('native_triggers.time.monotonic',return_value=t):
      return p.observe(frame=frame,position=(16,1679),collectables={},achievements={},disk_achievements={},stats={})
    self.assertIsNone(observe(22,0))
    # Restrict target choices only after observing the origin, to select part 2.
    if mode=='target':
     with patch('native_progress.eligible',return_value={'save10.ini':m['pool']['save10.ini']}):target=observe(23,.01)
    else:target=observe(23,.01)
    self.assertEqual(target,'save10.ini');self.assertEqual(p.destination(target),m['pool'][target]);self.assertEqual(observe(23,4),target)
    p.arrive(target,23,(16,1679));self.assertIsNone(observe(23,5));self.assertIsNone(observe(23,10));self.assertEqual(len(p.data['history']),1)
 def test_advanced_kid_toggle_does_not_downgrade_new_rules(self):
  from menu_model import Menu
  m=Menu.__new__(Menu);m.options=options(7);m.page='advanced';m.advanced_page=0
  m.focus=3+list(r.LEVELS).index('kid_icarus_after');m.advanced_key(13)
  self.assertEqual(m.options['route_version'],7)

if __name__=='__main__':unittest.main()
