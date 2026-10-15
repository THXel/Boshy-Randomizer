import sys,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import menu_navigation as nav
class StartupNotice(unittest.TestCase):
 def test_closes_only_visible_notice_owned_by_this_game(self):
  def w(pid,title,visible=True):return SimpleNamespace(pid=pid,title=title,isVisible=visible,_hWnd=123)
  windows=[w(1,'Playable characters'),w(2,'Playable characters'),w(1,'Confirm deletion'),w(1,'Playable characters',False)]
  with patch.object(nav,'game_window',return_value=SimpleNamespace(pid=1)),patch('PY.platform_windows.getAllWindows',return_value=windows),patch.object(nav.subprocess,'run') as run:
   self.assertTrue(nav.dismiss_startup_notice());run.assert_called_once_with(['wmctrl','-ic','0x7b'],check=True,timeout=2)
 def test_no_game_does_not_touch_any_window(self):
  with patch.object(nav,'game_window',side_effect=RuntimeError('No game')),patch.object(nav.subprocess,'run') as run:
   self.assertFalse(nav.dismiss_startup_notice());run.assert_not_called()
