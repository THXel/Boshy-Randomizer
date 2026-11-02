"""Native Target Select/Collect on the verified Normal/cycle/reward base."""

import json, sys
from pathlib import Path
import recover_boshy_modes as modes
from gameplay import target_mode, target_characters

routes = modes.routes
changes = []


def sections(payload):
    frame = routes.payloads[payload]
    result, a = target_mode.transform(
        frame,
        modes.sections(payload),
        routes.objects,
        routes.frames[frame - 1]["instances"],
    )
    result, b = target_characters.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    changes.extend(a + b)
    return result


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._write_frame_item = (
        modes.cycle.rewards.pickups.intro.characters.onehit.gameplay.blood.item
    )
    routes.write_mfa._exe_event_sections = sections
    assert routes.main() == 0
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "targets-source-audit.json").write_text(json.dumps(changes, indent=2) + "\n")
