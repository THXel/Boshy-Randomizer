"""Unexpected hub portals return to a checkpoint without consuming a route step."""
import unittest
import recover_boshy_routes as src
from transition import hub_guard
from transition.events import commands
from transition.router import STAGES

class HubGuardTests(unittest.TestCase):
 def test_all_guards_are_level_mode_scoped_and_do_not_advance_route(self):
  count=0
  for p,n in src.payloads.items():
   before=src.original_sections(p)
   after,audit=hub_guard.transform(n,before,src.table,src.objects,src.frames[n-1]['instances'])
   count+=len(audit)
   for row in (r for s in after for r in s):
    cs=commands(row)
    if not any(not c[0] and b'BlockedPortal\0' in c[-1] for c in cs):continue
    self.assertTrue(any(c[0] and b'LevelsEnabled\0' in c[-1] for c in cs))
    self.assertTrue(any(c[0] and b'CurrentStage\0' in c[-1] for c in cs))
    acts=[c[-1] for c in cs if not c[0]]
    self.assertFalse(any(b'Done' in a or b'NextId' in a or b'CurrentStage' in a for a in acts))
    for key in ('frame','xPos','yPos'):
     self.assertTrue(any(b'Positions\0' in a and key.encode()+b'\0' in a for a in acts))
  self.assertGreater(count,0)
 def test_legitimate_hub_exits_are_not_guarded(self):
  allowed={s['id'] for s in STAGES.values() if 29 in s['native_exit_frames']}
  self.assertEqual(len(allowed),4)
  for p,n in src.payloads.items():
   _,audit=hub_guard.transform(n,src.original_sections(p),src.table,src.objects,src.frames[n-1]['instances'])
   self.assertFalse({a['stage'] for a in audit}&allowed)
 def test_boss_rush_and_normal_export_do_not_enable_level_portal_guard(self):
  import configparser
  from export_route_probe import save_text
  for mode,levels,expected in [('normal',False,0),('boss_rush',True,0),('randomizer',True,1),('level_rush',True,1)]:
   cfg=configparser.ConfigParser();cfg.read_string(save_text(dict(source='save1.ini',route=['save1.ini','boss_solgryn.ini'],binding='test',options=dict(mode=mode,levels=levels,difficulty='normal'))))
   self.assertEqual(cfg.getint('FusionRouteV4','LevelsEnabled'),expected)
 def test_menu_and_restart_sections_preserved(self):
  for p,n in src.payloads.items():
   before=src.original_sections(p)
   after,_=hub_guard.transform(n,before,src.table,src.objects,src.frames[n-1]['instances'])
   self.assertEqual(before[:2],after[:2])
if __name__=='__main__':unittest.main()
