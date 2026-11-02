"""Private gameplay build with explicit native loading of the local character profile."""

import json, sys
from pathlib import Path
import recover_boshy_onehit as onehit
from gameplay.character_profile import transform

routes = onehit.routes
changes = []


def sections(payload):
    frame = routes.payloads[payload]
    ss, audit = transform(frame, onehit.sections(payload), routes.objects)
    changes.extend(audit)
    return ss


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._write_frame_item = onehit.gameplay.blood.item
    routes.write_mfa._exe_event_sections = sections
    status = routes.main()
    assert status == 0 and len(changes) >= 48
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "character-source-audit.json").write_text(
        json.dumps(
            dict(
                scope="Generated source; requires compilation and live verification",
                character_profile=changes,
                one_hit=onehit.changes,
                gameplay=onehit.gameplay.changes,
            ),
            indent=2,
        )
        + "\n"
    )
