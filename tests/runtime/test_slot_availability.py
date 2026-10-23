import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from native_models import slot_available, slot_summary
from PY.file_utils import smart_read
from PY.rc4_utils import rc4_crypt


class SaveSlots(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        (self.base / 'IWBTB').mkdir()
        self.path = self.base / 'IWBTB/SaveFile1.ini'
        self.store = SimpleNamespace(
            base=self.base,
            current=lambda slot: None,
            read_save=lambda p: smart_read(str(p))[0],
        )

    def save(self, text):
        self.path.write_bytes(rc4_crypt(b'BLOB', text.encode('latin1')))

    def test_absent_and_empty_are_free(self):
        self.assertTrue(slot_available(self.store, 1))
        self.path.touch()
        self.assertFalse(slot_summary(self.store, 1)['exists'])

    def test_real_failed_start_fixture_is_free_without_changing_bytes(self):
        self.save(
            '[Check]\r\nSaveVersion=1\r\n[Stats]\r\nDifficulty=2\r\nTimeSeconds=159'
        )
        before = self.path.read_bytes()
        self.assertTrue(slot_available(self.store, 1))
        self.assertFalse(slot_summary(self.store, 1)['exists'])
        self.assertEqual(before, self.path.read_bytes())

    def test_stub_created_after_menu_open_is_still_free(self):
        self.assertFalse(slot_summary(self.store, 1)['exists'])
        self.save(
            '[Check]\r\nSaveVersion=1\r\n[Stats]\r\nDifficulty=2\r\nTimeSeconds=159'
        )
        self.assertTrue(slot_available(self.store, 1))

    def test_actual_progress_is_protected(self):
        for section in (
            'Positions',
            'Collectables',
            'Achievements',
            'RandoChecks',
            'Unknown',
        ):
            with self.subTest(section=section):
                self.save('[Stats]\nDifficulty=2\n[' + section + ']\nentry=1')
                self.assertFalse(slot_available(self.store, 1))

    def test_managed_slots_never_become_free(self):
        for status in ('ready', 'preparing', 'restoring'):
            with self.subTest(status=status):
                self.store.current = lambda slot: {'status': status}
                self.assertFalse(slot_available(self.store, 1))
                self.path.touch()
                self.assertFalse(slot_available(self.store, 1))

    def test_restored_slot_can_be_reused(self):
        self.store.current = lambda slot: {'status': 'restored'}
        self.assertTrue(slot_available(self.store, 1))

    def test_unknown_or_damaged_data_is_protected(self):
        for text in (
            'garbage',
            '  ',
            '[Stats]\nDifficulty=9',
            '[Stats]\nTimeSeconds=-1',
            '[Stats]\nDeaths=4',
            '[Check]\nSaveVersion=2',
            '[Stats]\nDifficulty=1\nDifficulty=2',
            '[DEFAULT]\nx=1\n[Stats]\nDifficulty=1',
        ):
            with self.subTest(text=text):
                self.save(text)
                self.assertFalse(slot_available(self.store, 1))

    def test_symlinks_are_protected(self):
        target = self.base / 'elsewhere'
        target.touch()
        self.path.symlink_to(target)
        self.assertFalse(slot_available(self.store, 1))
        target.unlink()
        self.assertFalse(slot_available(self.store, 1))

    def test_slots_are_independent(self):
        self.save('[Positions]\nframe=3\nxPos=30\nyPos=40')
        self.assertFalse(slot_available(self.store, 1))
        self.assertTrue(slot_available(self.store, 2))
        self.assertTrue(slot_available(self.store, 3))


if __name__ == '__main__':
    unittest.main(verbosity=2)
