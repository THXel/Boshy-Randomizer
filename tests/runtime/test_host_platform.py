import sys
import unittest
import io
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import host_platform as h


class Transport(unittest.TestCase):
    def test_windows_children_initialize_private_module_path(self):
        with (
            patch.object(h, 'WINDOWS', True),
            patch.object(h.sys, 'executable', '/bundle/runtime/pythonw.exe'),
            patch.dict(h.os.environ, {'BOSHY_DATA_HOME': '/private'}),
        ):
            self.assertEqual(
                h.python_command('loading_screen.py', '--window', '{}'),
                [
                    '/bundle/runtime/python.exe',
                    '/private/windows_entry.py',
                    '--component',
                    'loading_screen.py',
                    '--window',
                    '{}',
                ],
            )

    def test_loading_cover_styles_the_toplevel_wrapper(self):
        from types import SimpleNamespace

        user = Mock()
        user.GetAncestor.return_value = 202
        user.GetWindowLongW.return_value = 0x40000
        with (
            patch.object(h, 'WINDOWS', True),
            patch.dict(sys.modules, {'windows_api': SimpleNamespace(user=user)}),
        ):
            self.assertEqual(h.nonactivating_window(101), 202)
        user.GetAncestor.assert_called_once_with(101, 2)
        user.SetWindowLongW.assert_called_once_with(202, -20, 0x08040020)

    def test_loading_cover_keeps_top_level_handle_if_already_root(self):
        from types import SimpleNamespace

        user = Mock()
        user.GetAncestor.return_value = 0
        user.GetWindowLongW.return_value = 0
        with (
            patch.object(h, 'WINDOWS', True),
            patch.dict(sys.modules, {'windows_api': SimpleNamespace(user=user)}),
        ):
            self.assertEqual(h.nonactivating_window(101), 101)
        user.SetWindowLongW.assert_called_once_with(101, -20, 0x08000020)

    def test_loading_cover_yields_only_its_own_foreground(self):
        from types import SimpleNamespace

        user = Mock()
        user.GetAncestor.return_value = 202
        user.GetWindowLongW.return_value = 0
        with (
            patch.object(h, 'WINDOWS', True),
            patch.dict(sys.modules, {'windows_api': SimpleNamespace(user=user)}),
            patch('game_focus.activate_game', return_value=True) as focus,
        ):
            user.GetForegroundWindow.return_value = 999
            h.nonactivating_window(101, handoff=True)
            focus.assert_not_called()
            user.GetForegroundWindow.return_value = 202
            h.nonactivating_window(101, handoff=True)
            focus.assert_called_once_with()

    def test_pipe_lines_and_eof(self):
        r = h.LineReader(io.StringIO('first\nsecond\n'))
        self.assertEqual(r.readline(), 'first\n')
        self.assertEqual(r.readline(), 'second\n')
        with self.assertRaisesRegex(RuntimeError, 'Bridge exited'):
            r.readline()

    def test_windows_sharing_retry_preserves_target_until_success(self):
        with (
            patch.object(h, 'WINDOWS', True),
            patch.object(
                h.os, 'replace', side_effect=[PermissionError(), None]
            ) as replace,
            patch.object(h.time, 'sleep'),
        ):
            h.replace_file('new', 'old')
            self.assertEqual(replace.call_count, 2)

    def test_other_errors_are_not_retried(self):
        with (
            patch.object(h, 'WINDOWS', True),
            patch.object(h.os, 'replace', side_effect=FileNotFoundError()) as replace,
        ):
            with self.assertRaises(FileNotFoundError):
                h.replace_file('new', 'old')
            self.assertEqual(replace.call_count, 1)

    def test_linux_permission_denied_is_not_retried(self):
        with (
            patch.object(h, 'WINDOWS', False),
            patch.object(h.os, 'replace', side_effect=PermissionError()) as replace,
        ):
            with self.assertRaises(PermissionError):
                h.replace_file('new', 'old')
            self.assertEqual(replace.call_count, 1)

    def test_windows_path_has_no_wine_drive(self):
        with patch.object(h, 'WINDOWS', True):
            self.assertEqual(
                h.native_path('C:/test/native_menu.dll'), r'C:\test\native_menu.dll'
            )

    def test_linux_path_keeps_wine_drive(self):
        with patch.object(h, 'WINDOWS', False):
            self.assertEqual(
                h.native_path('/test/native_menu.dll'), r'Z:\test\native_menu.dll'
            )

    def test_windows_identity_rejects_other_game_copy(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(h, 'WINDOWS', True):
            root = Path(tmp)
            p = Mock()
            p.exe.return_value = str(root / 'IWBTB/I Wanna Be The Boshy.exe')
            self.assertTrue(h.owned_process(p, root))
            p.exe.return_value = str(root / 'other/I Wanna Be The Boshy.exe')
            self.assertFalse(h.owned_process(p, root))


if __name__ == '__main__':
    unittest.main()
