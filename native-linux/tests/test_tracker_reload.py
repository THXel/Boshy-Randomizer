import json,sys,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from native_tracker import Publisher
from native_telemetry import MusicReader

class TrackerReload(unittest.TestCase):
 def test_same_run_rebinds_after_reload_or_connection_replacement(self):
  for via_menu,replace_player in ((True,True),(False,True),(False,False)):
   with self.subTest(menu=via_menu,new_player=replace_player),tempfile.TemporaryDirectory() as tmp:
    base=Path(tmp);(base/'INI').mkdir();folder=base/'run';folder.mkdir();store=NS(base=base,root=base)
    p=Publisher(store);p.identity='run';p.clock=77;p.clock_path=folder/'clock.json';p.catalogue_cache={'locations':[]};p.share_cache='SHARED-SEED'
    music=NS(TRACKS=('cue',),mapping=lambda seed:{'cue':'song'})
    import beta_catalogue
    rules=NS(module=lambda name:music if name=='music_randomizer' else beta_catalogue)
    m=dict(run_id='run',slot=1,seed='SEED',options=dict(mode='randomizer',difficulty=1,extras=dict(music=True)))
    def player():return NS(store=store,m=m,progress=NS(data=dict(index=0,limit=7,spot='save1.ini'),goals=dict(items=[],bosses=[])),metadata=dict(pid=1),rules=rules,bridge=Mock(read=Mock(return_value=(0x42524d31,1,1,1,0,0))))
    first=player();result=dict(frame=2,stats=dict(difficulty=1,deaths=0));data=dict(collectables={},unlockables={},license={},achievements={},randochecks={})
    def read(reader,*args):return reader.player.bridge.read()
    with patch('native_tracker.ini',return_value=data),patch('run_extras.presentation',return_value=[]),patch('native_telemetry.NativeReader.read',read):
     p.run(first,result);old=p.music_reader;old_bridge=first.bridge
     if via_menu:p.menu(loading=True)
     first.bridge=None
     second=player() if replace_player else first
     if not replace_player:second.bridge=Mock(read=Mock(return_value=(0x42524d31,1,1,2,0,0)))
     p.last=0;p.run(second,result)
     self.assertIsNot(p.music_reader,old);self.assertIs(p.music_reader.player,second)
     self.assertEqual(old_bridge.read.call_count,1)
     output=json.loads(p.path.read_text());self.assertEqual(output['music']['track'],'song');self.assertEqual(output['share_seed'],'SHARED-SEED');self.assertGreaterEqual(output['elapsed'],77)
 def test_closed_player_and_temporary_audio_read_timeout_are_optional(self):
  reader=MusicReader.__new__(MusicReader);reader.player=NS(bridge=None,m=dict(options=dict(extras=dict(music=True))));reader.reader=Mock()
  self.assertIsNone(reader.read());reader.reader.read.assert_not_called()
  reader.player.bridge=object();reader.reader.read.side_effect=TimeoutError('bridge busy')
  self.assertIsNone(reader.read())

if __name__=='__main__':unittest.main()
