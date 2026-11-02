"""Private native gameplay build with save-local automatic boss intro skips."""

import json
import sys
from pathlib import Path
import recover_boshy_characters as characters
from gameplay.intro_skip import transform, FRAMES

routes = characters.routes
changes = []


def sections(payload):
    result, audit = transform(routes.payloads[payload], characters.sections(payload))
    changes.extend(audit)
    return result


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._write_frame_item = characters.onehit.gameplay.blood.item
    routes.write_mfa._exe_event_sections = sections
    status = routes.main()
    assert (
        status == 0 and len(changes) == 13 and {r["frame"] for r in changes} == FRAMES
    )
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "intro-skip-source-audit.json").write_text(
        json.dumps(
            dict(
                scope="Generated source; requires compilation and live verification",
                intro_skip=changes,
                character_profile=characters.changes,
                one_hit=characters.onehit.changes,
                gameplay=characters.onehit.gameplay.changes,
            ),
            indent=2,
        )
        + "\n"
    )
