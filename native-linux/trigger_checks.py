"""Exhaustive offline checks against the user-confirmed exit contract.

This deliberately does not certify natural gameplay or native patch effects.
"""
from pathlib import Path
from itertools import product
from unittest.mock import patch
import tempfile
from trigger_audit import points
from native_triggers import CompletionGate,exits_for
from minibosses import Gate as Mini
from beta_bosses import Gate as Beta
from old_sonic import Gate as Sonic
from native_level_route import GastlyRoute

EXPECTED={
'save1.ini':(4,33),'save2.ini':(),'save3.ini':(10,37),'save4.ini':(12,),
'save6.ini':(14,),'save7.ini':(17,39,50),'save9.ini':(23,24,53),'save10.ini':(24,53),
'save11.ini':(26,),'save12.ini':(),'save13.ini':(),'save14.ini':(29,),'save15.ini':(51,38),
'save17.ini':(),'save18.ini':(46,),'save19.ini':(15,52),'save20.ini':(35,),
'save21.ini':(54,),'save22.ini':(32,),'save23.ini':(6,),
'boss1.ini':(5,),'boss2.ini':(),'boss3.ini':(7,),'boss4.ini':(8,),'boss6.ini':(11,),
'boss7.ini':(12,),'boss8.ini':(13,),'boss9.ini':(15,),'boss10.ini':(17,),
'boss11.ini':(22,),'boss12.ini':(25,),'boss13.ini':(27,),'boss15.ini':(31,),
'boss16.ini':(),'boss17.ini':(35,),'boss19.ini':(),'boss20.ini':(),'boss21.ini':(29,),
'boss22.ini':(31,),'boss23.ini':(61,),'boss_solgryn.ini':(),'gastly_grass':(10,37),
'boss_kappa':(29,),'boss_kid_icarus':(),'kid_icarus_after':(59,)}

def run(base):
 pool=points(base);assert 'tutorial' not in pool;assert set(pool)==set(EXPECTED)
 checks=0
 def check(test):
  nonlocal checks
  assert test;checks+=1
 for bits in product((False,True),repeat=4):
  hacks=dict(zip(('god_mode','one_hp','skip_intro','fast_chests'),bits))
  for mode in ('randomizer','target'):
   for spot,p in pool.items():
    check(exits_for(spot,p)==EXPECTED[spot])
    def observe(g,frame,death=0,tick=100,restart=False,position=None,won=False):
     flags={'sonic':2} if won else {}
     with patch('native_triggers.time.monotonic',return_value=0):return g.observe(spot,p,frame,flags,flags,{'deaths':death},tick,restart,position)
    g=CompletionGate();check(observe(g,p['frame']) is None);check(observe(g,p['frame'],tick=1,restart=True) is None)
    for dest in EXPECTED[spot]:
     g=CompletionGate();check(observe(g,dest) is None);check(observe(g,dest,tick=200) is None)
     g=CompletionGate();observe(g,p['frame']);reason=observe(g,dest,position=(7871,553) if spot=='save20.ini' else None,won=spot=='boss23.ini')
     check(reason==('Boss-Ausgang' if p['category']=='bosses' else 'Level-Ausgang'))
     if spot!='boss23.ini':
      for kw in ({'death':1},{'restart':True}):
       g=CompletionGate();observe(g,p['frame']);check(observe(g,dest,**kw) is None)
    # Every non-exit scene must remain inert, including another spot's entry.
    for wrong in range(1,62):
     if wrong in EXPECTED[spot]:continue
     g=CompletionGate();observe(g,p['frame']);check(observe(g,wrong,won=spot=='boss23.ini') is None)
   # Native-coordinate miniboss contracts; no screen pixels or flags alone.
   for spot,enter,before in [('save2.ini',(3210,300),(3190,300)),('save13.ini',(4490,250),(4470,250)),('save4.ini',(2700,1600),(2500,1600)),('save12.ini',(717,6600),(717,6671)),('save17.ini',(2175,1864),(1900,1864)),('boss16.ini',(5169,205),(4500,250))]:
    p=pool[spot];g=Mini()
    def sm(pos,tick):return dict(frame=p['frame'],tick=tick,player_alive=True,position=pos,generation=[1,2],boss_object=None,hp=None)
    check(g.observe(spot,0,p,sm(enter,10),0,0) is None);g.observe(spot,0,p,sm(before,20),0,1);check(g.observe(spot,0,p,sm(enter,30),0,2) is not None);check(g.observe(spot,0,p,sm(enter,1),1,3) is None)
   for spot,pos in [('boss2.ini',(3400,300)),('boss_kid_icarus',(717,6600))]:
    p=pool[spot];g=Mini();a=dict(frame=p['frame'],tick=20,player_alive=True,position=pos,generation=[1,2],boss_object=99,hp=1,exit_blocked=True,intro_active=False)
    z={**a,'tick':30,'hp':0,'boss_object':None if spot=='boss_kid_icarus' else 99,'exit_blocked':False}
    check(g.observe(spot,0,p,z,0,0) is None);g.observe(spot,0,p,a,0,1);check(g.observe(spot,0,p,z,0,2) is None)
    deadline=6.0 if spot=='boss2.ini' else 3.0
    check(g.observe(spot,0,p,{**z,'tick':39},0,deadline-.001) is None)
    check(g.observe(spot,0,p,{**z,'tick':40},0,deadline) is not None);check(g.observe(spot,0,p,{**z,'tick':1},1,deadline+1) is None)
   for spot,key,frame in [('boss19.ini','questionmark',44),('boss20.ini','ridley',45)]:
    g=Beta(allow_fast=hacks['one_hp']);a=dict(key=key,frame=frame,tick=10,player_alive=True,hp=1,intro_active=True,intro_phase=10,object=99,flags=0)
    check(not g.observe(spot,0,a,0,0));check(not g.observe(spot,0,{**a,'tick':20,'hp':0},0,4))
    a.update(tick=30,intro_active=False,intro_phase=780,hp=1,flags=1);check(not g.observe(spot,0,a,0,5));a.update(tick=40,hp=0);check(not g.observe(spot,0,a,0,6));check(g.observe(spot,0,{**a,'tick':50},0,7.6));check(not g.observe(spot,0,{**a,'tick':1},1,8))
   # Old Sonic's separate six-second animation guard is covered by its tests.
 with tempfile.TemporaryDirectory() as d:
  g=GastlyRoute(Path(d)/'g.db',run_id='test',seed='test',game_hash='hash',pool=pool)
  try:
   for sauce in ('0','1'):
    c={'awesomesauce':sauce,'gastly':'0'};check(g.observe(frame=9,collectables=c,disk_collectables=c) is None)
   c={'awesomesauce':'1','gastly':'1'};check(g.observe(frame=9,collectables=c,disk_collectables=c) is None)
   check(g.observe(frame=9,collectables=c,disk_collectables=c,restart_pressed=True,next_target=lambda:'save1.ini')=='save1.ini')
  finally:g.close()
 return dict(spots=len(pool),hack_combinations=16,modes=2,assertions=checks)

if __name__=='__main__':
 import json
 print(json.dumps(run(Path(__file__).resolve().parent),indent=2))
