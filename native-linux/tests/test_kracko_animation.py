import unittest,types
from pathlib import Path
import minibosses
from runtime_versions import repair_kracko_animation

class KrackoAnimation(unittest.TestCase):
 def gates(self):
  old=types.ModuleType('legacy_minibosses')
  text=Path(minibosses.__file__).read_text().replace(">=(4.0 if segment=='kracko' else 1.0) else None",">=1.0 else None")
  exec(compile(text,'legacy_minibosses','exec'),old.__dict__)
  repair_kracko_animation('minibosses',old)
  repair_kracko_animation('minibosses',old)
  return (minibosses.Gate,old.Gate)
 def observe(self,g,t,hp=0,tick=None,deaths=0,alive=True,obj=42):
  return g.observe('boss2.ini',0,dict(frame=5,segment='kracko'),dict(frame=5,tick=int(t*100) if tick is None else tick,position=[3300,200],hp=hp,boss_object=obj,player_alive=alive),deaths,t)
 def test_four_seconds_after_confirmed_hp_zero_in_new_and_saved_rules(self):
  for cls in self.gates():
   g=cls();self.assertIsNone(self.observe(g,0,hp=5))
   for t in (1,2,3,4.999):self.assertIsNone(self.observe(g,t))
   self.assertEqual(self.observe(g,5,obj=None,hp=None),'Kracko besiegt')
 def test_cold_load_death_reset_and_respawn_do_not_complete(self):
  for cls in self.gates():
   g=cls();self.assertIsNone(self.observe(g,5))
   for changes in (dict(tick=0),dict(deaths=1),dict(alive=False),dict(obj=99)):
    g=cls();self.observe(g,0,hp=5);self.observe(g,1)
    self.assertIsNone(self.observe(g,6,**changes))
    self.assertIsNone(self.observe(g,12,obj=None,hp=None))
if __name__=='__main__':unittest.main()
