import json,sys,tempfile,time,unittest,zipfile
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
from concurrent.futures import Future
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from transition_timing import Timings,observe
from debug_data import Recorder,Chord
from debug_window import Window

class TransitionMeasurements(unittest.TestCase):
 def test_detect_request_arrival_and_wait_are_separate(self):
  clock=Mock(return_value=10);t=Timings(clock);t.begin(0,'level','boss','exit')
  clock.return_value=12;t.begin(0,'level','boss');self.assertEqual(len(t.rows),1)
  t.phase('requested');clock.return_value=12.125;t.phase('arrived');clock.return_value=12.2;t.complete()
  row=t.snapshot()[0];self.assertEqual(row['detection_to_request_ms'],2000);self.assertEqual(row['request_to_arrival_ms'],125);self.assertEqual(row['total_ms'],2125);self.assertEqual(row['status'],'confirmed')
 def test_pending_retry_and_no_fabricated_arrival(self):
  clock=Mock(return_value=10);t=Timings(clock);t.begin(0,'a','b');clock.return_value=11
  row=t.snapshot()[0];self.assertEqual(row['elapsed_ms'],1000);self.assertIsNone(row['total_ms']);self.assertIsNone(row['detection_to_request_ms'])
  t.phase('requested');clock.return_value=12;t.phase('requested');clock.return_value=13;t.phase('arrived');t.complete()
  row=t.snapshot()[0];self.assertEqual(row['attempts'],2);self.assertEqual(row['request_to_arrival_ms'],2000);self.assertEqual(row['total_ms'],3000)
 def test_already_there_and_bounded_immutable_history(self):
  t=Timings()
  for i in range(40):t.begin(i,'same','same');t.complete()
  rows=t.snapshot();self.assertEqual(len(rows),32);self.assertEqual(rows[0]['index'],8);self.assertEqual(rows[-1]['status'],'already_at_target');self.assertIsNone(rows[-1]['request_to_arrival_ms'])
  rows[-1]['target']='changed';self.assertEqual(t.snapshot()[-1]['target'],'same')
 def test_abandoned_measurement_and_callback_failures_do_not_touch_game(self):
  t=Timings();t.begin(0,'a','b');t.begin(1,'c','d');self.assertEqual(t.snapshot()[0]['status'],'interrupted')
  observe(NS(),'requested');callback=Mock(side_effect=RuntimeError('diagnostic failure'));observe(NS(transition_observer=callback),'arrived');callback.assert_called_once_with('arrived')
 def test_native_transition_orders_telemetry(self):
  import lab
  events=[];b=NS(snapshot=Mock(return_value={'scene':3,'next':0,'frame_count':2}),cmd=Mock(return_value={'requested':True}),transition_observer=events.append)
  positions={k:{'value':str(v)} for k,v in [('frame',4),('xpos',100),('ypos',200)]}
  with patch('lab.time.sleep'),patch('PY.file_utils.smart_read',return_value=('',None)),patch('PY.ini_utils.apply_values_in_section',return_value='prepared'),patch('PY.save_utils.encrypt_save_atomic',return_value=True),patch('lab.ini_object_ids',return_value={'Ini++':109}),patch('lab.ini_items',return_value=positions):
   lab.transition(b,4,100,200);self.assertEqual(events,['requested','arrived']);events.clear();b.cmd.return_value={'requested':False}
   with self.assertRaises(AssertionError):lab.transition(b,4,100,200)
   self.assertEqual(events,[])

