import sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import game_focus
class Root:
 def __init__(self):self.calls=[]
 def after(self,delay,callback):self.calls.append((delay,callback))
 def tick(self):self.calls.pop(0)[1]()
class StartupFocus(unittest.TestCase):
 def test_late_tracker_returns_focus_once(self):
  root=Root()
  with patch.object(game_focus,'activate_game',return_value=True) as activate:
   game_focus.handoff_tracker_startup(root);self.assertFalse(activate.called)
   root.tick();activate.assert_called_once();self.assertEqual(root.calls,[])
 def test_game_not_ready_retries_then_stops(self):
  root=Root()
  with patch.object(game_focus,'activate_game',side_effect=[RuntimeError('not ready'),True]) as activate:
   game_focus.handoff_tracker_startup(root);root.tick();self.assertEqual(len(root.calls),1)
   root.tick();self.assertEqual(activate.call_count,2);self.assertEqual(root.calls,[])
 def test_missing_game_does_not_force_focus_forever(self):
  root=Root()
  with patch.object(game_focus.time,'monotonic',side_effect=[0,21]),patch.object(game_focus,'activate_game') as activate:
   game_focus.handoff_tracker_startup(root);root.tick();activate.assert_not_called();self.assertEqual(root.calls,[])
if __name__=='__main__':unittest.main()
