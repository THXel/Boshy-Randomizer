"""Packaging must exclude retired code and private configuration on both hosts."""
import ast
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'packaging'))
from payload import INI_CATALOGUES, PY_MODULES, runtime_files


class PackagePayload(unittest.TestCase):
    def make_source(self, root):
        for name in [*(f'PY/{n}.py' for n in PY_MODULES),
                     *(f'INI/{n}' for n in INI_CATALOGUES),
                     'native_player.py', 'native_extras.dll', 'fast_exit.c',
                     'start-linux.sh', 'wine_setup.py', 'package_bootstrap.py',
                     'wine-runner-manifest.json', 'Custom/logo.png']:
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'fixture')

    def test_private_settings_and_retired_modules_never_enter_packages(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_source(root)
            forbidden = ('PY/twitch_integration.py', 'PY/gui_config.py',
                         'PY/item_randomizer.py', 'INI/twitch_config.json',
                         'INI/settings.json', 'INI/native-live.json',
                         'INI/stats.json', 'source-manifest.json',
                         'package-files.json', 'installed-runtime.json')
            for name in forbidden:
                (root / name).write_text('private or obsolete')
            for platform in ('linux', 'windows'):
                names = {p.relative_to(root).as_posix() for p in runtime_files(root, platform=platform, audit_files=('fast_exit.c',))}
                self.assertFalse(names.intersection(forbidden))
                self.assertIn('native_player.py', names)
                self.assertIn('fast_exit.c', names)
                self.assertIn('PY/live_tracker.py', names)
                self.assertEqual('start-linux.sh' in names, platform == 'linux')
                self.assertEqual('wine_setup.py' in names, platform == 'linux')

    def test_missing_required_helper_fails_before_export(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.make_source(root)
            (root / 'PY/save_utils.py').unlink()
            with self.assertRaisesRegex(ValueError, 'save_utils.py'):
                runtime_files(root, platform='linux')

    def test_linked_catalogue_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / 'source'
            root.mkdir()
            self.make_source(root)
            (root / 'INI').rename(Path(folder) / 'private')
            try:
                (root / 'INI').symlink_to(Path(folder) / 'private', target_is_directory=True)
            except OSError:
                self.skipTest('Directory symlinks not available')
            with self.assertRaises(ValueError):
                runtime_files(root, platform='linux')

    def test_invalid_platform_is_rejected(self):
        with self.assertRaises(ValueError):
            runtime_files(ROOT, platform='invalid')

    def test_current_runtime_imports_only_packaged_py_helpers(self):
        modules = set(PY_MODULES)
        for path in (ROOT / 'native-linux').rglob('*.py'):
            if '__pycache__' in path.parts:
                continue
            tree = ast.parse(path.read_text(encoding='utf-8-sig'))
            for node in ast.walk(tree):
                imported = []
                if isinstance(node, ast.ImportFrom) and node.module == 'PY':
                    imported = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and (node.module or '').startswith('PY.'):
                    imported = [node.module.split('.')[1]]
                elif isinstance(node, ast.Import):
                    imported = [alias.name.split('.')[1] for alias in node.names if alias.name.startswith('PY.')]
                for name in imported:
                    self.assertIn(name, modules, f'{path}: {name} is not packaged')


if __name__ == '__main__':
    unittest.main()
