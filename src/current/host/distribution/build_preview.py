"""Stage a private test package without the original or full modified game.

This command deliberately produces a preview only. It neither publishes files
nor marks the release gates passed. Runtime inputs must be verified separately.
"""

import argparse
import json
import shutil
from pathlib import Path
from distribution.identity import VERSION, sha256
from distribution.payload import stage
from distribution.original import ORIGINAL_SHA
from distribution.runtime_files import validate_runtime


def build(lab, shared, runtime, soundpacks, patch, target_sha, output):
    validate_runtime(runtime)
    output = stage(lab, shared, output)
    shutil.copytree(runtime, output / "runtime", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copytree(soundpacks, output / "resources/soundpacks", ignore=shutil.ignore_patterns("__pycache__", ".*"))
    shutil.copyfile(patch, output / "game.bpatch")
    spec = {
        "schema": 1, "status": "private-preview", "version": VERSION,
        "source_sha256": ORIGINAL_SHA, "game_sha256": target_sha,
        "patch_sha256": sha256(output / "game.bpatch"),
        "files": {p.relative_to(output).as_posix(): sha256(p)
                  for p in sorted(output.rglob("*")) if p.is_file() and p.name != "game.bpatch"},
    }
    if (output / "resources/original.bin").exists() or (output / "game").exists():
        raise ValueError("A distributable package must not contain a full Boshy game")
    (output / "package.json").write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
    return spec


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ("lab", "shared", "runtime", "soundpacks", "patch", "output"):
        parser.add_argument("--" + key, type=Path, required=True)
    parser.add_argument("--target-sha", required=True)
    args = parser.parse_args()
    spec = build(**vars(args))
    print(json.dumps({k: v for k, v in spec.items() if k != "files"}, indent=2))


if __name__ == "__main__":
    main()
