"""Separate full-route prototype; original engine frame identities are preserved."""

from pathlib import Path
import json, sys
from recover_boshy_transition import (
    app,
    SOURCE,
    write_mfa,
    original_sections,
    walk_chunks,
    main,
)
from recover_boshy_alpha import preserve_alpha_only, recovered
from recover_boshy_frame_links import (
    handles,
    original_handles,
    table,
    canonical,
    aliases,
)
from recovery.frame_handles import rewrite_sections
from transition.router import transform, STAGES, CATALOGUE_HASH
from recovery.gameplay_rules import beta_damage_guards

objects = {o["handle"]: o for o in app.objects()[0]}
frames = app.frames()
changes = []
payloads = {}
for frame, c in enumerate(app.by_id[0x3333], 1):
    kids, _, _ = walk_chunks(c.payload, 0, len(c.payload), keep_payload=True)
    payloads[next(k.payload for k in kids if k.id == 0x333D)] = frame


def sections(payload):
    frame = payloads[payload]
    ss = original_sections(payload)
    ss, gameplay_audit = beta_damage_guards(frame, ss)
    result, audit = transform(frame, ss, table, objects, frames[frame - 1]["instances"])
    result, refs = rewrite_sections(result, aliases, table)
    changes.append(
        {
            **audit,
            "alias_changes": refs["literal_alias_changes"],
            "gameplay_rules": gameplay_audit,
        }
    )
    return result


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == SOURCE.resolve()
    type(app).frame_handles = handles
    write_mfa._object_effect_chunk = preserve_alpha_only
    write_mfa._exe_event_sections = sections
    try:
        status = main()
    finally:
        type(app).frame_handles = original_handles
    assert status == 0
    covered = {e["spot"] for f in changes for e in f["edges"]}
    assert covered == set(STAGES), set(STAGES) - covered
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "route-audit.json").write_text(
        json.dumps(
            {
                "schema": 4,
                "catalogue_hash": CATALOGUE_HASH,
                "frames": changes,
                "covered": sorted(covered),
                "canonical_handles": canonical,
                "alpha_records": recovered,
                "validation": "generated source only; requires compilation and live tests",
            },
            indent=2,
        )
    )
