"""Regressions from the live Kid Icarus save-write storm and rapid-fire saves."""
import struct
import unittest
from gameplay.save_transactions import transform
from gameplay.native_events import Events
from gameplay.profile_batch import begin, finish
from transition.events import action, commands, set_ini, expression, string, integer
from unittest.mock import patch
import recover_boshy_routes as routes


class SavePerformanceTests(unittest.TestCase):
    def test_entry_receipts_are_written_only_once_per_frame_visit(self):
        count = 0
        for payload in routes.payloads:
            for rows in routes.sections(payload):
                for row in rows:
                    cs = commands(row)
                    acts = [c for c in cs if not c[0]]
                    if len(acts) != 1 or acts[0][1:3] != (33,94):
                        continue
                    key = next((k for k in ('Armed','KidSeen') if (k+'\0').encode() in acts[0][-1]),None)
                    if not key:
                        continue
                    conditions = [c[-1] for c in cs if c[0]]
                    self.assertTrue(any((key+'\0').encode() in c and integer(0) in c for c in conditions))
                    self.assertTrue(any(b'Schema\0' in c for c in conditions))
                    count += 1
        self.assertGreaterEqual(count,22)

    def test_checkpoint_batches_writes_and_fastloop_before_jump(self):
        e = Events([[]]);oi=109
        writes = [set_ini('Positions',k,i,oi=oi) for i,k in enumerate(('xPos','yPos','frame'))]
        loop=action(-1,14,0,[expression(string('save'),45),expression(integer(1))])
        jump=action(-3,2,0,[expression(integer(3))])
        row=e.row([],writes+[loop,jump])
        with patch('gameplay.save_transactions.frame_metadata',return_value=(oi,93,loop)):
            result,audit=transform(3,[[row]],{},[])
        actions=[c[-1] for c in commands(result[0][0]) if not c[0]]
        self.assertEqual(actions,[begin(oi),*writes,loop,*finish(oi),jump])
        self.assertEqual(audit[0]['save_transactions'],1)

    def test_nested_handlers_keep_callers_transaction(self):
        e=Events([[]]);loop_condition=struct.pack('<HhhHHHBBH',16,-1,-16,0,0,0,0,0,e.ident())
        row=e.row([loop_condition],[set_ini('A','B',1,oi=109),set_ini('A','C',2,oi=109)])
        with patch('gameplay.save_transactions.frame_metadata',return_value=(109,93,b'')):
            result,_=transform(3,[[row]],{},[])
        self.assertEqual(result,[[row]])

    def test_clock_stays_in_memory_until_native_frame_exit(self):
        e=Events([[]]);oi=109
        timer=struct.pack('<HhhHHHBBH',16,-4,-4,0,0,0,0,0,e.ident())
        row=e.row([timer],[set_ini('Stats','TimeSeconds',123,oi=oi)])
        with patch('gameplay.save_transactions.frame_metadata',return_value=(oi,93,b'')):
            result,audit=transform(3,[[row]],{},[])
        clock=[c for c in commands(result[0][0]) if not c[0]]
        self.assertEqual([c[2] for c in clock],[132,94,132])
        end=commands(result[-1][0])
        self.assertEqual(end[0][1:3],(-3,-2))
        # Trigger conditions must not carry EVFLAGS_ALWAYS: the native runtime
        # otherwise evaluates End of Frame as a per-tick condition.
        self.assertEqual(end[0][-1][10],0)
        self.assertEqual(end[-1][1:4],(33,124,oi))
        self.assertEqual(audit[0]['buffered_clocks'],1)

    def test_restart_commits_before_control_leaves_frame(self):
        e=Events([[]]);oi=109
        for code in (0,1,2,4,5,6):
            changes=[set_ini('A','B',1,oi=oi),set_ini('A','C',2,oi=oi)]
            transfer=action(-3,code,0,[])
            with patch('gameplay.save_transactions.frame_metadata',return_value=(oi,93,b'')):
                result,_=transform(3,[[e.row([],changes+[transfer])]],{},[])
            acts=[c[-1] for c in commands(result[0][0]) if not c[0]]
            self.assertEqual(acts[-3:],[*finish(oi),transfer])
