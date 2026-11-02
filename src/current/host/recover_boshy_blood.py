"""Recover native routes, actor colours and player-owned blood into a private MFA."""

import json
import sys
from pathlib import Path
import recover_boshy_routes as routes
from visuals.actor_palettes import transform as actors
from visuals.player_blood import transform as blood, extend_object

changes = []
original_item = routes.write_mfa._write_frame_item


def item(w, obj, *args, **kwargs):
    return original_item(w, extend_object(obj), *args, **kwargs)


def sections(payload):
    frame = routes.payloads[payload]
    ss, aa = actors(
        frame,
        routes.sections(payload),
        routes.objects,
        routes.frames[frame - 1]["instances"],
    )
    ss, bb = blood(frame, ss, routes.objects, routes.frames[frame - 1]["instances"])
    changes.extend(bb)
    return ss


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._write_frame_item = item
    routes.write_mfa._exe_event_sections = sections
    try:
        status = routes.main()
    finally:
        type(routes.app).frame_handles = routes.original_handles
        routes.write_mfa._write_frame_item = original_item
    assert status == 0 and changes
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "blood-source-audit.json").write_text(
        json.dumps(
            dict(
                scope="native source; requires compilation and live verification",
                changes=changes,
                routes=routes.changes,
            ),
            indent=2,
        )
    )
