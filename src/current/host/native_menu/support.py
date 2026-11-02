"""Bounded diagnostic error metadata; no exception text, paths or file dumps."""

import errno
import re
import time
import traceback
from pathlib import Path


def describe_error(operation, error):
    token = lambda value: (
        value
        if isinstance(value, str) and re.fullmatch(r"[a-zA-Z0-9_.-]{1,80}", value)
        else "unknown"
    )
    row = dict(
        time=time.time(),
        operation=token(operation),
        error_type=token(type(error).__name__),
    )
    code, winerror = getattr(error, "errno", None), getattr(error, "winerror", None)
    if isinstance(code, int):
        row["errno"] = code
    if isinstance(winerror, int):
        row["winerror"] = winerror
    if code == errno.ENOSPC or winerror == 112:
        row["reason"] = "disk_full"
    elif isinstance(error, PermissionError):
        row["reason"] = "access_denied"
    elif isinstance(error, FileNotFoundError):
        row["reason"] = "file_missing"
    elif isinstance(error, TimeoutError):
        row["reason"] = "timeout"
    elif isinstance(error, ValueError):
        row["reason"] = "validation_failed"
    else:
        row["reason"] = "operation_failed"
    row["locations"] = [
        dict(module=token(Path(f.filename).name), function=token(f.name), line=f.lineno)
        for f in traceback.extract_tb(error.__traceback__)[-8:]
    ]
    return row
