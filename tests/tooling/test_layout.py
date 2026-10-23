"""Exercise the source/deployment boundary and failed-build preservation."""

from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tools'))
from layout import MANIFEST, assemble, source_map, verify_build, verify_generated


class LayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'repo'
        self.target = self.root / 'build/runtime'
        self.put('src/python/app/native_menu_host.py', 'print("menu")\n')
        self.put('src/python/rules/native_triggers.py', 'RULE_VERSION=3\n')
        self.put('tools/native/build_runtime.py', 'print("builder")\n')
        self.put('assets/INI/positions.json', '{}')
        self.put('src/shared/PY/__init__.py', '')
        self.put('tests/runtime/fixtures/old_rules.txt', 'old rule bytes')

    def put(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def assemble(self, builder=None):
        return assemble(root=self.root, target=self.target, native_builder=builder)

    def test_domains_assemble_to_stable_module_and_resource_names(self):
        metadata = self.assemble()
        self.assertEqual(
            (self.target / 'native_triggers.py').read_bytes(),
            (self.root / 'src/python/rules/native_triggers.py').read_bytes(),
        )
        self.assertEqual(
            (self.target / 'tests/fixtures/old_rules.txt').read_text(), 'old rule bytes'
        )
        self.assertIn('PY/__init__.py', metadata['outputs'])
        self.assertIn('INI/positions.json', metadata['outputs'])
        with self.assertRaisesRegex(ValueError, 'not been built'):
            verify_build(self.target, self.root)

    def test_duplicate_flat_module_name_rejected_before_existing_build_changes(self):
        self.assemble()
        before = (self.target / MANIFEST).read_bytes()
        self.put('src/python/menu/native_triggers.py', 'different')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.assemble()
        self.assertEqual((self.target / MANIFEST).read_bytes(), before)

    def test_local_edits_and_unknown_files_are_never_overwritten(self):
        self.assemble()
        for name in ('native_menu_host.py', 'private.txt'):
            with self.subTest(name=name):
                path = self.target / name
                original = path.read_bytes() if path.exists() else None
                path.write_text('local work')
                with self.assertRaisesRegex(ValueError, 'Generated files changed'):
                    self.assemble()
                self.assertEqual(path.read_text(), 'local work')
                if original is None:
                    path.unlink()
                else:
                    path.write_bytes(original)

    def test_private_runtime_directories_block_replacement_even_when_empty(self):
        self.assemble()
        for name in (
            'IWBTB',
            'native-runs',
            'rule-versions',
            'wineprefix',
            'soundpacks',
        ):
            path = self.target / name
            path.mkdir()
            with (
                self.subTest(name=name),
                self.assertRaisesRegex(ValueError, 'Private runtime'),
            ):
                self.assemble()
            self.assertTrue(path.is_dir())
            path.rmdir()

    def test_failed_compilation_keeps_previous_build(self):
        self.assemble()
        before = (self.target / MANIFEST).read_bytes()
        self.put('src/python/app/native_menu_host.py', 'new source')

        def fail(stage):
            (stage / 'native_extras.dll').write_bytes(b'partial')
            raise RuntimeError('compiler failed')

        with self.assertRaisesRegex(RuntimeError, 'compiler failed'):
            self.assemble(fail)
        self.assertEqual((self.target / MANIFEST).read_bytes(), before)
        self.assertEqual(
            (self.target / 'native_menu_host.py').read_text(), 'print("menu")\n'
        )
        self.assertFalse(list(self.target.parent.glob('.boshy-build-*')))

    def test_changed_source_is_stale_and_removed_source_is_not_left_behind(self):
        self.assemble(
            lambda stage: (stage / 'native_extras.dll').write_bytes(b'native')
        )
        verify_build(self.target, self.root)
        (self.root / 'src/python/rules/native_triggers.py').unlink()
        with self.assertRaisesRegex(ValueError, 'stale'):
            verify_build(self.target, self.root)
        self.assemble()
        self.assertFalse((self.target / 'native_triggers.py').exists())
        self.assertFalse((self.target / 'native_extras.dll').exists())

    def test_source_change_during_build_is_rejected(self):
        def change(stage):
            self.put('src/python/rules/native_triggers.py', 'changed while compiling')

        with self.assertRaisesRegex(ValueError, 'Source changed during build'):
            self.assemble(change)
        self.assertFalse(self.target.exists())

    def test_linked_source_and_target_are_rejected(self):
        outside = self.put('private/data.txt', 'private')
        link = self.root / 'src/python/app/linked.py'
        try:
            link.symlink_to(outside)
        except OSError:
            self.skipTest('Symlinks unavailable')
        with self.assertRaisesRegex(ValueError, 'Linked source'):
            source_map(self.root)
        link.unlink()
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(outside.parent, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Linked build'):
            self.assemble()
        self.assertEqual(outside.read_text(), 'private')

    def test_linked_source_directory_is_rejected_instead_of_silently_omitted(self):
        outside = self.root / 'private'
        outside.mkdir()
        link = self.root / 'src/python/linked'
        try:
            link.symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Symlinks unavailable')
        with self.assertRaisesRegex(ValueError, 'Linked source'):
            source_map(self.root)

    def test_unmanaged_target_and_build_metadata_never_get_packaged(self):
        self.target.mkdir(parents=True)
        (self.target / 'SaveFile1.ini').write_text('private save')
        with self.assertRaisesRegex(ValueError, 'Not a managed build'):
            self.assemble()
        self.assertEqual((self.target / 'SaveFile1.ini').read_text(), 'private save')
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'packaging'))
        from payload import ROOT_EXCLUDE

        self.assertIn(MANIFEST, ROOT_EXCLUDE)


if __name__ == '__main__':
    unittest.main()
