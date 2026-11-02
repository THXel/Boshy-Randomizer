"""Native private build: optional fast pickups and item-dialog suppression."""

import json, sys
from pathlib import Path
import recover_boshy_intro_skip as intro
from gameplay.pickups import transform

routes = intro.routes
changes = []


def sections(payload):
    result, audit = transform(
        routes.payloads[payload], intro.sections(payload), routes.objects
    )
    changes.extend(audit)
    return result


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._write_frame_item = intro.characters.onehit.gameplay.blood.item
    routes.write_mfa._exe_event_sections = sections
    status = routes.main()
    assert status == 0 and sum(c["rule"] == "quiet_pickups" for c in changes) == 4
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "pickup-source-audit.json").write_text(
        json.dumps(
            dict(
                scope="Generated source; compilation and live tests required",
                pickups=changes,
                intro_skip=intro.changes,
                character_profile=intro.characters.changes,
            ),
            indent=2,
        )
        + "\n"
    )
