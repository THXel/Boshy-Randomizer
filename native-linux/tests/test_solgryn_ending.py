"""A saved Solgryn victory must survive scenes without gameplay INI objects."""
import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from threading import Event
from unittest.mock import Mock,patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from native_player import Player

class SolgrynEnding(unittest.TestCase):
 def make(self,path):
  p=Player.__new__(Player);p.folder=Path(path);p.m=dict(run_id='run',slot=1,seed='SEED',options={'difficulty':1});p.last=None
  p.bridge=SimpleNamespace(snapshot=Mock(return_value={'scene':46}))
  p.watch=SimpleNamespace(error=None,ready=Event(),pressed=Event());p.watch.ready.set();p.watch.pressed.set()
  p.insights=SimpleNamespace(pause=Mock());p.shots=SimpleNamespace(pause=Mock());p.progress=SimpleNamespace(data={'index':6,'spot':'boss_solgryn.ini','transition_trace':['private']})
  summary=dict(run_id='run',completed=True,deaths=5,seconds=2631,game_seconds=2570,difficulty=1,live={'hook':{'errors':0}})
  (p.folder/'summary.json').write_text(json.dumps(summary));return p
 def test_ending_uses_confirmed_summary_without_ini_or_gameplay_reads(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.make(d);before=(p.folder/'summary.json').read_bytes()
   with patch('native_player.ini_object_ids',side_effect=AssertionError('Ending has no Ini++')),patch('native_player.read_state',side_effect=AssertionError('No gameplay reads after victory')):
    for scene in (45,46,47,1):
     p.bridge.snapshot.return_value={'scene':scene};result=p.poll();self.assertTrue(result['completed']);self.assertEqual(result['frame'],scene+1)
   self.assertEqual(result['stats'],dict(difficulty='1',deaths='5',timeseconds='2570'));self.assertNotIn('transition_trace',result['progress'])
   self.assertEqual(before,(p.folder/'summary.json').read_bytes());p.insights.pause.assert_called_once();p.shots.pause.assert_called_once();self.assertFalse(p.watch.ready.is_set());self.assertFalse(p.watch.pressed.is_set())
 def test_stale_last_status_does_not_clear_saved_victory(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.make(d);p.last={'completed':False,'frame':46,'stats':{'timeseconds':'9999'}}
   result=p.poll();self.assertTrue(result['completed']);self.assertEqual(result['stats']['timeseconds'],'2570');self.assertEqual(json.loads((p.folder/'status.json').read_text()),result)
 def test_without_summary_gameplay_still_runs_and_missing_ini_is_not_hidden(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.make(d);(p.folder/'summary.json').unlink()
   with patch('native_player.ini_object_ids',return_value={}) as read:
    with self.assertRaises(KeyError):p.poll()
   read.assert_called_once();p.insights.pause.assert_not_called()
 def test_foreign_or_unconfirmed_result_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.make(d)
   for change in ({'run_id':'another-run'},{'completed':False}):
    summary=dict(run_id='run',completed=True,**{})|change;(p.folder/'summary.json').write_text(json.dumps(summary))
    with self.assertRaises(ValueError):p.poll()
 def test_legacy_summary_without_tracker_seconds_and_no_shot_randomizer(self):
  with tempfile.TemporaryDirectory() as d:
   p=self.make(d);p.shots=None;s=json.loads((p.folder/'summary.json').read_text());s.pop('game_seconds');(p.folder/'summary.json').write_text(json.dumps(s))
   self.assertEqual(p.poll()['stats']['timeseconds'],'2631')

if __name__=='__main__':unittest.main()
