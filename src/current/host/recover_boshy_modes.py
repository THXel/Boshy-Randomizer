"""Original progression plus native Normal character changes on the verified base."""

import json, sys
from pathlib import Path
import recover_boshy_cycle as cycle
from gameplay.normal_mode import transform

routes = cycle.routes
changes = []


def sections(payload):
    frame = routes.payloads[payload]
    result, audit = transform(
        frame,
        cycle.sections(payload),
        routes.objects,
        routes.frames[frame - 1]["instances"],
    )
    changes.extend(audit)
    return result


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._write_frame_item = (
        cycle.rewards.pickups.intro.characters.onehit.gameplay.blood.item
    )
    routes.write_mfa._exe_event_sections = sections
    status = routes.main()
    assert status == 0
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "modes-source-audit.json").write_text(
        json.dumps(dict(normal=changes), indent=2) + "\n"
    )
