"""Export a fresh isolated Cheetah exit probe from an existing BR12 shared seed."""
from pathlib import Path
import argparse, hashlib, json, os, runpy, sys
ROOT = Path(__file__).resolve().parents[2]
REPO = ROOT/'work/Boshy-Randomizer'
sys.path.insert(0, str(REPO/'src/python/rules'))
from run_settings import decode
from fusion_route import probe_save, SOURCES, SOURCE_SPOT

def export(shared, game, out, *, source=SOURCE_SPOT, positions_path=None):
    game = Path(game)
    with game.open('rb') as file:
        game_hash = hashlib.file_digest(file, 'sha256').hexdigest()
    if not shared.startswith('BR12-'):
        raise ValueError('An existing BR12 shared seed is required; no silent default options.')
    seed, options = decode(shared)
    positions = json.loads(Path(positions_path or REPO/'assets/INI/positions.json').read_text())
    plan, plaintext = probe_save(seed, options, positions, game_hash, source=source)
    rc4 = runpy.run_path(str(REPO/'src/shared/PY/rc4_utils.py'))['rc4_crypt']
    payload = rc4(b'BLOB', plaintext.encode('latin1'))
    out = Path(out)
    # Never touch an existing save or directory. Validate everything before creating it.
    out.mkdir(parents=True, exist_ok=False)
    (out/'SaveFile1.ini').write_bytes(payload)
    (out/'plan.json').write_text(json.dumps({**plan, 'shared_seed': shared}, indent=2))
    (out/'NOTICE.txt').write_text('Private boss exit test. Starts at the selected boss. '
        'Only the outgoing route is implemented. Other seed options are recorded, '
        'not applied. Do not use as a complete run or released installer.\n')
    return plan

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--shared', required=True)
    parser.add_argument('--game', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--source',choices=SOURCES,default=SOURCE_SPOT)
    args = parser.parse_args()
    print(json.dumps(export(args.shared, args.game, args.out, source=args.source), indent=2))
