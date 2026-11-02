"""Build the first native visual integration on top of verified route recovery."""

import json
import sys
from pathlib import Path
import recover_boshy_routes as routes
from visuals.actor_palettes import transform

changes = []


def sections(payload):
    frame = routes.payloads[payload]
    original = routes.sections(payload)
    result, audit = transform(
        frame, original, routes.objects, routes.frames[frame - 1]["instances"]
    )
    changes.extend(audit)
    return result


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._exe_event_sections = sections
    try:
        status = routes.main()
    finally:
        type(routes.app).frame_handles = routes.original_handles
    assert status == 0 and changes
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "visual-audit.json").write_text(
        json.dumps(
            {
                "scope": "native actor palettes only; scenery/music/blood migration remains open",
                "routes": routes.changes,
                "actors": changes,
                "alpha_records": routes.recovered,
                "catalogue_sha256": routes.CATALOGUE_HASH,
                "validation": "generated source; compilation and live verification required",
            },
            indent=2,
        )
    )
