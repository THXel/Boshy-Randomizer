import sys,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from live_session import LiveSession
from native_session import SessionStore
from native_player import Player
from menu_navigation import load_slot

class MenuTransactions(unittest.TestCase):
 def make(self):
  store=SessionStore('/unused',read_save=Mock(),encode_save=Mock(),game_running=lambda:True)
  game=Mock();game.bridge.snapshot.return_value={'scene':1,'run':123}
  with patch('live_session.NativeReader') as reader:
   reader.return_value.read.return_value=(0x42524c31,1,0,1,123,1,0,0)
   live=LiveSession(store,game)
  live.command=Mock(return_value=(0x42524c31,1,0,1,123,1,0,0))
  return store,live
 def test_live_mutation_requires_native_menu_lock(self):
  store,live=self.make()
  with self.assertRaises(RuntimeError):store._stopped()
  with live.transaction():store._stopped();self.assertIsNotNone(store._menu_guard)
  self.assertIsNone(store._menu_guard)
  with self.assertRaises(RuntimeError):store._stopped()
  self.assertEqual([c.args[0] for c in live.command.call_args_list],[1,3])
 def test_exception_releases_lock_and_does_not_swallow_error(self):
  store,live=self.make()
  with self.assertRaisesRegex(ValueError,'fixture'):
   with live.transaction():raise ValueError('fixture')
  self.assertIsNone(store._menu_guard);self.assertIsNone(live.lock_run)
  self.assertEqual([c.args[0] for c in live.command.call_args_list],[1,3])
 def test_scene_or_generation_change_forbids_more_writes(self):
  for snapshot in ({'scene':2,'run':123},{'scene':1,'run':124}):
   store,live=self.make()
   with self.assertRaises(RuntimeError):
    with live.transaction():
     live.game.bridge.snapshot.return_value=snapshot;store._stopped()
   self.assertIsNone(store._menu_guard)
 def test_nested_transaction_is_rejected_without_releasing_outer_lock(self):
  store,live=self.make()
  with live.transaction():
   with self.assertRaises(RuntimeError):
    with live.transaction():pass
   store._stopped()
  self.assertEqual(live.command.call_count,2)
 def test_start_refuses_other_run_before_loading_or_launching(self):
  store=Mock(root=Path('/unused'));m={'run_id':'a'*32};p=Player(store,m)
  game=Mock(metadata={'menu':999,'context':111});game.bridge.read.return_value=b'b'*32
  with patch('native_player.launch') as launch,patch('menu_navigation.load_slot') as load:
   with self.assertRaises(RuntimeError):p.start(game=game)
  launch.assert_not_called();load.assert_not_called()
 def test_loader_all_slot_pairs_in_same_non_wrapping_menu(self):
  for start in (1,2,3):
   for target in (1,2,3):
    h=[0]*16;h[0]=0x424d4e31;h[2]=2;h[9]=start;snap={'scene':1};keys=[]
    def send(key):
     keys.append(key)
     if key=='Right':h[9]=min(3,h[9]+1)
     elif key=='Left':h[9]=max(1,h[9]-1)
     elif key=='Return':snap['scene']=2
    bridge=Mock();bridge.snapshot.side_effect=lambda:dict(snap)
    with patch('menu_navigation.header',side_effect=lambda *a:list(h)),patch('menu_navigation.key',side_effect=send),patch('menu_navigation.dismiss_startup_notice',return_value=False),patch('menu_navigation.time.sleep'):
     load_slot(bridge,1,target)
    self.assertEqual(h[9],target);self.assertEqual(keys,(['Right']*(target-start) if target>start else ['Left']*(start-target))+['Return'])
if __name__=='__main__':unittest.main()
