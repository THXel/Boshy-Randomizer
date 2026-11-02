"""Exercise ZIP import and the real patch in a new private installation directory."""

import json
import zipfile
from pathlib import Path
from distribution.game_patch import apply
from distribution.identity import sha256
from distribution.original import ORIGINAL_NAME
from distribution.transaction import install, installation_lock, active
from export_native_run import ORIGINAL


def run(output):
    output = Path(output).resolve()
    specification = json.loads((output / "patch-build.json").read_text())
    patch = output / "BoshyRandomizer-v39.bpatch"
    source = output / "original-input.zip"
    if not source.exists():
        with zipfile.ZipFile(source, "w", zipfile.ZIP_STORED) as archive:
            archive.write(ORIGINAL, "Boshy/" + ORIGINAL_NAME)
    root = output / "imported-installation"
    with installation_lock(root):
        result = install(
            source,
            root,
            "2026.10.26-preview.39",
            specification["target_sha256"],
            lambda original, target: apply(
                original,
                patch,
                target,
                expected_patch=specification["patch_sha256"],
                expected_target=specification["target_sha256"],
            ),
        )
    report = {
        "source_kind": "nested ZIP",
        "original_unchanged": sha256(ORIGINAL) == specification["source_sha256"],
        "patched_game_sha256": sha256(result / "game" / ORIGINAL_NAME),
        "retained_original_sha256": sha256(result / "resources/original.bin"),
        "active_version": active(root)["version"],
        "passed": True,
        "scope": "real private import and patch reconstruction; no installed desktop shortcut or OS package",
    }
    (output / "installation-roundtrip.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    source.unlink()  # Private temporary ZIP fixture, not the user's original.
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    import sys

    run(Path(sys.argv[1]))
