"""Recover all original frame handles alongside the three tested boss exits."""

from pathlib import Path
import json, sys
from recover_boshy_transition import app, SOURCE, write_mfa, original_sections, main
from recover_boshy_alpha import preserve_alpha_only, recovered
from recover_boshy_boss_exits import patches
from recovery.frame_handles import mapping, rewrite_sections

table, canonical, aliases = mapping(
    app.payload(0x222B), app.app_header()["numberOfFrames"]
)
changes = []
original_handles = type(app).frame_handles


def handles(self):
    # This wrapper accepts only the pinned original game as its CLI input.
    found = mapping(self.payload(0x222B), self.app_header()["numberOfFrames"])
    assert found == (table, canonical, aliases)
    return list(canonical)


def sections(payload):
    rows = original_sections(payload)
    route_audit = None
    if payload in patches:
        frame, transform = patches[payload]
        rows, route_audit = transform(rows)
    rows, audit = rewrite_sections(rows, aliases, table)
    changes.append({"frame": len(changes) + 1, **audit, "route": route_audit})
    return rows


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == SOURCE.resolve()
    type(app).frame_handles = handles
    write_mfa._object_effect_chunk = preserve_alpha_only
    write_mfa._exe_event_sections = sections
    try:
        status = main()
    finally:
        type(app).frame_handles = original_handles
    assert status == 0 and len(changes) == 61
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "frame-link-audit.json").write_text(
        json.dumps(
            {
                "original_lookup": table,
                "canonical_handles": canonical,
                "aliases": aliases,
                "frames": changes,
                "alpha_records": recovered,
            },
            indent=2,
        )
    )
