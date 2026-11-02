"""Close retries must remain bounded, regular and confined to the owned game."""
import unittest
from pathlib import Path
from unittest.mock import patch
from native_menu.shutdown import close_owned

class ShutdownTests(unittest.TestCase):
 def run_close(self, state, callback, timeout=2):
  clock=[0.0]
  def sleep(dt):clock[0]+=dt
  with patch('native_menu.shutdown.time.monotonic',side_effect=lambda:clock[0]),patch('native_menu.shutdown.time.sleep',side_effect=sleep):
   close_owned(Path('/own'),lambda:state,lambda:[['one','0','1'],['two','0','2']],callback,timeout=timeout)
  return clock[0]
 def test_ignored_initial_request_gets_regular_retry(self):
  state={1:Path('/own'),2:Path('/other')};calls=[]
  def request(row,retry):
   calls.append((row[0],retry))
   if retry:del state[1]
  elapsed=self.run_close(state,request)
  self.assertEqual(calls,[('one',False),('one',True)]);self.assertLess(elapsed,2);self.assertIn(2,state)
 def test_success_does_not_send_extra_requests(self):
  state={1:Path('/own')};calls=[]
  def request(row,retry):calls.append(retry);state.clear()
  self.run_close(state,request);self.assertEqual(calls,[False])
 def test_pid_reassignment_is_not_closed_again(self):
  state={1:Path('/own')};calls=[]
  def request(row,retry):calls.append(retry);state[1]=Path('/other')
  self.run_close(state,request);self.assertEqual(calls,[False])
 def test_unresponsive_process_returns_bounded_error_without_forcing_exit(self):
  state={1:Path('/own')};calls=[]
  with self.assertRaisesRegex(RuntimeError,'still running'):
   self.run_close(state,lambda row,retry:calls.append(retry))
  self.assertEqual(len(calls),3);self.assertEqual(state,{1:Path('/own')})
 def test_already_closed_needs_no_request(self):
  self.run_close({},lambda *args:self.fail('Unexpected close'))
 def test_close_race_is_benign_but_live_errors_are_not_hidden(self):
  state={1:Path('/own')}
  def gone(*args):state.clear();raise OSError('already gone')
  self.run_close(state,gone)
  with self.assertRaises(OSError):self.run_close({1:Path('/own')},lambda *args:(_ for _ in ()).throw(OSError('denied')))
