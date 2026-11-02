"""Measure a local Git binary delta without saving or publishing game payloads.

A literal forward block contains the complete target, even though it is called
an application patch. This tool reports that case explicitly. Other patch
algorithms may differ; this is not a general or legal distribution verdict.
"""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path


def audit(source, target):
    source, target = Path(source), Path(target)
    process = subprocess.Popen(
        [
            "git",
            "-c",
            "core.bigFileThreshold=512m",
            "diff",
            "--no-index",
            "--binary",
            "--",
            str(source),
            str(target),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    blocks = []
    for line in process.stdout:
        if line.startswith((b"literal ", b"delta ")):
            kind, size = line.decode().split()
            blocks.append(dict(type=kind, decoded_bytes=int(size), encoded_bytes=0))
        elif blocks and line.strip():
            blocks[-1]["encoded_bytes"] += len(line)
    error = process.stderr.read().decode()
    code = process.wait()
    if code != 1 or len(blocks) != 2:
        raise ValueError(f"Expected binary difference: {code}, {error}")

    def identity(path):
        return dict(
            sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            size=path.stat().st_size,
        )

    return dict(
        scope="Local Git binary delta audit; no release patch generated",
        source=identity(source),
        target=identity(target),
        forward=blocks[0],
        reverse=blocks[1],
        complete_target_in_forward_patch=blocks[0]["type"] == "literal",
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = audit(args.source, args.target)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
