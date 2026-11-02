"""Build current gameplay with the original menu choreography and native sessions."""

import json
import sys
from pathlib import Path
import recover_boshy_targets as targets
from native_menu import events, session, classic_events

routes = targets.routes
original_frame = routes.write_mfa._write_frame
changes = []


def sections(payload):
    result = targets.sections(payload)
    if routes.payloads[payload] == 2:
        result, menu = classic_events.transform(result)
        result, lifecycle = session.transform(result)
        changes.append(dict(menu=menu, lifecycle=lifecycle))
    return result


def frame(w, app, frame, index, objects, *args, **kwargs):
    if index == 1:
        objects = dict(objects) if isinstance(objects, dict) else dict(enumerate(objects))
        events.clone_objects(objects, frame)
        session.clone_object(objects, frame)
    return original_frame(w, app, frame, index, objects, *args, **kwargs)


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._write_frame_item = (
        targets.modes.cycle.rewards.pickups.intro.characters.onehit.gameplay.blood.item
    )
    routes.write_mfa._exe_event_sections = sections
    routes.write_mfa._write_frame = frame
    assert routes.main() == 0 and len(changes) == 1
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "classic-source-audit.json").write_text(
        json.dumps(
            dict(
                scope=__doc__,
                menu=changes,
                targets=targets.changes,
                validation="Generated source; compilation and live verification required",
            ),
            indent=2,
        )
        + "\n"
    )
