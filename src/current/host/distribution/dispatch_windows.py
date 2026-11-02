"""Stable launcher: select one verified installation and keep it locked in use."""

import subprocess
import sys
from pathlib import Path
from distribution.transaction import active, installation_lock


def main():
    root = Path(__file__).resolve().parents[3]
    try:
        with installation_lock(root):
            selected = active(root)
            if selected is None:
                raise RuntimeError("No active Boshy Randomizer installation. Please run Setup.")
            version = root / "versions" / selected["version"]
            return subprocess.call([
                str(version / "runtime/pythonw.exe"), "-B", "-X", "utf8",
                str(version / "app/distribution/windows_entry.py"), "--persistent",
            ], cwd=version)
    except Exception as error:
        from ctypes import windll
        windll.user32.MessageBoxW(None, str(error), "Boshy Randomizer", 0x10)
        return 1


if __name__ == "__main__":
    sys.exit(main())
