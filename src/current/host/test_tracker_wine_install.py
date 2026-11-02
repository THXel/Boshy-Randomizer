"""Packaged Wine installation to the personal Linux tracker boundary."""
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
from test_tracker import adapter

class PackagedWineTrackerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.users = Path(self.temp.name)
        self.feed = self.users / 'player/AppData/Local/boshy-randomizer/live.json'
        self.feed.parent.mkdir(parents=True)
        self.data = dict(schema=2, producer='boshy-fusion', application='boshy-randomizer',
                         updated_at=time.time(), game_running=True, mode='menu',
                         play_mode='menu', slot=0, seed='', elapsed=0)
        self.feed.write_text(json.dumps(self.data))
        patcher = patch.object(adapter, 'WINE_USERS', self.users)
        patcher.start(); self.addCleanup(patcher.stop)

    def response(self, data):
        connection = MagicMock()
        response = connection.getresponse.return_value
        response.status = 200; response.read.return_value = json.dumps(data).encode()
        return connection

    def test_native_feed_discovered_and_validated_heartbeat_accepted(self):
        connection = self.response(dict(self.data, connected=True))
        with patch.object(adapter.http.client, 'HTTPConnection', return_value=connection):
            self.assertEqual(adapter.read_feed(self.feed), self.data)
        self.assertIn(self.feed, adapter._wine_feeds())
        connection.request.assert_called_once_with('GET', '/state')
        connection.close.assert_called_once()

    def test_disconnected_server_rejects_fresh_file(self):
        with patch.object(adapter.http.client, 'HTTPConnection', return_value=self.response({'connected':False})):
            self.assertIsNone(adapter.read_feed(self.feed))

    def test_changed_heartbeat_or_run_rejected(self):
        for change in ({'updated_at':self.data['updated_at']+1}, {'seed':'other'}, {'run_id':'b'*32}):
            connection = self.response(dict(self.data, connected=True, **change))
            with patch.object(adapter.http.client, 'HTTPConnection', return_value=connection):
                self.assertIsNone(adapter.read_feed(self.feed))

    def test_unavailable_server_rejected(self):
        connection = MagicMock(); connection.request.side_effect = OSError('offline')
        with patch.object(adapter.http.client, 'HTTPConnection', return_value=connection):
            self.assertIsNone(adapter.read_feed(self.feed))
        connection.close.assert_called_once()

    def test_stale_file_does_not_query_server(self):
        with patch.object(adapter.http.client, 'HTTPConnection') as request:
            self.assertIsNone(adapter.read_feed(self.feed, now=self.data['updated_at']+10))
        request.assert_not_called()

    def test_explicit_gaming_prefix_is_discovered_but_unrelated_is_not(self):
        prefix = self.users / 'gaming64'; prefix.mkdir()
        feed = prefix / 'drive_c/users/player/AppData/Local/boshy-randomizer/live.json'
        feed.parent.mkdir(parents=True); feed.write_text(json.dumps(self.data))
        config = self.users / 'config.json'
        config.write_text(json.dumps({'wine_prefix':str(prefix)}))
        with patch.object(adapter, 'PREFIX_CONFIG', config):
            self.assertIn(feed, adapter._wine_feeds())
            with patch.object(adapter.http.client, 'HTTPConnection', return_value=self.response(dict(self.data, connected=True))):
                self.assertEqual(adapter.read_feed(feed), self.data)
        self.assertNotIn(self.users/'unrelated/live.json', adapter._wine_feeds())

    def test_original_game_keeps_priority(self):
        original = {'game_running':True, 'display_mode':'speedrun'}
        self.assertIs(adapter.select(original, self.data), original)

    def test_unrelated_prefix_not_accepted(self):
        with patch.object(adapter.http.client, 'HTTPConnection') as request:
            self.assertFalse(adapter._wine_alive(self.data, self.users/'other/live.json'))
        request.assert_not_called()

if __name__ == '__main__': unittest.main()