class ProblemMarkers(unittest.TestCase):
 def test_history_is_immutable_bounded_and_deduplicated(self):
  r=Recorder('/unused');state={'sequence':0,'time':100,'options':{'x':1}};r.observe(state);state['options']['x']=99;r.observe(state)
  self.assertEqual(len(r.ring),1);self.assertEqual(r.ring[0]['options']['x'],1)
  r.observe({'sequence':1,'time':221});self.assertEqual(len(r.ring),1)
  for i in range(500):r.observe({'sequence':i+2,'time':222+i*.001})
  self.assertEqual(len(r.ring),240)
 def test_marker_does_not_stop_or_mix_active_recording(self):
  with tempfile.TemporaryDirectory() as d:
   r=Recorder(d);state=dict(sequence=1,time=time.time(),run_id='run',share_seed='BR9-example',player_position=[1,2],options={'extras':{'one_hp':True}},transition_timings=[{'status':'confirmed'}])
   r.observe(state);r.start();stream=r.stream;active=r.active;frozen,marked,note=r.marker_snapshot(state,'Expected an exit')
   state['player_position'][0]=999;r.observe({**state,'sequence':2})
   path=frozen.export_marker(marked,note);self.assertIs(r.stream,stream);self.assertEqual(r.active,active);self.assertIsNone(r.last_export)
   with zipfile.ZipFile(path) as z:
    report=json.loads(z.read('bericht.json'));last=report['last_state'];self.assertEqual(last['player_position'],[1,2]);self.assertEqual(last['share_seed'],'BR9-example');self.assertTrue(last['options']['extras']['one_hp']);self.assertIn('problem_marker',last)
    history=[json.loads(x) for x in z.read('zeitverlauf.jsonl').decode().splitlines()];self.assertEqual(len(history),1);self.assertEqual(history[0]['player_position'],[1,2]);self.assertEqual(json.loads(z.read('transition-timings.json')),state['transition_timings'])
   self.assertEqual(json.loads((Path(d)/'debug-reports/latest-marker.json').read_text())['path'],str(path));record=r.finish('continued');self.assertNotEqual(path,record)
   with zipfile.ZipFile(record) as z:self.assertEqual(len(z.read('zeitverlauf.jsonl').splitlines()),2)
 def test_old_history_is_pruned_even_without_new_samples(self):
  r=Recorder('/unused');r.observe({'sequence':1,'time':10})
  with patch('debug_data.time.time',return_value=200):frozen,marked,note=r.marker_snapshot(r.ring[-1])
  self.assertEqual(len(frozen.ring),0);self.assertEqual(marked['problem_marker']['observation_age_seconds'],190)
 def test_shortcut_one_shot_and_focus_gate(self):
  c=Chord();self.assertFalse(c.update(True,False));self.assertFalse(c.update(True,True));c.update(False,False);self.assertTrue(c.update(True,True));self.assertFalse(c.update(True,True))
 def test_window_marker_is_background_only_and_debounced(self):
  with tempfile.TemporaryDirectory() as d:
   w=Window.__new__(Window);w.closing=False;w.marker_future=None;w.marker_last=-float('inf');w.state={'sequence':1,'time':time.time()};w.recorder=Recorder(d);w.recorder.observe(w.state);w.note=Mock();w.note.get.return_value='note';w.exporter=Mock();future=Future();w.exporter.submit.return_value=future;w.marker_button=Mock();w.notice=Mock();w.show=Mock();w.command=Mock()
   w.mark_problem();w.mark_problem();w.exporter.submit.assert_called_once();w.show.assert_not_called();w.command.assert_not_called();self.assertIs(w.marker_future,future)
   future.set_exception(OSError('disk full'));w.marker_result();self.assertIsNone(w.marker_future);self.assertIn('disk full',w.notice.set.call_args.args[0])
 def test_position_pointer_reuse_is_rejected(self):
  import struct
  from debug_runtime import DebugRuntime
  r=DebugRuntime.__new__(DebugRuntime);r.player_key=('run',2,3,100);r.player_ptr=200;r.player_oi=9;r.player_handle=7;r.player_slot=1;r.player_tick=5
  raw=bytearray(100);struct.pack_into('<h',raw,0,8);struct.pack_into('<H',raw,18,9);struct.pack_into('<h',raw,24,2)
  player=NS(m={'run_id':'run'},bridge=NS(read=Mock(side_effect=[struct.pack('<I',200),raw])))
  self.assertIsNone(r.position(player,dict(run=2,scene=3,object_list=100,frame_count=6),retry=False));self.assertIsNone(r.player_ptr)
 def test_position_reacquires_after_reset_in_same_sample(self):
  import struct
  from debug_runtime import DebugRuntime
  r=DebugRuntime.__new__(DebugRuntime);r.player_key=('run',2,3,100);r.player_ptr=200;r.player_oi=9;r.player_handle=7;r.player_slot=1;r.player_tick=5
  snap=dict(run=2,scene=3,object_list=100,frame_count=6)
  raw=bytearray(160);struct.pack_into('<h',raw,0,8);struct.pack_into('<H',raw,18,9);struct.pack_into('<h',raw,24,2);struct.pack_into('<I',raw,28,300);struct.pack_into('<i',raw,76,40);struct.pack_into('<i',raw,84,50)
  obj=dict(type=2,ptr=201,oi=9,handle=8,slot=1,raw=raw.hex())
  player=NS(m={'run_id':'run'},bridge=NS(snapshot=Mock(return_value=snap),read=Mock(side_effect=[struct.pack('<I',200),raw,b'Player',struct.pack('<I',201),raw])))
  with patch('lab.objects',return_value=[obj]):self.assertEqual(r.position(player,snap),[40,50])
  self.assertEqual(r.player_ptr,201)
if __name__=='__main__':unittest.main()
