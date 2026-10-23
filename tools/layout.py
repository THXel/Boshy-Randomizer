"""Map maintained source areas to the stable on-disk game/runtime ABI.

Saved rules import flat module names and bind resource names by hash. The
repository layout is intentionally independent of that deployment layout.
"""

from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / 'build' / 'runtime'
MANIFEST = '.build-metadata.json'
NATIVE_SUFFIXES = {'.c', '.h', '.S', '.ld'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_map(root=ROOT):
    """Return destination -> source, rejecting links and duplicate destinations."""
    root = Path(root).resolve()
    result = {}

    def add(source, destination):
        if source.is_symlink() or any(
            p.is_symlink() for p in source.parents if p != root and root in p.parents
        ):
            raise ValueError('Linked source: ' + str(source))
        destination = Path(destination).as_posix()
        if destination in result:
            raise ValueError('Duplicate runtime destination: ' + destination)
        result[destination] = source

    for folder, suffixes in [
        ('src/python', {'.py'}),
        ('src/native', NATIVE_SUFFIXES),
        ('src/launchers', {'.sh'}),
        ('tools/native', {'.py'}),
    ]:
        for path in sorted((root / folder).rglob('*')):
            if path.is_symlink():
                raise ValueError('Linked source: ' + str(path))
            if (
                path.is_file()
                and path.suffix in suffixes
                and '__pycache__' not in path.parts
            ):
                add(path, path.name)
    for folder, prefix in [
        ('src/shared', ''),
        ('assets', ''),
        ('tests/runtime', 'tests'),
    ]:
        base = root / folder
        for path in sorted(base.rglob('*')):
            if path.is_symlink():
                raise ValueError('Linked source: ' + str(path))
            if path.is_file() and '__pycache__' not in path.parts:
                relative = path.relative_to(base)
                if folder == 'assets' and relative.parts[0] == 'catalogues':
                    relative = relative.relative_to('catalogues')
                add(path, Path(prefix) / relative)
    if (
        not result
        or 'native_menu_host.py' not in result
        or 'build_runtime.py' not in result
    ):
        raise ValueError('Incomplete source checkout')
    return dict(sorted(result.items()))


def files_in(folder):
    """Bytecode is disposable; every other generated file must be accounted for."""
    folder = Path(folder)
    files = {}
    for path in folder.rglob('*'):
        if path.is_symlink():
            raise ValueError('Linked build path: ' + str(path))
        if path.is_file() and '__pycache__' not in path.parts and path.name != MANIFEST:
            files[path.relative_to(folder).as_posix()] = digest(path)
    return files


def source_hashes(mapping, root=ROOT):
    return {
        name: {'source': path.relative_to(root).as_posix(), 'sha256': digest(path)}
        for name, path in mapping.items()
    }


def read_metadata(target):
    target = Path(target)
    if target.is_symlink() or not (target / MANIFEST).is_file():
        raise ValueError('Not a managed build directory: ' + str(target))
    data = json.loads((target / MANIFEST).read_text(encoding='utf-8'))
    if data.get('version') != 1:
        raise ValueError('Unknown build metadata version')
    return data


def verify_generated(target):
    """Never replace local edits, a game installation, or private run data."""
    target = Path(target)
    metadata = read_metadata(target)
    for name in ('IWBTB', 'native-runs', 'rule-versions', 'wineprefix', 'soundpacks'):
        if (target / name).exists():
            raise ValueError('Private runtime data in build directory: ' + name)
    actual = files_in(target)
    if actual != metadata['outputs']:
        changed = sorted(
            k
            for k in actual.keys() | metadata['outputs'].keys()
            if actual.get(k) != metadata['outputs'].get(k)
        )
        raise ValueError(
            'Generated files changed; preserve edits in src/ first: '
            + ', '.join(changed[:8])
        )
    return metadata


def verify_build(target=RUNTIME, root=ROOT):
    metadata = verify_generated(target)
    if metadata.get('native_built') is not True:
        raise ValueError(
            'Native payloads have not been built. Run python tools/build.py'
        )
    if metadata['sources'] != source_hashes(source_map(root), root):
        raise ValueError('Build is stale. Run python tools/build.py')
    return metadata


def assemble(*, root=ROOT, target=RUNTIME, native_builder=None):
    """Build in a fresh sibling folder and replace only a verified build tree."""
    root, target = Path(root).resolve(), Path(target)
    if target.is_symlink():
        raise ValueError('Linked build directory: ' + str(target))
    target = target.resolve()
    mapping = source_map(root)
    sources = source_hashes(mapping, root)
    if target.exists():
        verify_generated(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.boshy-build-', dir=target.parent))
    previous = None
    try:
        for name, source in mapping.items():
            destination = stage / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        if native_builder is not None:
            native_builder(stage)
        # Catch source edits made while compiling rather than publishing a mix.
        if source_hashes(source_map(root), root) != sources:
            raise ValueError('Source changed during build; retry')
        metadata = dict(
            version=1,
            native_built=native_builder is not None,
            sources=sources,
            outputs=files_in(stage),
        )
        (stage / MANIFEST).write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + '\n', encoding='utf-8'
        )
        if target.exists():
            verify_generated(target)
            previous = Path(
                tempfile.mkdtemp(prefix='.boshy-previous-', dir=target.parent)
            )
            previous.rmdir()
            os.replace(target, previous)
        try:
            os.replace(stage, target)
        except BaseException:
            if previous is not None:
                os.replace(previous, target)
                previous = None
            raise
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        if previous is not None and previous.exists():
            shutil.rmtree(previous)
    return metadata
