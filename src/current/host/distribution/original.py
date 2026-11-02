"""Import a supported original from a directory or ZIP into a private staging area.

Never execute the source, follow links, overwrite it, or extract arbitrary ZIP
paths. Only the original EXE and known game data are copied; old saves, wrappers
and unrelated executables do not enter the new installation.
"""

import os
import re
import shutil
import stat
import zipfile
from pathlib import Path, PurePosixPath
from distribution.identity import sha256
from distribution.progress import ignore
from distribution.import_errors import OriginalImportError

ORIGINAL_NAME = "I Wanna Be The Boshy.exe"
ORIGINAL_SHA = "dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806"
MAX_FILES = 20000
MAX_TOTAL = 2_000_000_000
MAX_FILE = 500_000_000
DATA_SUFFIXES = {
    ".ogg",
    ".mp3",
    ".wav",
    ".mid",
    ".midi",
    ".mod",
    ".xm",
    ".it",
    ".s3m",
    ".png",
    ".bmp",
    ".jpg",
    ".jpeg",
    ".gif",
    ".dat",
    ".txt",
}
RESERVED = {
    "con",
    "prn",
    "aux",
    "nul",
    *(f"com{i}" for i in range(1, 10)),
    *(f"lpt{i}" for i in range(1, 10)),
}


def relative_name(name):
    """Apply Windows path rules even when building/importing on Linux."""
    if not name or "\\" in name or "\0" in name or name.startswith("/"):
        raise OriginalImportError("unsafe_path", "Unsafe archive path")
    path = PurePosixPath(name.rstrip("/"))
    if not path.parts or any(
        part in {".", ".."}
        or part.endswith((".", " "))
        or re.search(r'[<>:"|?*\x00-\x1f]', part)
        or part.split(".")[0].lower() in RESERVED
        for part in path.parts
    ):
        raise OriginalImportError("unsafe_path", "Unsafe archive path")
    return path


def wanted(path):
    return (
        path.name.casefold() == ORIGINAL_NAME.casefold()
        or path.suffix.lower() in DATA_SUFFIXES
    )


def import_original(source, destination, *, expected=ORIGINAL_SHA, progress=ignore):
    """Return the copied EXE, only after all source/path/size/hash checks pass.

    Destination must be absent. A failed import removes only its own staging
    directory. Multiple original EXEs are ambiguous and rejected.
    """
    progress("importing")
    source, destination = Path(source), Path(destination)
    if source.is_symlink() or destination.exists() or destination.is_symlink():
        raise ValueError("Import requires a real source and a new destination")
    source = source.resolve(strict=True)
    if source.is_dir() and (
        destination.resolve() == source or source in destination.resolve().parents
    ):
        raise ValueError("Destination must be outside the original game folder")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.mkdir()
    try:
        if source.is_dir():
            _directory(source, destination, progress)
        elif zipfile.is_zipfile(source):
            _archive(source, destination, progress)
        else:
            raise OriginalImportError(
                "source_type", "Choose a Boshy folder or ZIP archive"
            )
        result = destination / ORIGINAL_NAME
        if sha256(result) != expected:
            raise OriginalImportError(
                "unsupported_game", "Unsupported or damaged original Boshy executable"
            )
        return result
    except BaseException:
        shutil.rmtree(destination)
        raise


def _check_limits(count, total, largest, source):
    for actual, limit, code in (
        (count, MAX_FILES, "file_count"),
        (total, MAX_TOTAL, "total_size"),
        (largest, MAX_FILE, "file_size"),
    ):
        if actual > limit:
            raise OriginalImportError(code, source + " exceeds import limits: " + code)


def _directory(source, destination, progress):
    rows = []
    size = 0
    for base, dirs, files in os.walk(source, followlinks=False):
        for name in dirs + files:
            p = Path(base) / name
            if p.is_symlink() or getattr(p, "is_junction", lambda: False)():
                raise OriginalImportError(
                    "links", "Links are not allowed in the original folder"
                )
        for name in files:
            p = Path(base) / name
            if not p.is_file():
                raise ValueError("Special files are not allowed")
            rel = relative_name(p.relative_to(source).as_posix())
            size += p.stat().st_size
            rows.append((rel, p))
            _check_limits(len(rows), size, p.stat().st_size, "Original folder")
    _copy_rows(
        rows, destination, lambda p, target: shutil.copyfile(p, target), progress
    )


def _archive(source, destination, progress):
    with zipfile.ZipFile(source) as archive:
        rows, size = [], 0
        for item in archive.infolist():
            # ZipInfo normalizes backslashes on Windows. Validate the original
            # central-directory spelling before any platform normalization.
            rel = relative_name(item.orig_filename)
            mode = item.external_attr >> 16
            if stat.S_ISLNK(mode) or (
                stat.S_IFMT(mode) and not (stat.S_ISREG(mode) or stat.S_ISDIR(mode))
            ):
                raise OriginalImportError(
                    "links", "Archive contains a link or special file"
                )
            if item.flag_bits & 1:
                raise ValueError("Encrypted archives are not supported")
            if item.is_dir():
                continue
            size += item.file_size
            rows.append((rel, item))
            _check_limits(len(rows), size, item.file_size, "Archive")

        def extract(item, target):
            with archive.open(item) as src, target.open("xb") as dst:
                copied = 0
                while block := src.read(1024 * 1024):
                    copied += len(block)
                    if copied > item.file_size:
                        raise ValueError("Archive member size mismatch")
                    dst.write(block)
                if copied != item.file_size:
                    raise ValueError("Truncated archive member")

        _copy_rows(rows, destination, extract, progress)


def _copy_rows(rows, destination, copier, progress):
    candidates = [
        rel for rel, _ in rows if rel.name.casefold() == ORIGINAL_NAME.casefold()
    ]
    if len(candidates) != 1:
        raise OriginalImportError(
            "missing_game" if not candidates else "multiple_games",
            "Select a folder or ZIP containing exactly one original Boshy game",
        )
    root = candidates[0].parent
    seen = set()
    selected = []
    for rel, item in rows:
        key = str(rel).casefold()
        if key in seen:
            raise OriginalImportError(
                "duplicate_path", "Duplicate or case-colliding source path"
            )
        seen.add(key)
        if not rel.is_relative_to(root):
            continue
        local = rel.relative_to(root)
        if not wanted(local):
            continue
        if local.name.casefold() == ORIGINAL_NAME.casefold():
            local = PurePosixPath(ORIGINAL_NAME)
        selected.append((local, item))
    progress("importing", 0, len(selected))
    for index, (local, item) in enumerate(selected, 1):
        target = destination.joinpath(*local.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        copier(item, target)
        progress("importing", index, len(selected))
