"""Create a separate Fusion project with alpha recovery and one native route edge."""
from pathlib import Path
import hashlib
import json
import sys
sys.path.insert(0, str(Path(__file__).parent / 'KlikBack/src'))
from klikback.core.mmf2 import write_mfa
from klikback.core.mmf2.read_app import App, walk_chunks
from klikback.cli import main
from recover_boshy_alpha import preserve_alpha_only, recovered
from transition.cheetah import transform

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('/home/thxel/.local/share/boshy-randomizer/IWBTB/I Wanna Be The Boshy.exe')
with SOURCE.open('rb') as file:
    assert hashlib.file_digest(file, 'sha256').hexdigest() == 'dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806'
app = App(SOURCE)
frame = app.by_id[0x3333][53]
chunks, _, _ = walk_chunks(frame.payload, 0, len(frame.payload), keep_payload=True)
events = next(c.payload for c in chunks if c.id == 0x333d)
original_sections = write_mfa._exe_event_sections
changes = []


def route_sections(payload):
    sections = original_sections(payload)
    if payload == events:
        sections, audit = transform(sections)
        changes.append(audit)
    return sections


if __name__ == '__main__':
    write_mfa._object_effect_chunk = preserve_alpha_only
    write_mfa._exe_event_sections = route_sections
    status = main()
    assert status == 0 and len(changes) == 1
    (Path(sys.argv[sys.argv.index('--out') + 1]) / 'source-audit.json').write_text(
        json.dumps({'route_changes': changes, 'alpha_records': recovered}, indent=2))
    raise SystemExit(status)
