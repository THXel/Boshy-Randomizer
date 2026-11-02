"""Local integration tests for the pinned private Fusion build and export boundary."""
import configparser
import json
from pathlib import Path
import runpy
import tempfile
import unittest
from export_seed_probe import export as export_current, REPO, ROOT
from functools import partial

# This prototype predates the original-spawn correction; retain its pinned ABI.
export = partial(export_current, positions_path=ROOT / "outputs/Fusion-PositionNames-20261025/before/repo/assets/INI/positions.json")
import fusion_route
import seed_codec
import seed_share

GAME = Path('/home/thxel/Games/clickteam-fusion-developer/drive_c/BoshyTransitions/Boshy-frame-links.exe')


def code(seed='fusion-1', **changes):
    options = seed_codec.defaults()
    options.update(level_pool=['save1.ini', 'save7.ini'], level_count=2,
                   boss_pool=['cheetahman'], route_boss_count=1, items=False)
    options.update(changes)
    return seed_share.encode(seed, options)


@unittest.skipUnless(GAME.exists(), 'Private pinned Fusion build is required')
class ExportTests(unittest.TestCase):
    def test_encrypted_export_contains_exact_seed_route(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'probe'
            plan = export(code(), GAME, out)
            decrypt = runpy.run_path(str(REPO/'src/shared/PY/rc4_utils.py'))['rc4_crypt']
            ini = configparser.ConfigParser(interpolation=None)
            ini.read_string(decrypt(b'BLOB', (out/'SaveFile1.ini').read_bytes()).decode('latin1'))
            self.assertEqual(ini.getint(fusion_route.GROUP, 'CheetahRoute'), 1)
            self.assertEqual(ini.get(fusion_route.GROUP, 'Binding'), plan['binding'])
            self.assertEqual(json.loads((out/'plan.json').read_text())['route'], plan['route'])

    def test_existing_directory_and_save_are_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory);save = out/'SaveFile1.ini';save.write_bytes(b'untouched')
            with self.assertRaises(FileExistsError):export(code(), GAME, out)
            self.assertEqual(save.read_bytes(), b'untouched')
            self.assertEqual([p.name for p in out.iterdir()], ['SaveFile1.ini'])

    def test_unsupported_successor_creates_no_export(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'rejected'
            with self.assertRaisesRegex(ValueError, 'boss_solgryn'):
                export(code(level_count=0, level_pool=[]), GAME, out)
            self.assertFalse(out.exists())

    def test_wrong_build_creates_no_export(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);wrong = root/'wrong.exe';wrong.write_bytes(b'not the tested build')
            with self.assertRaisesRegex(ValueError, 'build'):
                export(code(), wrong, root/'rejected')
            self.assertFalse((root/'rejected').exists())


if __name__ == '__main__':unittest.main()
