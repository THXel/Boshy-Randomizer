"""Recycle completed working copies; retain saves, journals and unknown data."""

import json
import math
import os
import re
import stat
import time
from pathlib import Path
from menu_host.store import atomic
from platform_support.recycle import recycle

MARKER = "working-copy.json"
KEEP = 3
NAME = re.compile(r"rebuilt-menu-[0-9a-f]{32}")


def linked(path):
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(
        getattr(info, "st_file_attributes", 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT
    )


def metadata(folder):
    path = Path(folder) / MARKER
    if linked(path) or path.stat().st_size > 4096:
        raise ValueError("Invalid working-copy marker")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("schema") != 1:
        raise ValueError("Unknown working-copy marker")
    return value


def started(folder, profile):
    folder = Path(folder)
    if not NAME.fullmatch(folder.name) or linked(folder):
        raise ValueError("Working-copy boundary")
    atomic(
        folder / MARKER,
        json.dumps(
            dict(
                schema=1,
                profile=str(Path(profile).resolve()),
                state="open",
                created=time.time(),
            )
        ).encode(),
    )


def finished(folder, profile):
    data = metadata(folder)
    if data.get("profile") != str(Path(profile).resolve()):
        raise ValueError("Working-copy profile changed")
    data.update(state="closed", closed=time.time())
    atomic(Path(folder) / MARKER, json.dumps(data).encode())


def tree_is_plain(folder):
    for base, dirs, files in os.walk(folder, followlinks=False):
        for name in dirs + files:
            if linked(Path(base) / name):
                return False
    return True


def collect(store, *, keep=KEEP, active_games=None):
    """Caller holds the Store lock; uncertainty leaves files untouched."""
    result = dict(recycled=0, retained=0, skipped=0)
    try:
        store.writable()
        if not store.lockfile:
            raise RuntimeError("Cleanup requires the run-store lock")
        if type(keep) is not int or keep < 1:
            raise ValueError("Keep at least one completed working copy")
        runs = store.runs.resolve()
        profile = str(store.root.resolve())
        protected = {
            store.folder(slot).resolve() for slot in (1, 2, 3) if store.current(slot)
        }
        journal = store.root / "native-session.json"
        if journal.exists() or journal.is_symlink():
            if linked(journal) or journal.stat().st_size > 16384:
                raise ValueError("Uncertain recovery journal")
            data = json.loads(journal.read_text(encoding="utf-8"))
            name = data.get("working", "")
            if not NAME.fullmatch(name):
                raise ValueError("Uncertain recovery journal")
            protected.add(runs / name)
        if active_games is None:
            from menu_host.processes import games

            active_games = lambda: games(runs)
        protected.update(Path(p).resolve() for p in active_games().values())
        candidates = []
        for folder in runs.iterdir():
            if not NAME.fullmatch(folder.name) or folder in protected:
                continue
            try:
                if (
                    linked(folder)
                    or not folder.is_dir()
                    or (folder / "plan.json").exists()
                ):
                    continue
                data = metadata(folder)
                closed = data.get("closed")
                if (
                    data.get("profile") != profile
                    or data.get("state") != "closed"
                    or not isinstance(closed, (int, float))
                    or not math.isfinite(closed)
                ):
                    continue
                candidates.append((closed, folder))
            except (OSError, ValueError, TypeError):
                result["skipped"] += 1
        candidates.sort(key=lambda row: (row[0], row[1].name), reverse=True)
        result["retained"] = min(keep, len(candidates))
        for _, folder in candidates[keep:]:
            try:
                if folder in active_games().values() or not tree_is_plain(folder):
                    result["skipped"] += 1
                    continue
                recycle(folder)
                result["recycled"] += 1
            except (OSError, RuntimeError):
                result["skipped"] += 1
    except (OSError, ValueError, RuntimeError, TypeError, KeyError):
        result["blocked"] = True
    return result
