"""Native route-station character cycling on top of verified mixed rewards."""

import json, sys
from pathlib import Path
import recover_boshy_rewards as rewards
from gameplay.character_cycle import transform

routes = rewards.routes
changes = []


def sections(payload):
    frame = routes.payloads[payload]
    result, audit = transform(
        frame,
        rewards.sections(payload),
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
        rewards.pickups.intro.characters.onehit.gameplay.blood.item
    )
    routes.write_mfa._exe_event_sections = sections
    status = routes.main()
    assert status == 0 and len({a["stage"] for a in changes}) == len(routes.STAGES)
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "cycle-source-audit.json").write_text(
        json.dumps(dict(cycle=changes, rewards=rewards.changes), indent=2) + "\n"
    )
