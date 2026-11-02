"""Versioned installation with atomic activation and explicit rollback.

An interrupted import/patch cannot replace the active version. Installed code
and user saves live in separate directories. Old versions remain available
until explicitly removed by the package manager/uninstaller.
"""

import json
import os
import re
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from distribution.identity import sha256
from distribution.progress import ignore
from platform_support.storage import lock_file, replace
from distribution.original import import_original, ORIGINAL_NAME, ORIGINAL_SHA


def atomic_json(path, data):
    path = Path(path)
    fd, tmp = tempfile.mkstemp(prefix=".activation-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, sort_keys=True, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        replace(tmp, path)
    finally:
        Path(tmp).unlink(missing_ok=True)


def valid_version(version):
    if not isinstance(version, str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", version
    ):
        raise ValueError("Invalid installation version")
    return version


@contextmanager
def installation_lock(root):
    """Serialize install, activation and rollback on both supported platforms."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = root / ".installation.lock"
    if root.is_symlink() or path.is_symlink():
        raise ValueError("Linked installation directory or lock")
    with lock_file(path):
        yield


def active(root):
    root = Path(root)
    pointer = root / "active.json"
    if not pointer.exists():
        return None
    data = json.loads(pointer.read_text(encoding="utf-8"))
    valid_version(data["version"])
    executable = root / "versions" / data["version"] / "game" / ORIGINAL_NAME
    if sha256(executable) != data["game_sha256"]:
        raise ValueError("Active installation is damaged")
    return data


def install(
    source,
    root,
    version,
    expected_target,
    patcher,
    *,
    expected_source=ORIGINAL_SHA,
    payload=None,
    activate_now=True,
    progress=ignore
):
    """Patcher accepts (original_exe, output_exe); it must not launch code.

    A package frontend must hold installation_lock while calling this API.
    The patcher and expected hashes come from the trusted package, never the ZIP.
    """
    version = valid_version(version)
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    active(root)  # Reject an already damaged active installation.
    versions = root / "versions"
    versions.mkdir(exist_ok=True)
    target = versions / version
    if target.exists():
        raise FileExistsError("Version already installed")
    with tempfile.TemporaryDirectory(prefix=".install-", dir=root) as tmp:
        stage = Path(tmp)
        original = import_original(
            source, stage / "game", expected=expected_source, progress=progress
        )
        # The asset preparer reads original artwork from this private resource.
        # It is never launched or exposed as a second game shortcut.
        (stage / "resources").mkdir()
        shutil.copyfile(original, stage / "resources/original.bin")
        patched = stage / "patched.exe"
        progress("patching")
        patcher(original, patched)
        if sha256(patched) != expected_target:
            raise ValueError(
                "Patched game checksum mismatch; current version preserved"
            )
        os.replace(patched, original)
        if payload is not None:
            from distribution.package_files import install_payload

            install_payload(payload, stage, progress)
        receipt = {
            "schema": 1,
            "version": version,
            "game_sha256": expected_target,
            "source_sha256": expected_source,
        }
        files = [p for p in sorted(stage.rglob("*")) if p.is_file()]
        receipt["files"] = {}
        progress("verifying", 0, len(files))
        for index, path in enumerate(files, 1):
            receipt["files"][path.relative_to(stage).as_posix()] = sha256(path)
            progress("verifying", index, len(files))
        atomic_json(stage / "installation.json", receipt)
        # Commit the immutable version before changing the small active pointer.
        progress("committing")
        os.replace(stage, target)
    if activate_now:
        try:
            activate(root, version, progress)
        except BaseException:
            shutil.rmtree(target)
            raise
    return target


def verified_version(root, version, progress=ignore):
    """Check the complete version, including its own host and runtime."""
    from distribution.original import relative_name

    folder = Path(root) / "versions" / valid_version(version)
    if folder.is_symlink():
        raise ValueError("Linked installation version")
    receipt = json.loads((folder / "installation.json").read_text(encoding="utf-8"))
    if receipt.get("schema") != 1 or receipt.get("version") != version:
        raise ValueError("Invalid installation receipt")
    progress("verifying", 0, len(receipt["files"]))
    for index, (name, expected) in enumerate(receipt["files"].items(), 1):
        path = folder.joinpath(*relative_name(name).parts)
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError("Linked installed file")
        if sha256(path) != expected:
            raise ValueError("Installed file is damaged: " + name)
        progress("verifying", index, len(receipt["files"]))
    return receipt


def activate(root, version, progress=ignore):
    root = Path(root)
    receipt = verified_version(root, version, progress)
    progress("activating")
    previous = active(root)
    if previous and previous["version"] == version:
        return previous
    # Keep a small pointer; file ownership lives only in installation.json.
    pointer = {
        k: receipt[k] for k in ("schema", "version", "game_sha256", "source_sha256")
    }
    pointer["previous"] = previous
    atomic_json(root / "active.json", pointer)
    return pointer


def rollback(root):
    root = Path(root)
    current = active(root)
    previous = current.get("previous") if current else None
    if not previous:
        raise ValueError("No previous version available")
    version = valid_version(previous["version"])
    verified_version(root, version)
    path = root / "versions" / version / "game" / ORIGINAL_NAME
    if sha256(path) != previous["game_sha256"]:
        raise ValueError("Previous installation is damaged")
    atomic_json(root / "active.json", previous)
    return path


def uninstall(root, progress=ignore):
    """Remove only owned, unmodified installed files; never remove user saves."""
    progress("removing")
    root = Path(root)
    preserved = []
    versions = root / "versions"
    if not versions.is_dir() or versions.is_symlink():
        raise ValueError("No owned installation found")
    for folder in sorted(versions.iterdir()):
        if folder.is_symlink() or not folder.is_dir():
            preserved.append(folder.name)
            continue
        receipt = folder / "installation.json"
        if not receipt.is_file() or receipt.is_symlink():
            preserved.append(folder.name)
            continue
        data = json.loads(receipt.read_text(encoding="utf-8"))
        if data.get("schema") != 1 or data.get("version") != folder.name:
            raise ValueError("Uninstall ownership check failed")
        from distribution.original import relative_name

        progress("removing", 0, len(data["files"]))
        for index, (name, expected) in enumerate(data["files"].items(), 1):
            rel = relative_name(name)
            path = folder.joinpath(*rel.parts)
            if path.is_symlink() or any(
                p.is_symlink() for p in path.parents if p != root.parent
            ):
                raise ValueError("Linked installed file")
            if not path.exists():
                progress("removing", index, len(data["files"]))
                continue
            if sha256(path) == expected:
                path.unlink()
            else:
                preserved.append(folder.name + "/" + name)
            progress("removing", index, len(data["files"]))
        receipt.unlink()
        for directory in sorted(
            folder.rglob("*"), key=lambda p: len(p.parts), reverse=True
        ):
            if directory.is_dir() and not directory.is_symlink():
                try:
                    directory.rmdir()
                except OSError:
                    pass  # Untracked or modified files belong to the user.
        try:
            folder.rmdir()
        except OSError:
            preserved.append(folder.name)
    (root / "active.json").unlink(missing_ok=True)
    return sorted(set(preserved))
