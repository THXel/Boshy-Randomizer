"""Repeat all four phase comparisons with fresh evidence folders.

This is a diagnostic suite for two hash-identified EXEs. It temporarily disables
Die fastloops in isolated processes and sets documented HP/position fixtures.
It does not modify either EXE or enable the sprite randomizer.
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', default=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    args = parser.parse_args()
    if not args.run_id or not all(c.isalnum() or c in '-_' for c in args.run_id):
        parser.error('run-id must contain only letters, digits, hyphens and underscores')
    root = Path(__file__).resolve().parent
    for variant, scene, seconds in (
        ('rebuilt', 'solgryn', 60),
        ('original', 'solgryn', 60),
        ('rebuilt', 'sonic', 30),
        ('original', 'sonic', 30),
    ):
        print('START', variant, scene, flush=True)
        subprocess.run([
            sys.executable, str(root / 'scene_probe.py'), variant, scene,
            '--seconds', '0', '--leave-open',
            '--output-group', 'Fusion-PhaseBoot-' + args.run_id,
        ], check=True)
        subprocess.run([
            sys.executable, str(root / 'phase_capture.py'), variant + '-' + scene,
            '--seconds', str(seconds), '--label=-' + args.run_id,
        ], check=True)
        time.sleep(1)
    print('PHASE SUITE COMPLETE', flush=True)


if __name__ == '__main__':
    main()
