#!/usr/bin/env python3
"""Assemble the stable runtime and rebuild its portable native payloads."""

import argparse
import subprocess
import sys
from layout import RUNTIME, assemble


def compile_native(stage):
    subprocess.run(
        [sys.executable, str(stage / 'build_runtime.py')], cwd=stage, check=True
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--assemble-only',
        action='store_true',
        help='Prepare Python/resources/tests without native compilation (Windows checks).',
    )
    args = parser.parse_args()
    metadata = assemble(native_builder=None if args.assemble_only else compile_native)
    print(f"Prepared {len(metadata['outputs'])} files in {RUNTIME}")


if __name__ == '__main__':
    main()
