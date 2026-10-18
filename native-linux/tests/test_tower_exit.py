import sys,types,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import native_triggers
from runtime_versions import repair_tower_exit

class TowerExit(unittest.TestCase):
 def modules(self):
  old=(ROOT/'native_triggers.py').read_text().replace('TOWER_EXIT_VERSION=1','TOWER_EXIT_VERSION=0')
  old=old.replace("        if self.candidate and", "        if point['frame']==51 and frame==35 and position!=(7871,553):return None\n        if self.candidate and")
  mod=types.ModuleType('old_tower');exec(old,mod.__dict__)
  repair_tower_exit('native_triggers',mod);method=mod.CompletionGate.observe
  repair_tower_exit('native_triggers',mod);self.assertIs(method,mod.CompletionGate.observe)
  return native_triggers,mod
 def test_door_edge_and_guards(self):
  point={'frame':51,'category':'rooms'}
  for mod in self.modules():
   for case in ('door','arrival','reset','death','wrong','same'):
    with self.subTest(module=mod.__name__,case=case):
     g=mod.CompletionGate()
     g.observe('save20.ini',point,35 if case=='arrival' else 51,{},{},{'deaths':0},100)
     result=g.observe('save20.ini',point,38 if case=='wrong' else 51 if case=='same' else 35,{},{},{'deaths':int(case=='death')},101,case=='reset',position=(7871,559))
     self.assertEqual(result,'Level-Ausgang' if case=='door' else None)
if __name__=='__main__':unittest.main()
