"""Private native build with seed-bound mixed chest rewards."""

import json, sys
from pathlib import Path
import recover_boshy_pickups as pickups
from gameplay.rewards import transform
from gameplay.reward_plan import LOCATIONS

routes = pickups.routes
changes = []


def sections(payload):
    result, audit = transform(routes.payloads[payload], pickups.sections(payload))
    changes.extend(audit)
    return result


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._write_frame_item = (
        pickups.intro.characters.onehit.gameplay.blood.item
    )
    routes.write_mfa._exe_event_sections = sections
    status = routes.main()
    assert status == 0 and len(changes) == len(LOCATIONS) == 36
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "reward-source-audit.json").write_text(
        json.dumps(dict(rewards=changes, pickups=pickups.changes), indent=2) + "\n"
    )
