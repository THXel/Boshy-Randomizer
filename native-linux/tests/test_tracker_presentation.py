import sys,json,tempfile,threading,time,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tracker_presenter import progress,elapsed
from tracker_grid import layout
from native_tracker import Publisher
from native_menu_host import update_result
from tracker_source import Source

class TrackerTests(unittest.TestCase):
 def test_route_is_not_collection_progress_and_finishes_final_stage(self):
  d=dict(mode='randomizer',route_index=6,route_limit=7,checks_done=3,checks_total=36)
  self.assertAlmostEqual(progress(d)[1],600/7)
  self.assertEqual(progress(dict(d,phase='finished'))[1],100)
 def test_target_and_normal_have_their_own_progress(self):
  d=dict(mode='randomizer',play_mode='target',checks_done=5,checks_total=20,goals=[dict(done=True),dict(done=False)])
  self.assertEqual(progress(d)[1],50)
  self.assertEqual(progress(dict(d,play_mode='normal'))[1],25)
  self.assertEqual(progress(dict(d,goals=[]))[1],0)
 def test_stale_timer_freezes_without_rewinding(self):
  d=dict(elapsed=100,timer_running=True,updated_at=10)
  self.assertEqual([elapsed(d,t) for t in (9,10,17,18,19,40)],[100,100,107,108,108,108])
  self.assertEqual(elapsed(dict(d,timer_running=False),40),100)
 def test_all_icons_fit_saved_window_without_losing_groups(self):
  rows=[dict(group=g,name=str(i),done=i==0) for g,n in [('Items',20),('Characters',17),('Bosses',23)] for i in range(n)]
  size,cells,headers,height=layout(rows,280,355)
  self.assertEqual(len(cells),60);self.assertEqual(len(headers),3);self.assertLessEqual(height,355)
  self.assertTrue(all(0<=x and x+size<=280 for x,y,r in cells))
 def test_publisher_includes_solgryn_and_collectibles_not_starter_characters(self):
  for mode in ('randomizer','target','normal'):
   for completed in (False,True):
    with self.subTest(mode=mode,completed=completed),tempfile.TemporaryDirectory() as tmp:
     base=Path(tmp);(base/'INI').mkdir();store=NS(base=base,root=base);folder=base/'run';folder.mkdir()
     p=Publisher(store);p.identity='run';p.clock_path=folder/'clock.json';p.catalogue_cache={'locations':[dict(source='Wily CD',source_kind='item',key='item'),dict(source='Luigi',source_kind='character',key='luigi')]};p.share_cache='SHARE';p.music_reader=NS(read=lambda:None)
     player=NS(m=dict(run_id='run',slot=1,seed='SEED',options=dict(mode=mode,difficulty=1)),progress=NS(data=dict(index=6,limit=7,spot='boss_solgryn.ini'),goals=dict(items=[],bosses=[])),metadata={},rules=None,bridge=object())
     p.music_player=player;p.music_bridge=player.bridge
     data=dict(collectables={'wily cd':'1'},unlockables={'luigi':'1','dark boshy':'1'},license={'charactername':'Dark Boshy'},achievements={},randochecks={'item':'1'})
     with patch('native_tracker.ini',return_value=data),patch('run_extras.presentation',return_value=[]):p.run(player,dict(frame=46,completed=completed,stats=dict(difficulty=1,deaths=2)))
     d=json.loads(p.path.read_text());boss=[r for r in d['bosses'] if r['name']=='Solgryn'];self.assertEqual(len(boss),1);self.assertEqual(boss[0]['done'],completed)
     self.assertEqual([r['name'] for r in d['characters']],['Luigi']);self.assertTrue(d['characters'][0]['done']);self.assertEqual(d['checks_done'],1)
 def test_source_keeps_last_valid_read_but_closes_with_host(self):
  with tempfile.TemporaryDirectory() as tmp,patch('tracker_source.BASE',Path(tmp)),patch('tracker_source.host_alive',return_value=True),patch.dict('os.environ',BOSHY_TRACKER_HOST='123'):
   path=Path(tmp)/'INI/native-live.json';path.parent.mkdir();path.write_text(json.dumps(dict(host_pid=123,schema=1,mode='randomizer',elapsed=123)))
   source=Source()
   try:
    deadline=time.monotonic()+2
    while not source.read() and time.monotonic()<deadline:time.sleep(.01)
    self.assertEqual(source.read()['elapsed'],123)
    path.write_text('{');time.sleep(.35);self.assertEqual(source.read()['elapsed'],123)
    with patch('tracker_source.host_alive',return_value=False):
     source.thread.join(1);self.assertTrue(source.finished)
   finally:source.stop.set();source.thread.join(1)

class CreditsTests(unittest.TestCase):
 def objects(self):
  player=Mock();player.bridge.snapshot.return_value={'scene':46};tracker=Mock();model=Mock(dirty=False,slot=1,action=None);view=Mock();view.events.return_value=[]
  return player,tracker,model,view,Mock(),Mock()
 def test_credits_temporary_missing_snapshot_retries_and_recovers(self):
  args=self.objects();args[0].poll.side_effect=[RuntimeError({'error':'state unavailable'}),dict(completed=True,frame=47)]
  self.assertFalse(update_result(*args));args[1].run.assert_not_called()
  self.assertTrue(update_result(*args));args[1].run.assert_called_once();args[0].close.assert_not_called()
 def test_credits_menu_reads_can_temporarily_disappear_too(self):
  args=self.objects();args[3].events.side_effect=RuntimeError({'error':'read failed'})
  for _ in range(300):self.assertFalse(update_result(*args))
  args[0].close.assert_not_called();args[0].poll.assert_not_called()
 def test_f2_closes_overlay_without_republishing_saved_victory(self):
  for scene in (0,1):
   args=self.objects();args[0].bridge.snapshot.return_value={'scene':scene}
   self.assertTrue(update_result(*args))
   args[3].write.assert_called_once_with(60,0)
   self.assertEqual(args[2].page,'slots');self.assertEqual(args[2].action,('result_back',1,None))
   args[0].poll.assert_not_called();args[1].run.assert_not_called();args[4].draw.assert_not_called()
 def test_transient_reset_snapshot_does_not_delete_results(self):
  args=self.objects();args[0].bridge.snapshot.side_effect=RuntimeError({'error':'state unavailable'})
  self.assertFalse(update_result(*args));args[3].write.assert_not_called();args[0].close.assert_not_called()
 def test_unknown_errors_are_not_swallowed(self):
  args=self.objects();args[0].poll.side_effect=RuntimeError('native patch invalid')
  with self.assertRaises(RuntimeError):update_result(*args)

if __name__=='__main__':unittest.main()
