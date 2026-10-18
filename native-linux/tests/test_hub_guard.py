"""Illegal hub shortcuts reset a checkpoint, never complete/reroll a stage."""
import sys,unittest,threading,copy
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from contextlib import nullcontext
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from hub_guard import HubGuard
from fast_exit import FastExit
from lab import IniReadInProgress
from native_triggers import CompletionGate
import native_triggers
class HubGuardTest(unittest.TestCase):
 def player(self,spot='save2.ini',frame=5,**point):
  gate=CompletionGate();data=dict(index=3,spot=spot,pending=None,history=[{'target':spot}],baseline=[frame,30,1850])
  p=NS(m={'options':{'levels':True,'mode':'randomizer'},'pool':{spot:dict(frame=frame,category='rooms',**point)}},progress=NS(data=data,gate=gate,mini_gate=NS(snapshot=lambda:{}),save=Mock(),trace=Mock(),pause=Mock(),rebase=Mock()),watch=NS(down=False,pressed=threading.Event(),ready=threading.Event()),rules=NS(module=lambda n:native_triggers),bridge=NS(),metadata={'menu':123},save_name='SaveFile2.ini',can_transition=Mock(return_value=True),characters=Mock(),shots=Mock())
  p.hub_guard=HubGuard(p);p.fast_exit=FastExit(p);p.fast_exit.command=Mock(return_value=True);p.fast_exit.control=lambda:(0x42584531,0,0,0)
  return p,p.hub_guard
 def remember(self,p,g,frame=5,x=1234,y=567):
  cp=dict(frame=frame,xpos=x,ypos=y);g.remember(frame,cp,dict(cp),True);return cp
 def test_latest_confirmed_save_not_stage_start(self):
  p,g=self.player();self.remember(p,g);cp=self.remember(p,g,x=1800,y=777)
  p.progress.data['baseline']=[29,100,100]
  before=copy.deepcopy(p.progress.data)
  with patch('hub_guard.protect',return_value=nullcontext()),patch('hub_guard.transition') as move,self.assertRaises(IniReadInProgress):g.restore(5,29)
  move.assert_called_once_with(p.bridge,5,1800,777,'SaveFile2.ini',stabilize=True)
  for k in ('index','spot','history','pending'):self.assertEqual(before[k],p.progress.data[k])
  p.characters.prepare.assert_not_called();p.shots.observe.assert_not_called();self.assertNotIn('hub_return',p.progress.data)
 def test_partial_save_and_hub_coordinates_cannot_replace_checkpoint(self):
  p,g=self.player();cp=self.remember(p,g);want=dict(g.checkpoint())
  for frame,live,disk,settled in [(5,{**cp,'xpos':0},cp,True),(5,cp,cp,False),(29,{'frame':29,'xpos':0,'ypos':0},{'frame':29,'xpos':0,'ypos':0},True)]:g.remember(frame,live,disk,settled)
  self.assertEqual(g.checkpoint(),want)
 def test_hub_fallback_uses_original_saved_position_after_resume(self):
  p,g=self.player();cp=dict(frame=5,xpos=1234,ypos=567);g.remember(29,cp,dict(cp),True)
  with patch('hub_guard.protect',return_value=nullcontext()),patch('hub_guard.transition') as move,self.assertRaises(IniReadInProgress):g.restore(29)
  self.assertEqual(move.call_args.args[1:4],(5,1234,567))
 def test_allowed_hub_exits_are_untouched(self):
  for spot,frame,segment,category in [('save14.ini',33,None,'rooms'),('boss21.ini',54,None,'bosses'),('boss_kappa',37,'kappa','bosses')]:
   p,g=self.player(spot,frame,segment=segment);p.m['pool'][spot]['category']=category
   self.remember(p,g,frame);self.assertIsNone(g.context());self.assertFalse(g.restore(29));self.assertFalse(g.intercept(frame))
 def test_no_trigger_on_regular_room_or_when_level_randomizer_disabled(self):
  p,g=self.player();self.remember(p,g);self.assertFalse(g.restore(5));p.m['options']['levels']=False;self.assertFalse(g.restore(29))
 def test_target_mode_has_same_rule(self):
  p,g=self.player();p.m['options']['mode']='target';self.remember(p,g);self.assertTrue(g.intercept(5))
 def test_stale_checkpoint_cannot_return_to_previous_stage(self):
  p,g=self.player();self.remember(p,g);p.progress.data['index']+=1;self.assertIsNone(g.checkpoint());self.assertFalse(g.restore(29))
 def test_pending_route_wins_and_cannot_be_overwritten(self):
  p,g=self.player();self.remember(p,g);p.progress.data['pending']='boss3.ini';self.assertFalse(g.restore(29));self.assertFalse(g.intercept(5))
 def test_failure_retains_return_for_recovery(self):
  p,g=self.player();self.remember(p,g)
  with patch('hub_guard.protect',return_value=nullcontext()),patch('hub_guard.transition',side_effect=TimeoutError),self.assertRaises(TimeoutError):g.restore(5,29)
  self.assertEqual(p.progress.data['hub_return']['xpos'],1234)
  with patch('hub_guard.protect',return_value=nullcontext()),patch('hub_guard.transition') as move,self.assertRaises(IniReadInProgress):g.restore(5)
  move.assert_called_once();self.assertNotIn('hub_return',p.progress.data)
 def test_blocking_dialog_or_held_reset_cannot_advance_route(self):
  for mode in ('dialog','reset'):
   p,g=self.player();self.remember(p,g)
   if mode=='dialog':p.can_transition.return_value=False
   else:p.watch.down=True
   with self.assertRaises(IniReadInProgress):g.restore(5,29)
   self.assertEqual(p.progress.data['index'],3)
 def test_arm_includes_hub_and_native_notice_but_capture_does_not_include_flag(self):
  p,g=self.player();self.remember(p,g);p.progress.gate.observe('save2.ini',p.m['pool']['save2.ini'],5,{},{},{'deaths':0},40)
  p.fast_exit.arm(5,{'deaths':0});self.assertIn(29,p.fast_exit.armed[4]);self.assertNotIn(64,p.fast_exit.armed[4]);self.assertIn(64,p.fast_exit.command.call_args.args[2])
 def test_empty_segment_exits_still_reject_hub(self):
  p,g=self.player(segment='before_kracko');self.remember(p,g);p.fast_exit.arm(5,{'deaths':0});self.assertEqual(p.fast_exit.armed[4],(29,))
if __name__=='__main__':unittest.main()
