"""Publish an existing reviewed draft, never substitute a legacy runtime build."""

from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
REPO = 'THXel/Boshy-Randomizer'


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)


def main():
    if (
        os.environ.get('GITHUB_REPOSITORY') != REPO
        or os.environ.get('GITHUB_REF') != 'refs/heads/Boshy-Randomizer'
    ):
        raise SystemExit('Publish only from the reviewed project branch.')
    cfg = json.loads((ROOT / 'packaging/release.json').read_text())
    release = json.loads(gh('api', f'repos/{REPO}/releases/tags/{cfg["tag"]}'))
    if not release['draft']:
        raise SystemExit('Refusing to modify an already published release.')
    commit = gh('api', f'repos/{REPO}/commits/{cfg["tag"]}', '--jq', '.sha').strip()
    if commit != os.environ['GITHUB_SHA']:
        raise SystemExit('Draft tag does not match the reviewed source commit.')
    expected = cfg['assets']
    assets = {a['name']: a for a in release['assets']}
    if set(assets) != set(expected):
        raise SystemExit('Draft assets do not match the release manifest.')
    with tempfile.TemporaryDirectory() as tmp:
        gh('release', 'download', cfg['tag'], '--repo', REPO, '--dir', tmp)
        for name, spec in expected.items():
            path = Path(tmp) / name
            with path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            if digest != spec['sha256'] or path.stat().st_size != spec['bytes']:
                raise SystemExit('Asset verification failed: ' + name)
            if assets[name].get('digest') != 'sha256:' + digest:
                raise SystemExit('GitHub asset digest mismatch: ' + name)
    gh(
        'release',
        'edit',
        cfg['tag'],
        '--repo',
        REPO,
        '--title',
        cfg['title'],
        '--notes-file',
        str(ROOT / cfg['notes']),
        '--draft=false',
        '--prerelease=false',
        '--latest',
    )
    print(f'https://github.com/{REPO}/releases/tag/{cfg["tag"]}')


if __name__ == '__main__':
    main()
