"""Small, portable build identities; no developer paths in public reports."""

import hashlib
import json
from pathlib import Path

PRODUCT = "Boshy Randomizer"
VERSION = "1.0.2"


def sha256(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def source_manifest(root):
    """Hash maintained code/data, excluding generated outputs and vendor trees."""
    root = Path(root)
    ignored = {
        "__pycache__",
        ".git",
        ".ruff_cache",
        "KlikBack",
        "reference-nebula",
        "reference-clickteam-sdk",
        "help-extracted",
    }
    modules = {
        "distribution",
        "platform_support",
        "quality",
        "gameplay",
        "menu_host",
        "music",
        "native_menu",
        "recovery",
        "tracker",
        "transition",
        "visuals",
    }
    return {
        str(p.relative_to(root)): sha256(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
        and not p.is_symlink()
        and (
            len(p.relative_to(root).parts) == 1
            or p.relative_to(root).parts[0] in modules
        )
        and not ignored.intersection(p.relative_to(root).parts)
        and p.suffix in {".py", ".c", ".json", ".iss", ".csx"}
        and not p.name.startswith("route-build")
    }


def source_digest(root):
    return hashlib.sha256(
        json.dumps(
            source_manifest(root), sort_keys=True, separators=(",", ":")
        ).encode()
    ).hexdigest()


def describe(executable, expected):
    actual = sha256(executable)
    if actual != expected:
        raise ValueError("Game executable does not match the selected build")
    return {"product": PRODUCT, "version": VERSION, "game_sha256": actual}


def verify_receipt(receipt, source, project, executable):
    """Reject stale source/project/output selections before package generation.

    A receipt is created only after the compiled-structure and runtime gates pass.
    It does not replace those tests or claim binary reproducibility.
    """
    if receipt.get("schema") != 1 or receipt.get("status") != "verified":
        raise ValueError("Build has not passed verification")
    expected = {
        "source_sha256": source_digest(source),
        "project_sha256": sha256(project),
        "game_sha256": sha256(executable),
    }
    if any(receipt.get(k) != v for k, v in expected.items()):
        raise ValueError("Source, project or executable changed after verification")
    return expected
