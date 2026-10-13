"""A failed UI construction must never leak the loading audio gate."""
import unittest,sys,types
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import loading_screen
class LoadingCleanup(unittest.TestCase):
 def test_audio_closed_when_window_creation_fails(self):
  calls=[]
  class Gate:
   def __init__(self,pid):calls.append(('open',pid))
   def close(self):calls.append(('close',))
  fake_tk=types.ModuleType('tkinter')
  def fail():raise RuntimeError('simulated display error')
  fake_tk.Tk=fail
  fake_pil=types.ModuleType('PIL');fake_pil.Image=object();fake_pil.ImageTk=object();fake_pil.ImageOps=object()
  fake_audio=types.ModuleType('loading_audio');fake_audio.AudioGate=Gate
  with patch.dict(sys.modules,{'tkinter':fake_tk,'PIL':fake_pil,'loading_audio':fake_audio}):
   with self.assertRaisesRegex(RuntimeError,'simulated display error'):loading_screen.window({'pid':123})
  self.assertEqual(calls,[('open',123),('close',)])
if __name__=='__main__':unittest.main()
