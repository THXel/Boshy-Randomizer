import hashlib
import json
import os
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import game_import as gi
import wine_setup as ws


class GameImport(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.base = self.root / 'runtime'
        (self.base / 'INI').mkdir(parents=True)
        for name in ('characters.json', 'characters_rando.json'):
            (self.base / 'INI' / name).write_bytes((ROOT / 'INI' / name).read_bytes())
        self.source = self.root / 'original'
        self.source.mkdir()
        (self.source / gi.EXE).write_bytes(b'fixture-game')
        (self.source / 'Custom').mkdir()
        (self.source / 'Custom/asset.txt').write_text('asset')
        (self.source / 'SaveFile1.ini').write_text('private-save')
        (self.source / 'onlineLicense.ini').write_text('private-profile')
        self.patcher = patch.object(
            gi, 'EXPECTED', hashlib.sha256(b'fixture-game').hexdigest()
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_folder_is_private_copy_without_progress(self):
        dest = gi.import_game(self.source, self.base)
        self.assertEqual((dest / 'Custom/asset.txt').read_text(), 'asset')
        self.assertFalse((dest / 'SaveFile1.ini').exists())
        self.assertNotEqual(
            (dest / 'onlineLicense.ini').read_bytes(), b'private-profile'
        )
        self.assertEqual((self.source / 'SaveFile1.ini').read_text(), 'private-save')
        from PY.file_utils import smart_read

        text, encrypted = smart_read(str(dest / 'options.ini'))
        self.assertTrue(encrypted)
        self.assertIn('ScreenSize=880', text)

    def test_wrapped_zip_and_windows_paths(self):
        path = self.root / 'game.zip'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr('Game\\' + gi.EXE, b'fixture-game')
            z.writestr('Game\\Custom\\asset.txt', 'asset')
            z.writestr('Game\\SaveFile1.ini', 'private')
        dest = gi.import_game(path, self.base)
        self.assertEqual((dest / 'Custom/asset.txt').read_text(), 'asset')
        self.assertFalse((dest / 'SaveFile1.ini').exists())

    def test_existing_destination_is_never_replaced(self):
        gi.import_game(self.source, self.base)
        with self.assertRaises(ValueError):
            gi.import_game(self.source, self.base)

    def test_wrong_executable_is_rejected_atomically(self):
        (self.source / gi.EXE).write_bytes(b'wrong-version')
        with self.assertRaises(ValueError):
            gi.import_game(self.source, self.base)
        self.assertFalse((self.base / 'IWBTB').exists())
        self.assertFalse(list(self.base.glob('.game-import-*')))

    def test_unsafe_zip_paths(self):
        for name in ('../outside', 'C:\\escape', '/absolute', 'x/../../escape'):
            with self.subTest(name=name):
                path = self.root / 'unsafe.zip'
                with zipfile.ZipFile(path, 'w') as z:
                    z.writestr(gi.EXE, b'fixture-game')
                    z.writestr(name, 'unsafe')
                with self.assertRaises(ValueError):
                    gi.import_game(path, self.base)
                self.assertFalse((self.base / 'IWBTB').exists())

    def test_case_collision_rejected(self):
        path = self.root / 'duplicates.zip'
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr(gi.EXE, b'fixture-game')
            z.writestr('Custom/A', 'a')
            z.writestr('Custom/a', 'b')
        with self.assertRaises(ValueError):
            gi.import_game(path, self.base)

    def test_symlinks_rejected(self):
        (self.source / 'Custom/link').symlink_to(self.source / gi.EXE)
        with self.assertRaises(ValueError):
            gi.import_game(self.source, self.base)

    def test_zip_symlink_rejected(self):
        path = self.root / 'symlink.zip'
        info = zipfile.ZipInfo('Custom/link')
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(path, 'w') as z:
            z.writestr(gi.EXE, b'fixture-game')
            z.writestr(info, '../outside')
        with self.assertRaises(ValueError):
            gi.import_game(path, self.base)

    def test_size_limit(self):
        with patch.object(gi, 'LIMIT', 2), self.assertRaises(ValueError):
            gi.import_game(self.source, self.base)


class RuntimeResources(unittest.TestCase):
    def test_empty_engine_created_slot_is_available(self):
        from types import SimpleNamespace
        from native_models import slot_summary

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            (base / 'IWBTB').mkdir()
            (base / 'IWBTB/SaveFile1.ini').touch()
            store = SimpleNamespace(base=base, current=lambda slot: None)
            self.assertFalse(slot_summary(store, 1)['exists'])

    def test_loading_catalogue_has_all_icons(self):
        from loading_destination import for_frame

        data = json.loads((ROOT / 'loading-icons/index.json').read_text())
        for frame in [*data, 999]:
            with self.subTest(frame=frame):
                self.assertTrue(Path(for_frame(ROOT, frame)['icon']).is_file())

    def test_production_entrypoint_imports(self):
        import native_menu_host

        self.assertTrue(callable(native_menu_host.run))


class WineVerification(unittest.TestCase):
    def test_modified_runner_is_not_reused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'wine').write_bytes(b'verified')
            m = root / 'manifest.json'
            m.write_text(
                json.dumps(
                    {
                        'files': {'wine': hashlib.sha256(b'verified').hexdigest()},
                        'links': {},
                    }
                )
            )
            with patch.object(ws, 'MANIFEST', m):
                self.assertTrue(ws.verified(root))
                (root / 'wine').write_bytes(b'modified')
                self.assertFalse(ws.verified(root))

    def test_verified_existing_runner_avoids_network(self):
        with (
            tempfile.TemporaryDirectory() as tmp,
            patch.dict(os.environ, {'XDG_DATA_HOME': tmp}),
        ):
            path = Path(tmp) / 'lutris/runners/wine' / ws.NAME
            path.mkdir(parents=True)
            with (
                patch.object(ws, 'verified', side_effect=lambda p: p == path),
                patch.object(ws.urllib.request, 'urlopen') as network,
            ):
                self.assertEqual(ws.ensure_runner(), path / 'bin/wine')
                network.assert_not_called()


if __name__ == '__main__':
    unittest.main()
