"""Recycle only: no permanent-delete fallback on either supported platform."""

import os
import subprocess
from pathlib import Path


def recycle(path):
    path = Path(path).absolute()
    if os.name != "nt":
        try:
            subprocess.run(
                ["gio", "trash", "--", str(path)],
                check=True,
                timeout=30,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except subprocess.SubprocessError as error:
            raise OSError("Could not move working copy to Trash") from error
        return
    from platform_support.wine_trash import is_wine, recycle as wine_recycle

    if is_wine():
        return wine_recycle(path)
    from platform_support.recycle_windows import recycle as windows_recycle

    windows_recycle(path)
