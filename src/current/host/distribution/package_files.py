"""Exact, hash-checked application payload shared by both package frontends."""

import json
import shutil
from pathlib import Path
from distribution.identity import sha256
from distribution.progress import ignore
from distribution.original import relative_name

ROOTS = {"app", "runtime", "shared", "licenses", "resources"}


def specification(payload):
    return json.loads((Path(payload) / "package.json").read_text(encoding="utf-8"))


def checked_files(payload, progress=ignore):
    payload = Path(payload)
    spec = specification(payload)
    if spec.get("schema") != 1 or not spec.get("files"):
        raise ValueError("Invalid application package")
    progress("checking", 0, len(spec["files"]))
    seen = set()
    for name, expected in spec["files"].items():
        key = name.casefold()
        if key in seen:
            raise ValueError("Case-colliding application package paths")
        seen.add(key)
        rel = relative_name(name)
        if rel.parts[0] not in ROOTS or name == "resources/original.bin":
            raise ValueError("Unexpected package file: " + name)
        if rel.parts[0] == "resources" and rel.parts[1:2] != ("soundpacks",):
            raise ValueError("Unexpected game resource")
        path = payload.joinpath(*rel.parts)
        if path.is_symlink() or any(p.is_symlink() for p in path.parents):
            raise ValueError("Linked package file")
        if sha256(path) != expected:
            raise ValueError("Damaged application package: " + name)
        progress("checking", len(seen), len(spec["files"]))
        yield rel, path


def install_payload(payload, destination, progress=ignore):
    destination = Path(destination)
    files = list(checked_files(payload, progress))
    progress("copying", 0, len(files))
    for index, (rel, source) in enumerate(files, 1):
        target = destination.joinpath(*rel.parts)
        if target.exists():
            raise ValueError("Package file overlaps imported game: " + str(rel))
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        progress("copying", index, len(files))
