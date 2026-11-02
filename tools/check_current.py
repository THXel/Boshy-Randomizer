#!/usr/bin/env python3
"""Verify the current host source and its game-free regression subset."""

from pathlib import Path
import compileall, hashlib, json, os, shutil, subprocess, sys, tempfile

root = Path(__file__).resolve().parents[1]
source = root / 'src/current'
host = source / 'host'
manifest = json.loads((source / 'source.json').read_text())
for name, expected in manifest['files'].items():
    p = source / name
    if (
        not p.is_file()
        or p.is_symlink()
        or hashlib.sha256(p.read_bytes()).hexdigest() != expected
    ):
        raise ValueError('Source mismatch: ' + name)
if not compileall.compile_dir(host, quiet=1):
    raise SystemExit('Host syntax check failed')
with tempfile.TemporaryDirectory(prefix='boshy-current-tests-') as tmp:
    work = Path(tmp)
    shared = work / 'shared'
    shutil.copytree(root / 'assets', shared / 'assets')
    shutil.copytree(source / 'shared', shared, dirs_exist_ok=True)
    cfg = work / 'runtime.json'
    cfg.write_text(
        json.dumps(
            dict(
                schema=1,
                prefix=str(work / 'prefix'),
                original=str(work / 'original.exe'),
                soundpacks=str(work / 'soundpacks'),
                game=str(work / 'game.exe'),
                wine=str(work / 'wine'),
                repository=str(shared),
            )
        )
    )
    env = {
        **os.environ,
        'BOSHY_RUNTIME_CONFIG': str(cfg),
        'PYTHONDONTWRITEBYTECODE': '1',
    }
    tests = [
        'test_diagnostics',
        'test_menu_preferences',
        'test_display_preferences',
        'test_menu_organization',
        'test_parity_defaults.ParityDefaultsTests.test_first_use_spider_and_saved_opt_out_and_import',
        'test_debug_actions.DebugActionTests.test_recording_is_bounded_and_labels_are_complete',
    ]
    import ast

    tree = ast.parse((host / 'test_tracker_web.py').read_text())
    for cls in tree.body:
        if isinstance(cls, ast.ClassDef) and cls.name == 'WebTrackerTests':
            tests += [
                'test_tracker_web.WebTrackerTests.' + m.name
                for m in cls.body
                if isinstance(m, ast.FunctionDef)
                and m.name.startswith('test_')
                and m.name != 'test_all_native_rewards_and_routes_have_real_icons'
            ]
    subprocess.run(
        [sys.executable, '-B', '-m', 'unittest', *tests, '-v'],
        cwd=host,
        env=env,
        check=True,
    )
print(
    'Current host checks passed; original-game and VM tests are separate release gates.'
)
