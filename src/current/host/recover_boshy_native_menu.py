"""Generate the native title-menu project on top of tested gameplay rules."""

import json, sys
from pathlib import Path
import recover_boshy_onehit as onehit
from native_menu.events import transform, clone_objects

routes = onehit.routes
original_frame = routes.write_mfa._write_frame
changes = []


def sections(payload):
    ss = onehit.sections(payload)
    if routes.payloads[payload] == 2:
        ss, audit = transform(ss)
        changes.append(audit)
    return ss


def frame(w, app, frame, index, objects, *args, **kwargs):
    if index == 1:
        objects = dict(enumerate(objects))
        clone_objects(objects, frame)
    return original_frame(w, app, frame, index, objects, *args, **kwargs)


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._write_frame_item = onehit.gameplay.blood.item
    routes.write_mfa._exe_event_sections = sections
    routes.write_mfa._write_frame = frame
    status = routes.main()
    assert status == 0 and len(changes) == 1
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "native-menu-audit.json").write_text(
        json.dumps(
            dict(
                menu=changes, one_hit=onehit.changes, gameplay=onehit.gameplay.changes
            ),
            indent=2,
        )
        + "\n"
    )
