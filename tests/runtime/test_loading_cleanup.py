"""A failed UI construction must never leak the loading audio gate."""

import unittest
import sys
import types
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import loading_screen


class LoadingCleanup(unittest.TestCase):
    def test_audio_closed_when_window_creation_fails(self):
        calls = []

        class Gate:
            def __init__(self, pid):
                calls.append(('open', pid))

            def close(self):
                calls.append(('close',))

        fake_tk = types.ModuleType('tkinter')

        def fail():
            raise RuntimeError('simulated display error')

        fake_tk.Tk = fail
        fake_pil = types.ModuleType('PIL')
        fake_pil.Image = object()
        fake_pil.ImageTk = object()
        fake_pil.ImageOps = object()
        fake_audio = types.ModuleType('loading_audio')
        fake_audio.AudioGate = Gate
        with patch.dict(
            sys.modules,
            {'tkinter': fake_tk, 'PIL': fake_pil, 'loading_audio': fake_audio},
        ):
            with self.assertRaisesRegex(RuntimeError, 'simulated display error'):
                loading_screen.window({'pid': 123})
        self.assertEqual(calls, [('open', 123), ('close',)])

    def test_preserved_audio_never_opens_gate_even_when_window_fails(self):
        from unittest.mock import Mock

        fake_tk = types.ModuleType('tkinter')
        fake_tk.Tk = Mock(side_effect=RuntimeError('display unavailable'))
        fake_pil = types.ModuleType('PIL')
        fake_pil.Image = object()
        fake_pil.ImageTk = object()
        fake_pil.ImageOps = object()
        fake_audio = types.ModuleType('loading_audio')
        fake_audio.AudioGate = Mock()
        with patch.dict(
            sys.modules,
            {'tkinter': fake_tk, 'PIL': fake_pil, 'loading_audio': fake_audio},
        ):
            with self.assertRaisesRegex(RuntimeError, 'display unavailable'):
                loading_screen.window({'pid': 123, 'preserve_audio': True})
        fake_audio.AudioGate.assert_not_called()

    def test_preserved_cover_keeps_audio_destination_and_passes_policy_to_child(self):
        import json
        import os
        import tempfile
        from unittest.mock import Mock

        for initial in (None, 'existing-user-sink'):
            with self.subTest(initial=initial), tempfile.TemporaryDirectory() as folder:
                env = {} if initial is None else {'PULSE_SINK': initial}
                process = Mock()
                process.poll.return_value = None
                with (
                    patch.dict(os.environ, env, clear=True),
                    patch('lab.game_window', side_effect=RuntimeError('no window')),
                    patch.object(
                        loading_screen,
                        'python_command',
                        side_effect=lambda *args: list(args),
                    ),
                    patch.object(
                        loading_screen.subprocess, 'Popen', return_value=process
                    ) as spawn,
                    patch.object(loading_screen, 'LineReader') as reader,
                ):
                    reader.return_value.readline.return_value = 'READY audio-preserved'
                    cover = loading_screen.LoadingScreen(folder, 3, preserve_audio=True)
                    settings = json.loads(spawn.call_args.args[0][-1])
                    self.assertTrue(settings['preserve_audio'])
                    self.assertEqual(os.environ.get('PULSE_SINK'), initial)
                    # Closing a visual cover must not roll back changes made by another owner.
                    os.environ['PULSE_SINK'] = 'new-user-sink'
                    cover.close()
                    self.assertEqual(os.environ['PULSE_SINK'], 'new-user-sink')
                    process.stdin.close.assert_called_once()
                    process.wait.assert_called_once()


if __name__ == '__main__':
    unittest.main()
