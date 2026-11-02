"""Recoverable home-trash rename used by the Windows host running in Wine.

Follows the freedesktop Trash specification. No cross-filesystem copy/delete
fallback: an unavailable destination leaves the working copy in place.
"""

import os
import stat
import time
import uuid
from pathlib import Path
from urllib.parse import quote_from_bytes


def plain_directory(path):
    if path.exists() or path.is_symlink():
        info = path.lstat()
        if (
            stat.S_ISLNK(info.st_mode)
            or getattr(info, "st_file_attributes", 0)
            & stat.FILE_ATTRIBUTE_REPARSE_POINT
        ):
            raise OSError("Linked trash directory is not supported")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.is_dir():
        raise OSError("Trash destination is not a directory")


def move_to_home_trash(source, trash, unix_source):
    source, trash = Path(source), Path(trash)
    if (
        not isinstance(unix_source, bytes)
        or not unix_source.startswith(b"/")
        or b"\0" in unix_source
    ):
        raise ValueError("An absolute Unix source path is required")
    for directory in (trash, trash / "files", trash / "info"):
        plain_directory(directory)
    name = "boshy-" + uuid.uuid4().hex
    target = trash / "files" / name
    info = trash / "info" / (name + ".trashinfo")
    if target.exists() or target.is_symlink():
        raise FileExistsError(target)
    content = "[Trash Info]\nPath=" + quote_from_bytes(unix_source, safe="/")
    content += "\nDeletionDate=" + time.strftime("%Y-%m-%dT%H:%M:%S") + "\n"
    # Exclusive metadata reservation precedes the move, as required by the spec.
    with info.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        # Windows/Wine rename refuses replacement and cross-device copying.
        os.rename(source, target)
    except OSError:
        # Remove only our unused reservation, never game data.
        if source.exists() and not target.exists():
            info.unlink(missing_ok=True)
        raise
    return target, info
