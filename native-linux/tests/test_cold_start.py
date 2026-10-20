"""Fresh Windows startup waits for the owned process, with a bounded deadline."""
import sys,unittest
from pathlib import Path
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import window_position as wp
class ColdStart(unittest.TestCase):
 def test_windows_slow_start_past_original_deadline(self):
  window=object();process=Mock();process.is_running.return_value=True
  with patch.object(wp,'WINDOWS',True),patch.object(wp.time,'monotonic',side_effect=[0,16,90]),patch.object(wp.time,'sleep'),patch.object(wp,'game_window',side_effect=[RuntimeError('not ready'),RuntimeError('not ready'),window]),patch('psutil.Process',return_value=process):
   self.assertIs(wp.wait_for_game(process_id=12),window)
 def test_exited_process_fails_without_waiting_for_full_deadline(self):
  process=Mock();process.is_running.return_value=False
  with patch.object(wp,'game_window',side_effect=RuntimeError('not ready')),patch('psutil.Process',return_value=process):
   with self.assertRaisesRegex(RuntimeError,'exited'):wp.wait_for_game(process_id=12)
 def test_deadlines_remain_bounded(self):
  for windows,explicit,clock in [(False,None,16),(True,None,181),(True,5,6)]:
   with self.subTest(windows=windows,explicit=explicit),patch.object(wp,'WINDOWS',windows),patch.object(wp.time,'monotonic',side_effect=[0,clock]),patch.object(wp,'game_window',side_effect=RuntimeError('not ready')):
    with self.assertRaisesRegex(RuntimeError,'not ready'):wp.wait_for_game(timeout=explicit)
if __name__=='__main__':unittest.main()
