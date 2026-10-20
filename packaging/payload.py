"""Shared public runtime selection for Linux and Windows packages.

Only maintained PY helpers and public INI catalogues belong in an installer.
A developer's local settings or retired GUI modules must never be swept in.
"""
from pathlib import Path

PY_MODULES = (
    '__init__', 'config', 'file_utils', 'ini_utils', 'live_tracker', 'logger',
    'pixel_detector', 'platform_runtime', 'platform_windows', 'rc4_utils',
    'save_utils',
)
INI_CATALOGUES = ('characters.json', 'characters_rando.json', 'positions.json')
ROOT_EXCLUDE = {
    'source-manifest.json', 'package-files.json', 'installed-runtime.json',
    'slot_reward_context.bin', 'elf_to_coff.py',
}
WINDOWS_EXCLUDE = {
    'package_bootstrap.py', 'wine_setup.py', 'wine-runner-manifest.json',
}
ASSET_FOLDERS = {
    'locales': {'.json'},
    'Custom': {'.png', '.bmp', '.ttf', '.wav', '.txt'},
    'menu-character-icons': {'.png'},
    'native-icons': {'.bmp'},
    'loading-icons': {'.png', '.webp', '.json'},
}


def runtime_files(source, *, platform, audit_files=()):
    """Return deterministic, validated paths without importing the game runtime."""
    if platform not in ('linux', 'windows'):
        raise ValueError('Unknown package platform: ' + platform)
    source = Path(source).resolve()
    excluded = ROOT_EXCLUDE | (WINDOWS_EXCLUDE if platform == 'windows' else set())
    extensions = {'.py', '.dll', '.exe', '.bin', '.json'}
    if platform == 'linux':
        extensions.add('.sh')
    files = {
        p for p in source.iterdir()
        if p.is_file() and not p.is_symlink() and p.suffix in extensions
        and not p.name.startswith('build_') and p.name not in excluded
    }
    required = [source / 'PY' / (name + '.py') for name in PY_MODULES]
    required += [source / 'INI' / name for name in INI_CATALOGUES]
    required += [source / name for name in audit_files]
    for path in required:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(source):
            raise ValueError('Missing or linked runtime resource: ' + str(path))
    files.update(required)
    for folder, allowed in ASSET_FOLDERS.items():
        files.update(
            p for p in (source / folder).rglob('*')
            if p.is_file() and not p.is_symlink() and p.suffix in allowed
            and '__pycache__' not in p.parts
        )
    for path in files:
        if any(parent.is_symlink() for parent in path.parents if parent != source and source in parent.parents):
            raise ValueError('Linked runtime directory: ' + str(path))
    return sorted(files)
