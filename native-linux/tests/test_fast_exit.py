import sys,unittest,threading
from pathlib import Path
from types import SimpleNamespace as NS
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from fast_exit import FastExit
from native_triggers import CompletionGate
import native_triggers
class FastExitTest(unittest.TestCase):
 def player(self,spot='save1.ini',frame=3):
  point=dict(frame=frame,category='rooms' if spot.startswith('save') else 'bosses')
  g=CompletionGate();g.observe(spot,point,frame,{}, {},{'deaths':2},100)
  p=NS(m={'options':{'levels':True},'pool':{spot:point}},progress=NS(data={'index':0,'spot':spot,'pending':None},gate=g),watch=NS(down=False,pressed=threading.Event()),rules=NS(module=lambda n:native_triggers))
  return p,FastExit(p)
 def test_only_observed_origin_can_arm(self):
  p,f=self.player();self.assertEqual(f.allowed(3),(4,33));self.assertEqual(f.allowed(4),());p.progress.gate.seen_origin=False;self.assertEqual(f.allowed(3),())
 def test_special_gates_and_resets_are_not_shortened(self):
  for spot,frame in [('boss23.ini',60),('save23.ini',51),('boss_solgryn.ini',46)]:
   p,f=self.player(spot,frame);self.assertEqual(f.allowed(frame),())
  p,f=self.player();p.watch.down=True;self.assertEqual(f.allowed(3),());p.watch.down=False;p.watch.pressed.set();self.assertEqual(f.allowed(3),())
 def test_stale_capture_does_not_finish_new_stage_or_death(self):
  p,f=self.player();f.control=lambda:(0x42584531,8,0,259);calls=[];f.command=lambda *a:calls.append(a)
  f.armed=(0,'save1.ini',3,2,(4,33));self.assertEqual(f.captured(3,{'deaths':2}),4)
  self.assertIsNone(f.captured(3,{'deaths':3}));self.assertEqual(calls[-1],(2,2))
 def test_wrong_destination_and_unarmed_capture_rejected(self):
  p,f=self.player();f.control=lambda:(0x42584531,8,0,260);f.command=lambda *a:True
  self.assertIsNone(f.captured(3,{'deaths':2}));f.armed=(0,'save1.ini',3,2,(4,33));self.assertIsNone(f.captured(3,{'deaths':2}))
if __name__=='__main__':unittest.main()
