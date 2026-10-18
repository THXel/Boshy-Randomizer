import json,sys,unittest,struct
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from spawn_guard import perform,position_matches,player_position,PLAYER_OIS,POSITION_FRAMES
from transition_timing import Timings
import lab

class SpawnGuard(unittest.TestCase):
 def snap(self,**kw):return dict(scene=4,next=0,frame_count=3,run=200,object_list=0x30000,objects=1,**kw)
 def test_exactly_one_reset_then_real_position_confirmation(self):
  b=NS(snapshot=Mock(return_value=self.snap()),transition_observer=Mock());load=Mock()
  with patch('spawn_guard.player_position',return_value=[30,1871]):perform(b,5,30,1850,load)
  self.assertEqual(load.call_count,2);self.assertEqual(b.last_spawn_check['status'],'confirmed');self.assertEqual(b.last_spawn_check['target_resets'],1)
  self.assertEqual([c.args[0] for c in b.transition_observer.call_args_list],['spawn-reset','arrived'])
 def test_wrong_warp_cannot_confirm_or_start_reset_loop(self):
  b=NS(snapshot=Mock(return_value=self.snap()),transition_observer=Mock());load=Mock()
  with patch('spawn_guard.player_position',return_value=[3400,300]),patch('spawn_guard.time.monotonic',side_effect=[0,.1,2]),patch('spawn_guard.time.sleep'),self.assertRaises(TimeoutError):perform(b,5,30,1850,load)
  self.assertEqual(load.call_count,2);self.assertEqual(b.last_spawn_check['status'],'failed');self.assertEqual(b.last_spawn_check['position'],[3400,300]);self.assertNotIn('arrived',[c.args[0] for c in b.transition_observer.call_args_list])
 def test_missing_player_waits_but_never_confirms(self):
  b=NS(snapshot=Mock(return_value=self.snap()));load=Mock()
  with patch('spawn_guard.player_position',return_value=None),patch('spawn_guard.time.monotonic',side_effect=[0,.1,2]),patch('spawn_guard.time.sleep'),self.assertRaises(TimeoutError):perform(b,5,30,1850,load)
  self.assertEqual(load.call_count,2)
 def test_failed_first_load_never_attempts_a_reset(self):
  b=NS();load=Mock(side_effect=OSError('save failed'))
  with self.assertRaises(OSError):perform(b,5,30,1850,load)
  load.assert_called_once();self.assertEqual(b.last_spawn_check['target_resets'],0)
 def test_fixed_boss_spawn_and_physics_margins(self):
  self.assertTrue(position_matches(4,[1963,328],[27,440]));self.assertTrue(position_matches(5,[30,1850],[30,1871]));self.assertFalse(position_matches(5,[30,1850],[670,1871]));self.assertFalse(position_matches(4,[100,100],None))
 def test_all_configured_scenes_have_verified_player_identity(self):
  from trigger_audit import points
  for point in points(ROOT).values():self.assertIn(point['frame']-1,PLAYER_OIS)
 def test_player_reader_rejects_reused_pointer(self):
  snap=self.snap();raw=bytearray(128);struct.pack_into('<H',raw,18,358);struct.pack_into('<h',raw,24,2)
  b=NS(read=Mock(side_effect=[struct.pack('<II',0x40000,0),raw[:26],raw,struct.pack('<I',0x50000)]))
  with self.assertRaises(lab.IniReadInProgress):player_position(b,snap)
 def test_player_reader_returns_actual_coordinates_not_ini(self):
  snap=self.snap();raw=bytearray(128);struct.pack_into('<H',raw,18,358);struct.pack_into('<h',raw,24,2);struct.pack_into('<i',raw,76,3400);struct.pack_into('<i',raw,84,300)
  b=NS(read=Mock(side_effect=[struct.pack('<II',0x40000,0),raw[:26],raw,struct.pack('<I',0x40000)]),snapshot=Mock(return_value=snap))
  self.assertEqual(player_position(b,snap),[3400,300])
 def test_same_room_reload_requires_fresh_generation(self):
  before=dict(scene=4,next=0,frame_count=80,run=200,object_list=300);busy={**before,'next':3};fresh={**before,'frame_count':2}
  b=NS(snapshot=Mock(side_effect=[before,before,busy,fresh]),cmd=Mock(return_value={'requested':True}))
  pos={k:{'value':str(v)} for k,v in [('frame',5),('xpos',30),('ypos',1850)]}
  with patch('lab.time.sleep'),patch('PY.file_utils.smart_read',return_value=('',None)),patch('PY.ini_utils.apply_values_in_section',return_value='prepared'),patch('PY.save_utils.encrypt_save_atomic',return_value=True),patch('lab.ini_object_ids',return_value={'Ini++':109}),patch('lab.ini_items',return_value=pos) as read:
   result=lab._transition(b,5,30,1850,'SaveFile2.ini',require_generation=True)
  self.assertEqual(result['frame_count'],2);read.assert_called_once()
 def test_same_scene_pause_releases_only_after_engine_processing(self):
  before=dict(scene=4,next=0,frame_count=80,run=200,object_list=300);busy={**before,'next':3};fresh={**before,'frame_count':1};ready={**fresh,'frame_count':2}
  b=NS(spawn_guard_address=0x10000,snapshot=Mock(side_effect=[before,before,busy,fresh,ready]),cmd=Mock(return_value={'requested':True}))
  pos={k:{'value':str(v)} for k,v in [('frame',5),('xpos',30),('ypos',1850)]}
  with patch('lab.time.sleep'),patch('PY.file_utils.smart_read',return_value=('',None)),patch('PY.ini_utils.apply_values_in_section',return_value='prepared'),patch('PY.save_utils.encrypt_save_atomic',return_value=True),patch('lab.ini_object_ids',return_value={'Ini++':109}),patch('lab.ini_items',return_value=pos):lab._transition(b,5,30,1850,'SaveFile2.ini',require_generation=True)
  self.assertEqual([c.args[0] for c in b.cmd.call_args_list],['scene 4 4','menu 10000 60 1'])
 def test_timing_includes_reset_before_arrival(self):
  clock=Mock(return_value=0);t=Timings(clock);t.begin(0,'a','b');t.phase('requested');clock.return_value=.1;t.phase('spawn-reset');t.phase('requested');self.assertIsNone(t.snapshot()[0]['total_ms']);clock.return_value=.2;t.phase('arrived');t.complete()
  self.assertEqual(t.snapshot()[0]['total_ms'],200);self.assertEqual(t.snapshot()[0]['target_resets'],1)
 def test_native_checkpoint_settling_requires_close_live_player(self):
  from spawn_guard import adjusted_checkpoint
  b=NS();snap=dict(scene=10,next=0);pos={k:{'value':str(v)} for k,v in [('frame',11),('xpos',35),('ypos',143)]}
  with patch('spawn_guard.player_position',return_value=[35,143]):self.assertTrue(adjusted_checkpoint(b,snap,11,35,140,pos))
  for actual in ([670,143],[35,149],None):
   with patch('spawn_guard.player_position',return_value=actual):self.assertFalse(adjusted_checkpoint(b,snap,11,35,140,pos))
  for wrong in ({**snap,'scene':9},{**snap,'next':1}):
   with patch('spawn_guard.player_position') as read:self.assertFalse(adjusted_checkpoint(b,wrong,11,35,140,pos));read.assert_not_called()
  pos['ypos']['value']='149'
  with patch('spawn_guard.player_position') as read:self.assertFalse(adjusted_checkpoint(b,snap,11,35,140,pos));read.assert_not_called()
if __name__=='__main__':unittest.main()
