"""Menu audio ownership and no-restart guarantees for ordinary UI refreshes."""
import unittest
from pathlib import Path
from unittest.mock import patch,Mock
from menu_host.audio import MenuAudio

class MenuAudioTests(unittest.TestCase):
    def test_refresh_resume_and_delete_lifecycle_keep_same_stream(self):
        proc=Mock();proc.poll.return_value=None
        with patch('menu_host.audio.prepare',return_value=Path('/private/title.wav')), patch('menu_host.audio.subprocess.Popen',return_value=proc) as spawn:
            a=MenuAudio('/private');a.sync()
            for _ in range(8):a.sync();a.resume()
            self.assertEqual(spawn.call_count,1)
            self.assertIs(a.process,proc)
            proc.terminate.assert_not_called()
            a.suspend();proc.terminate.assert_called_once()
            a.resume();self.assertEqual(spawn.call_count,2)
            a.close();a.sync();self.assertEqual(spawn.call_count,2)

    def test_mute_and_preparation_failure_do_not_spawn_audio(self):
        with patch('menu_host.audio.prepare',return_value=Path('/private/title.wav')),patch('menu_host.audio.subprocess.Popen') as spawn:
            a=MenuAudio('/private',False);a.sync();a.resume();spawn.assert_not_called()
        with patch('menu_host.audio.prepare',side_effect=RuntimeError('missing')),patch('menu_host.audio.subprocess.Popen') as spawn:
            a=MenuAudio('/private');a.sync();self.assertEqual(a.error,'missing');spawn.assert_not_called()

if __name__=='__main__':unittest.main()
