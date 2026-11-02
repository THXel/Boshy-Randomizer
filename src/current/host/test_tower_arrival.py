"""Arrival-only correction must preserve original movement and jumping."""
import unittest
import recover_boshy_routes as source
from gameplay.tower_arrival import transform, LIFT, COUNTER
from native_menu.events import alt
from transition.events import commands


class TowerArrivalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=next(p for p,f in source.payloads.items() if f==51)
        cls.before=source.original_sections(p)
        cls.after,cls.audit=transform(51,cls.before,source.objects,source.frames[50]['instances'])

    def test_original_events_unchanged_and_only_three_new_rows(self):
        self.assertEqual(self.after[:-1],self.before)
        self.assertEqual(len(self.after[-1]),3)
        self.assertEqual(self.audit[0]['maximum_ticks'],3)
        self.assertEqual(transform(54,self.before,{},[]),(self.before,[]))

    def test_no_persistent_writes_or_per_tick_profile_reads(self):
        for index,row in enumerate(self.after[-1]):
            cs=commands(row)
            self.assertFalse(any(not c[0] and c[1]==33 for c in cs))
            if index:
                self.assertFalse(any(b'FusionRouteV4' in c[-1] for c in cs))
                self.assertTrue(any(alt(LIFT,COUNTER) in c[-1] for c in cs if c[0]))
        start=commands(self.after[-1][0])
        self.assertEqual(start[0][1:3],(-3,-1))
        self.assertTrue(any(b'Schema' in c[-1] for c in start))

    def test_jump_disarms_before_correction(self):
        disarm=commands(self.after[-1][1])
        self.assertTrue(any(alt(307,2) in c[-1] for c in disarm if c[0]))
        self.assertEqual(disarm[-1][1:4],(2,31,LIFT))
        landing=commands(self.after[-1][2])
        self.assertTrue(any(c[1:4]==(2,-4,97) for c in landing if c[0]))
        self.assertEqual([c[1:4] for c in landing if not c[0]],
                         [(2,3,307),(2,31,307),(2,31,LIFT)])
