"""Linux package registration and update boundaries without touching live Lutris."""

import json
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch
from distribution.linux import launcher


class LinuxPackageTests(unittest.TestCase):
    def test_registration_lookup_is_exact_and_read_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'lutris').mkdir()
            with sqlite3.connect(root / 'lutris/pga.db') as db:
                db.execute('CREATE TABLE games (id INTEGER, installer_slug TEXT, installed INTEGER)')
                db.executemany('INSERT INTO games VALUES (?, ?, ?)', [(1, 'original-boshy', 1), (2, launcher.SLUG, 0)])
            with patch.object(launcher, 'DATA', root):
                self.assertIsNone(launcher.registered_game())
                with sqlite3.connect(root / 'lutris/pga.db') as db:
                    db.execute('INSERT INTO games VALUES (3, ?, 1)', (launcher.SLUG,))
                self.assertEqual(launcher.registered_game(), 3)
                with sqlite3.connect(root / 'lutris/pga.db') as db:
                    db.execute('INSERT INTO games VALUES (4, ?, 1)', (launcher.SLUG,))
                with self.assertRaises(RuntimeError):
                    launcher.registered_game()

    def test_existing_entry_does_not_register_duplicate_or_reinstall(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            app = base / 'app'
            app.mkdir()
            spec = {'version': 'v1', 'setup_sha256': 'a' * 64}
            (app / 'package-info.json').write_text(json.dumps(spec))
            (base / 'installed-package.json').write_text(json.dumps(spec))
            installed = base / 'wineprefix/drive_c/Program Files/Boshy Randomizer'
            installed.mkdir(parents=True)
            (installed / 'active.json').write_text('{"version":"v1"}')
            wine = types.SimpleNamespace(ensure_runner=lambda status: Path('/runner/bin/wine'))
            with (patch.object(launcher, 'HERE', app), patch.object(launcher, 'BASE', base),
                  patch.object(launcher.os, 'geteuid', return_value=1000),
                  patch.object(launcher.shutil, 'which', return_value='/usr/bin/lutris'),
                  patch.dict(sys.modules, {'wine_setup': wine}),
                  patch.object(launcher, 'registered_game', return_value=23),
                  patch.object(launcher, 'install_artwork') as artwork,
                  patch.object(launcher.subprocess, 'run') as run,
                  patch.object(launcher.subprocess, 'Popen') as popen):
                self.assertEqual(launcher.prepare('run', lambda s: None), '23')
                artwork.assert_called_once_with(app, base, 23)
                run.assert_not_called()
                popen.assert_not_called()
                (base / 'installed-package.json').unlink()
                (app / 'BoshyRandomizer-Setup.exe').write_bytes(b'damaged')
                with self.assertRaises(RuntimeError):
                    launcher.prepare('setup', lambda s: None)
                run.assert_not_called()
                self.assertTrue((installed / 'active.json').exists())

    def test_runner_environment_preserves_host_environment_and_isolates_prefix(self):
        before = dict(launcher.os.environ)
        env = launcher.wine_environment(Path('/runner/bin/wine'))
        self.assertEqual(dict(launcher.os.environ), before)
        self.assertEqual(env['WINEPREFIX'], str(launcher.BASE / 'wineprefix'))
        self.assertEqual(env['WINEESYNC'], '0')
        self.assertIn('winemenubuilder.exe=d', env['WINEDLLOVERRIDES'])
