"""Explicit, account-local removal; ordinary uninstall always preserves data."""

import os
import shutil
import stat
from pathlib import Path


def checked_user_data():
    location = os.environ.get("LOCALAPPDATA")
    if not location or not Path(location).is_absolute():
        raise ValueError("LOCALAPPDATA is not an absolute path")
    root = Path(location) / "BoshyRandomizer"
    # Do not follow links/junctions into other accounts, prefixes or applications.
    for path in (root, *root.parents):
        if path.exists() or path.is_symlink():
            info = path.lstat()
            if (
                stat.S_ISLNK(info.st_mode)
                or getattr(info, "st_file_attributes", 0) & 0x400
            ):
                raise ValueError("Linked user-data paths cannot be removed")
    if root.exists():
        if not root.is_dir():
            raise ValueError("User-data path is not a directory")
        for directory, dirs, files in os.walk(root, followlinks=False):
            for name in dirs + files:
                path = Path(directory) / name
                info = path.lstat()
                if (
                    stat.S_ISLNK(info.st_mode)
                    or getattr(info, "st_file_attributes", 0) & 0x400
                ):
                    raise ValueError("Linked user-data paths cannot be removed")
    return root


def remove_user_data():
    root = checked_user_data()
    if root.exists():
        shutil.rmtree(root)
    return str(root)
