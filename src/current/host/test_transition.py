"""Regression invariants against the actual original Cheetahman event stream."""
import unittest
from recover_boshy_transition import events, original_sections
from transition.cheetah import transform
from transition.events import commands

class TransitionTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.old=original_sections(events);cls.new,cls.audit=transform(cls.old)
 def test_only_exit_section_changes(self):
  self.assertEqual(len(self.old),len(self.new))
  self.assertEqual([i for i,(a,b) in enumerate(zip(self.old,self.new)) if a!=b],[101])
  self.assertEqual(self.old[101][1:],self.new[101][3:])
 def test_fallback_preserves_original_actions(self):
  old=[c[4] for c in commands(self.old[101][0]) if not c[0]]
  new=[c[4] for c in commands(self.new[101][0]) if not c[0]]
  self.assertEqual(old,new)
  self.assertEqual(self.new[101][0][2],3)
 def test_routes_require_collision_and_victory(self):
  collision=commands(self.old[101][0])[0][4]
  victory=commands(self.old[91][152])[0][4]
  for row in self.new[101][1:3]:
   cond=[c[4] for c in commands(row) if c[0]]
   self.assertEqual(cond[:2],[collision,victory]);self.assertEqual(len(cond),3)
 def test_checkpoint_is_persisted_before_original_jump(self):
  jump=commands(self.old[101][0])[-1][4]
  for row in self.new[101][1:3]:
   acts=[c for c in commands(row) if not c[0]]
   self.assertEqual([(c[1],c[2]) for c in acts],[(-1,3)]*3+[(33,94)]*4+[(-1,14),(-3,2)])
   self.assertIn(b'save\0',acts[-2][4]);self.assertEqual(acts[-1][4],jump)
   for c,key in zip(acts[3:7],[b'xPos',b'yPos',b'frame',b'CheetahDone']):self.assertIn(key,c[4])
if __name__=='__main__':unittest.main()
