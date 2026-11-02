"""Build the private native routes/graphics/blood source with optional God Mode."""

import json, sys
from pathlib import Path
import recover_boshy_blood as blood
from gameplay.god_mode import transform
from gameplay.controls import transform as controls

routes = blood.routes
changes = []


def sections(payload):
    frame = routes.payloads[payload]
    ss, audit = transform(
        frame,
        blood.sections(payload),
        routes.objects,
        routes.frames[frame - 1]["instances"],
    )
    ss, control_audit = controls(frame, ss, routes.objects, routes.frames[frame - 1]["instances"])
    audit.extend(control_audit)
    changes.extend(audit)
    return ss


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._write_frame_item = blood.item
    routes.write_mfa._exe_event_sections = sections
    try:
        status = routes.main()
    finally:
        type(routes.app).frame_handles = routes.original_handles
        routes.write_mfa._write_frame_item = blood.original_item
    assert status == 0 and changes
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "gameplay-source-audit.json").write_text(
        json.dumps(
            dict(
                scope="Native source; requires compilation and live verification",
                gameplay=changes,
                blood=blood.changes,
                routes=routes.changes,
            ),
            indent=2,
        )
        + "\n"
    )
