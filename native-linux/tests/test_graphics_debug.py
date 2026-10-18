import sys,tempfile,time,json,zipfile
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import graphics_debug as g
from debug_data import Recorder
from debug_runtime import DebugRuntime
class GraphicsDebug(unittest.TestCase):
 def player(self,base):return NS(store=NS(base=Path(base)),m={'run_id':'a'*32,'session_binding':'bound'},bridge=NS(ready={'pid':123},snapshot=Mock(return_value={'scene':7,'next':0})),progress=NS(data={}),last={'frame':8})
 def test_run_process_and_mask_binding(self):
  with tempfile.TemporaryDirectory() as base:
   p=self.player(base);g.request(p,9);self.assertEqual(g.requested(base,'a'*32,123),9)
   self.assertEqual(g.requested(base,'b'*32,123),0);self.assertEqual(g.requested(base,'a'*32,124),0)
   g.reset(base);self.assertEqual(g.requested(base,'a'*32,123),0)
 def test_invalid_or_transition_command_cannot_write(self):
  with tempfile.TemporaryDirectory() as base:
   p=self.player(base)
   for mask in (True,-1,16,'1'):
    with self.assertRaises(ValueError):g.request(p,mask)
   p.progress.data['pending']={'target':'x'}
   with self.assertRaises(ValueError):g.request(p,1)
   self.assertFalse((Path(base)/'menu-runtime').exists())
 def test_cosmetic_command_does_not_modify_run(self):
  with tempfile.TemporaryDirectory() as base:
   p=self.player(base);d=DebugRuntime(p.store,start_window=False)
   req=dict(session=d.token,created_at=time.time(),run_id=p.m['run_id'],binding='bound',enabled=False,action='graphics_mask',value=5)
   (d.folder/'request-test.json').write_text(json.dumps(req));d.commands(p)
   self.assertTrue(json.loads((d.folder/'response-test.json').read_text())['ok']);self.assertEqual(g.requested(base,p.m['run_id'],123),5)
   self.assertFalse((Path(base)/'debug-actions').exists());self.assertEqual(p.progress.data,{})
   req['run_id']='b'*32;(d.folder/'request-wrong.json').write_text(json.dumps(req));d.commands(p)
   self.assertFalse(json.loads((d.folder/'response-wrong.json').read_text())['ok']);self.assertEqual(g.requested(base,p.m['run_id'],123),5)
 def test_reloading_same_run_rebinds_native_reader(self):
  with tempfile.TemporaryDirectory() as base,patch('graphics_debug.Telemetry') as reader:
   p=self.player(base);d=DebugRuntime(p.store,start_window=False)
   d.graphics_state(p);d.graphics_state(p);self.assertEqual(reader.call_count,1)
   p.bridge=NS(ready={'pid':123});d.graphics_state(p);self.assertEqual(reader.call_count,2)
   other=self.player(base);d.graphics_state(other);self.assertEqual(reader.call_count,3)
 def test_report_contains_window_capture_and_graphics(self):
  with tempfile.TemporaryDirectory() as base,patch('graphics_debug.capture_game',return_value=(b'png-fixture',{'scope':'game-window-only'})):
   state={'sequence':1,'time':time.time(),'graphics':{'background_set':'World 3','history':[{'room':'World 1'}]}}
   path=Recorder(base).finish('test',state)
   with zipfile.ZipFile(path) as z:
    self.assertEqual(z.read('game.png'),b'png-fixture');self.assertEqual(json.loads(z.read('graphics.json')),state['graphics'])
    self.assertEqual(json.loads(z.read('bericht.json'))['screenshot']['scope'],'game-window-only')
 def test_missing_screenshot_does_not_drop_report(self):
  with tempfile.TemporaryDirectory() as base,patch('graphics_debug.capture_game',return_value=(None,{'unavailable':'no game'})):
   path=Recorder(base).finish('test',{'sequence':1})
   with zipfile.ZipFile(path) as z:
    self.assertNotIn('game.png',z.namelist());self.assertEqual(json.loads(z.read('bericht.json'))['screenshot']['unavailable'],'no game')
if __name__=='__main__':unittest.main()
