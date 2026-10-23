"""Publish reviewed Windows + freshly tested Linux assets as one GitHub release.

Executed by release.yml with the repository-scoped GITHUB_TOKEN. The Windows
installer is rebuilt in the same workflow, installation tested and hash checked.
"""

from pathlib import Path
import hashlib
import json
import os
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / 'packaging/release.json').read_text())
REPO = 'THXel/Boshy-Randomizer'
OUT = ROOT / 'dist'
OUT.mkdir(exist_ok=True)


def gh(*args):
    return subprocess.check_output(['gh', *args], text=True)


def api(path, *args):
    return json.loads(gh('api', path, *args))


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if (
        os.environ.get('GITHUB_REPOSITORY') != REPO
        or os.environ.get('GITHUB_REF') != 'refs/heads/Boshy-Randomizer'
    ):
        raise SystemExit('Release publication is restricted to the project branch.')
    linux = OUT / CFG['linux_file']
    if not linux.is_file():
        raise SystemExit('Build and test the Linux package first.')
    win = OUT / CFG['windows_file']
    report = json.loads((OUT / 'windows-build.json').read_text(encoding='utf-8-sig'))
    if (
        report.get('source_commit') != os.environ['GITHUB_SHA']
        or report.get('version') != CFG['version']
        or report.get('file') != win.name
        or report.get('installed_files', 0) < 100
        or not win.is_file()
        or digest(win) != report.get('sha256')
    ):
        raise SystemExit('Windows build provenance or checksum mismatch.')
    sums = OUT / 'SHA256SUMS'
    sums.write_text(''.join(f'{digest(p)}  {p.name}\n' for p in (win, linux)))
    notes = (ROOT / CFG['notes']).read_text()
    for rel in ('WINDOWS_PACKAGE.md', 'LINUX_PACKAGE.md'):
        notes = notes.replace(
            f']({rel})', f'](https://github.com/{REPO}/blob/{CFG["tag"]}/docs/{rel})'
        )
    notes = notes.replace(
        '](../CHANGELOG.md)',
        f'](https://github.com/{REPO}/blob/{CFG["tag"]}/CHANGELOG.md)',
    )
    notesfile = OUT / 'release-notes.md'
    notesfile.write_text(notes)
    releases = api(f'repos/{REPO}/releases?per_page=100')
    existing = next((x for x in releases if x['tag_name'] == CFG['tag']), None)
    if existing and not existing['draft']:
        raise SystemExit(
            'This release is already published. Refusing to replace public downloads.'
        )
    if not existing:
        gh(
            'release',
            'create',
            CFG['tag'],
            '--repo',
            REPO,
            '--target',
            os.environ['GITHUB_SHA'],
            '--draft',
            '--title',
            CFG['title'],
            '--notes-file',
            str(notesfile),
        )
    else:
        gh(
            'release',
            'edit',
            CFG['tag'],
            '--repo',
            REPO,
            '--title',
            CFG['title'],
            '--notes-file',
            str(notesfile),
        )
    gh(
        'release',
        'upload',
        CFG['tag'],
        str(win),
        str(linux),
        str(sums),
        '--repo',
        REPO,
        '--clobber',
    )
    draft = next(
        x
        for x in api(f'repos/{REPO}/releases?per_page=100')
        if x['tag_name'] == CFG['tag']
    )
    check = api(f'repos/{REPO}/releases/{draft["id"]}')
    uploaded = {x['name']: x for x in check['assets']}
    for p in (win, linux, sums):
        a = uploaded[p.name]
        if a['size'] != p.stat().st_size or a.get('digest') != 'sha256:' + digest(p):
            raise SystemExit('Uploaded asset verification failed: ' + p.name)
    gh('release', 'edit', CFG['tag'], '--repo', REPO, '--draft=false', '--latest')
    print(f'Published https://github.com/{REPO}/releases/tag/{CFG["tag"]}')


if __name__ == '__main__':
    main()
