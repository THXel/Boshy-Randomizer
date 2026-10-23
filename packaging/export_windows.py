#!/usr/bin/env python3
"""Export only public runtime assets; no game, saves, user settings or Wine."""

from pathlib import Path
import argparse
import hashlib
import json
import shutil
import sys
from payload import runtime_files


def export(source, target, version):
    source = Path(source).resolve()
    target = Path(target).resolve()
    sys.path.insert(0, str(source))
    from trigger_audit import FILES

    files = runtime_files(source, platform='windows', audit_files=FILES)
    if target.exists() and any(target.iterdir()):
        raise ValueError('Choose an empty export directory')
    target.mkdir(parents=True, exist_ok=True)
    hashes = {}
    seen = {}
    for p in sorted(set(files)):
        name = p.relative_to(source).as_posix()
        data = p.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        key = name.casefold()
        if key in seen:
            if seen[key] != digest:
                raise ValueError('Windows filename collision: ' + name)
            continue
        seen[key] = digest
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        hashes[name] = digest
    release = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()
    (target / 'package-files.json').write_text(
        json.dumps(dict(version=version, release=release, files=hashes), indent=2)
        + '\n',
        encoding='utf-8',
    )
    return hashes


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    parser.add_argument(
        '--source',
        type=Path,
        default=Path(__file__).resolve().parents[1] / 'build/runtime',
    )
    parser.add_argument(
        '--version',
        default=json.loads((Path(__file__).parent / 'release.json').read_text())[
            'version'
        ],
    )
    a = parser.parse_args()
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
    from layout import verify_build

    verify_build(a.source)
    print('Exported', len(export(a.source, a.output, a.version)), 'files')
