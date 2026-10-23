"""Windows entry point and explicit child-process dispatch; no Wine dependency."""

import os
import sys
import json
import hashlib
import shutil
import struct
import runpy
import traceback
from pathlib import Path

COMPONENTS = {'tracker_entry.py', 'debug_window.py', 'loading_screen.py'}


def main():
    import ctypes

    ctypes.windll.user32.SetProcessDPIAware()
    source = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
    payload = source / 'payload' if (source / 'payload').is_dir() else source
    root = Path(
        os.environ.get(
            'BOSHY_DATA_HOME', str(Path(os.environ['LOCALAPPDATA']) / 'BoshyRandomizer')
        )
    ).resolve()
    if not str(root).isascii() or len(str(root)) > 180:
        raise RuntimeError('Choose a short ASCII path using BOSHY_DATA_HOME.')
    root.mkdir(parents=True, exist_ok=True)
    os.environ['BOSHY_DATA_HOME'] = str(root)
    if root.is_symlink() or (root / 'IWBTB').is_symlink():
        raise RuntimeError('Private local game folder required')
    if len(sys.argv) > 2 and sys.argv[1] == '--component':
        name = sys.argv[2]
        if name not in COMPONENTS:
            raise RuntimeError('Unknown component')
        sys.path.insert(0, str(root))
        os.chdir(root)
        sys.argv = [name, *sys.argv[3:]]
        runpy.run_path(str(root / name), run_name='__main__')
        return
    sys.path.insert(0, str(payload))
    from host_platform import lock_file, owned_process, native_path

    lock = (root / '.windows-instance.lock').open('a')
    lock_file(lock)
    import psutil

    if any(owned_process(p, root) for p in psutil.process_iter()):
        raise RuntimeError('Close this randomizer game before updating.')
    manifest = json.loads((payload / 'package-files.json').read_text(encoding='utf-8'))
    for name, want in manifest['files'].items():
        file = payload / name
        if hashlib.sha256(file.read_bytes()).hexdigest() != want:
            raise RuntimeError('Package integrity error: ' + name)
    for name in manifest['files']:
        dest = root / name
        if dest.is_symlink():
            raise RuntimeError('Linked runtime resource rejected')
        dest.parent.mkdir(parents=True, exist_ok=True)
        temp = dest.with_name(dest.name + '.package-new')
        shutil.copyfile(payload / name, temp)
        os.replace(temp, dest)
    sys.path.insert(0, str(root))
    from mixed_rewards import CONTEXT_SIZE

    for blob, symbol in [
        ('slot_reward_hook.bin', 'slot_reward_symbols.json'),
        ('slot_reward_extras.bin', 'slot_reward_extras_symbols.json'),
    ]:
        p = root / blob
        raw = bytearray(p.read_bytes())
        off = (
            json.loads((root / symbol).read_text(encoding='utf-8'))['context_offset']
            + CONTEXT_SIZE
        )
        for field, name in [(64, 'menu-runtime/frame.bmp'), (1356, 'native_menu.dll')]:
            value = native_path(root / name).encode('ascii')
            if len(value) >= 260:
                raise RuntimeError('Runtime path too long')
            raw[off + field : off + field + 260] = value.ljust(260, b'\0')
        p.write_bytes(raw)
    for folder in ('menu-runtime', 'native-runs', 'evidence'):
        (root / folder).mkdir(exist_ok=True)
    (root / 'installed-runtime.json').write_text(
        json.dumps({'version': manifest['version'], 'release': manifest['release']}),
        encoding='utf-8',
    )
    os.environ['BOSHY_DATA_HOME'] = str(root)
    os.chdir(root)
    from first_run import Setup

    if not (root / 'IWBTB').exists() and not Setup(root).run():
        return
    from native_menu_host import run

    run()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        text = traceback.format_exc()
        root = Path(
            os.environ.get(
                'BOSHY_DATA_HOME',
                str(Path(os.environ.get('LOCALAPPDATA', '.')) / 'BoshyRandomizer'),
            )
        )
        root.mkdir(parents=True, exist_ok=True)
        (root / 'windows-error.log').write_text(text, encoding='utf-8')
        import tkinter as tk
        from tkinter import messagebox

        app = tk.Tk()
        app.withdraw()
        messagebox.showerror('Boshy Randomizer', text[-1800:])
        app.destroy()
        raise
