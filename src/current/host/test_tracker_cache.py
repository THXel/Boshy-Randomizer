"""Changed saves, stale snapshots and heartbeat continuity with the parsed cache."""
from pathlib import Path
import os, tempfile, unittest, configparser, json
from unittest.mock import Mock, patch
from types import SimpleNamespace
from menu_host.store import save, RC4, atomic
from tracker.snapshots import SnapshotCache
from tracker.publisher import Publisher
from test_tracker import plan

def write(path,value):atomic(path,RC4(b'BLOB',('[Stats]\nDeaths='+str(value)+'\n').encode()))
class CacheTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.p=self.root/'SaveFile1.ini';write(self.p,1);self.loader=Mock(wraps=save);self.cache=SnapshotCache(self.loader)
 def tearDown(self):self.temp.cleanup()
 def value(self):return self.cache(self.p).getint('Stats','Deaths')
 def test_unchanged_reuses_parsed_data(self):
  self.assertEqual(self.value(),1)
  for _ in range(20):self.assertEqual(self.value(),1)
  self.assertEqual(self.loader.call_count,1)
 def test_atomic_replacement_preserving_size_and_mtime_is_seen(self):
  self.value();old=self.p.stat();write(self.p,2);os.utime(self.p,ns=(old.st_atime_ns,old.st_mtime_ns));self.assertEqual(self.value(),2)
 def test_inplace_same_size_write_seen(self):
  self.value();self.p.write_bytes(RC4(b'BLOB',b'[Stats]\nDeaths=3\n'));self.assertEqual(self.value(),3)
 def test_missing_file_never_returns_cached_value(self):
  self.value();self.p.unlink()
  with self.assertRaises(OSError):self.value()
  write(self.p,4);self.assertEqual(self.value(),4)
 def test_corrupt_then_repaired_never_returns_stale_value(self):
  self.value();self.p.write_bytes(b'broken')
  with self.assertRaises(configparser.Error):self.value()
  write(self.p,5);self.assertEqual(self.value(),5)
 def test_empty_file_is_rejected(self):
  self.value();self.p.write_bytes(b'')
  with self.assertRaises(ValueError):self.value()
 def test_symlink_rejected_even_after_cache_hit(self):
  self.value();target=self.root/'other.ini';self.p.rename(target);self.p.symlink_to(target)
  with self.assertRaises(ValueError):self.value()
 def test_changes_during_read_are_retried_next_tick(self):
  def race(path):
   cfg=save(path);write(path,6);return cfg
  cache=SnapshotCache(race)
  with self.assertRaises(OSError):cache(self.p)
  self.assertEqual(cache.entries,{})
  cache.loader=save;self.assertEqual(cache(self.p).getint('Stats','Deaths'),6)
 def test_different_run_folders_do_not_share_entries(self):
  self.value();other=self.root/'other';other.mkdir();p=other/'SaveFile1.ini';write(p,7);self.assertEqual(self.cache(p).getint('Stats','Deaths'),7);self.assertEqual(self.value(),1)

class PublisherCacheTests(unittest.TestCase):
 def test_clock_heartbeat_and_changed_deaths_continue_with_cached_saves(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);run=root/'run';run.mkdir();work=root/'work';work.mkdir()
   (run/'plan.json').write_text(json.dumps(plan()))
   path=work/'SaveFile1.ini';write(path,1)
   store=SimpleNamespace(current=lambda _: {'run':'rebuilt-menu-'+'a'*32},folder=lambda _:run)
   c=SimpleNamespace(closed=False,window=SimpleNamespace(pid=os.getpid(),reader=SimpleNamespace(frame=lambda:'First World - Prehistorik')),folder=work,phase='playing',active_slot=1)
   pub=Publisher(store,root/'feed.json');clock=[10.0]
   with patch('tracker.publisher.time.monotonic',side_effect=lambda:clock[0]):
    pub.tick(c,True);initial=json.loads(pub.path.read_text())
    clock[0]+=3;pub.tick(c,True);second=json.loads(pub.path.read_text())
    self.assertEqual(second['elapsed'],3);self.assertGreaterEqual(second['updated_at'],initial['updated_at']);self.assertEqual(pub.snapshots.hits,1)
    write(path,7);clock[0]+=1;pub.tick(c,True);self.assertEqual(json.loads(pub.path.read_text())['deaths'],7)
    before=pub.path.read_bytes();path.write_bytes(b'broken');clock[0]+=1;pub.tick(c,True)
    self.assertTrue(pub.last_error);self.assertEqual(pub.path.read_bytes(),before)
    write(path,8);clock[0]+=1;pub.tick(c,True);self.assertFalse(pub.last_error);self.assertEqual(json.loads(pub.path.read_text())['deaths'],8)
    pub.close(c);self.assertEqual(pub.snapshots.entries,{})
