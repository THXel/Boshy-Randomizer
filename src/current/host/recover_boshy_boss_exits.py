"""Build a separate three-boss Fusion prototype from the hash-verified original."""

from pathlib import Path
import json, sys
from recover_boshy_transition import (
    app,
    write_mfa,
    walk_chunks,
    original_sections,
    main,
)
from recover_boshy_alpha import preserve_alpha_only, recovered
from transition.boss_exits import mario, kracko, cheetah_v3, GROUP, TARGETS

patches = {}
for frame, transform in [(5, kracko), (10, mario), (54, cheetah_v3)]:
    raw = app.by_id[0x3333][frame - 1].payload
    kids, _, _ = walk_chunks(raw, 0, len(raw), keep_payload=True)
    payload = next(c.payload for c in kids if c.id == 0x333D)
    patches[payload] = (frame, transform)
changes = []


def patched_sections(payload):
    sections = original_sections(payload)
    if payload in patches:
        frame, transform = patches[payload]
        sections, audit = transform(sections)
        changes.append({'frame': frame, **audit})
    return sections


if __name__ == '__main__':
    write_mfa._object_effect_chunk = preserve_alpha_only
    write_mfa._exe_event_sections = patched_sections
    status = main()
    assert status == 0 and len(changes) == 3
    (Path(sys.argv[sys.argv.index('--out') + 1]) / 'source-audit.json').write_text(
        json.dumps(
            {
                'group': GROUP,
                'targets': TARGETS,
                'route_changes': changes,
                'alpha_records': recovered,
            },
            indent=2,
        )
    )
