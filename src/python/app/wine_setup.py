"""Provision the pinned Lutris Wine build; never change a user's existing runner."""

from pathlib import Path
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request

NAME = 'wine-staging-11.2-x86_64'
URL = 'https://github.com/Kron4ek/Wine-Builds/releases/download/11.2/wine-11.2-staging-amd64-wow64.tar.xz'
SHA256 = 'edd598a710b3738bd0183bbb393b26d91179a0d0d421b51dd9df001aa7b1eeb9'
ARCHIVE_ROOT = 'wine-11.2-staging-amd64-wow64'
MANIFEST = Path(__file__).with_name('wine-runner-manifest.json')


def verified(root):
    root = Path(root)
    if not root.is_dir():
        return False
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    try:
        for name, want in data['files'].items():
            p = root / name
            if p.is_symlink() or hashlib.sha256(p.read_bytes()).hexdigest() != want:
                return False
        for name, target in data['links'].items():
            if not (root / name).is_symlink() or os.readlink(root / name) != target:
                return False
    except OSError:
        return False
    return True


def ensure_runner(status=lambda message: None):
    runners = (
        Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))
        / 'lutris/runners/wine'
    )
    runners.mkdir(parents=True, exist_ok=True)
    with (runners / '.boshy-runner.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        status('Checking Wine Staging 11.2…')
        for name in (NAME, 'boshy-' + NAME):
            root = runners / name
            if verified(root):
                return root / 'bin/wine'
        # Keep an existing Lutris runner intact, even if it was modified by its owner.
        target = runners / ('boshy-' + NAME)
        if target.exists():
            raise RuntimeError(
                'The private Wine runner failed verification. Rename it and try again: '
                + str(target)
            )
        with tempfile.TemporaryDirectory(prefix='.boshy-wine-', dir=runners) as tmp:
            tmp = Path(tmp)
            archive = tmp / 'wine.tar.xz'
            digest = hashlib.sha256()
            size = 0
            status('Downloading Wine Staging 11.2 (72 MiB)…')
            request = urllib.request.Request(
                URL, headers={'User-Agent': 'Boshy-Randomizer/2026.10'}
            )
            with (
                urllib.request.urlopen(request, timeout=45) as source,
                archive.open('wb') as dest,
            ):
                while block := source.read(1024 * 1024):
                    size += len(block)
                    if size > 100 * 1024**2:
                        raise RuntimeError('Wine download exceeds the expected size.')
                    digest.update(block)
                    dest.write(block)
            if digest.hexdigest() != SHA256:
                raise RuntimeError(
                    'Wine download verification failed. Please try again.'
                )
            status('Installing verified Wine Staging 11.2…')
            with tarfile.open(archive) as t:
                t.extractall(tmp / 'unpacked', filter='data')
            root = tmp / 'unpacked' / ARCHIVE_ROOT
            if not verified(root):
                raise RuntimeError('Extracted Wine runner failed verification.')
            os.rename(root, target)
        return target / 'bin/wine'


def prepare_wine(base, status=lambda message: None):
    wine = ensure_runner(status)
    os.environ['BOSHY_WINE'] = str(wine)
    if not (base / 'wineprefix/system.reg').exists():
        status('Preparing your private Wine environment…')
        env = {
            **os.environ,
            'WINEPREFIX': str(base / 'wineprefix'),
            'WINEDEBUG': '-all',
            'WINEDLLOVERRIDES': 'mscoree,mshtml=',
            'WINEESYNC': '0',
            'WINEFSYNC': '0',
        }
        with (base / 'evidence/wine-setup.log').open('w') as log:
            subprocess.run(
                [str(wine), 'wineboot', '-u'],
                env=env,
                stdout=log,
                stderr=log,
                check=True,
                timeout=180,
            )
    return wine
