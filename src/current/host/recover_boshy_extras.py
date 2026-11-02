"""Gameplay-only build with native mirror and death character options."""

import json, sys
from pathlib import Path
import recover_boshy_targets as targets
from gameplay import native_extras
from native_menu import attribution, social, display_build, options_display
from visuals import embedded_blood

original_frame = targets.routes.write_mfa._write_frame
routes = targets.routes
changes = []


def sections(payload):
    frame = routes.payloads[payload]
    result, audit = native_extras.transform(
        frame,
        targets.sections(payload),
        routes.objects,
        routes.frames[frame - 1]["instances"],
    )
    result, credit_audit = attribution.transform(frame, result)
    result, social_audit = social.transform(frame, result)
    result, display_audit = options_display.transform(
        frame, result, routes.objects, routes.frames[frame - 1]["instances"]
    )
    changes.extend(audit + credit_audit + social_audit + display_audit)
    return result


def frame(w, app, frame, index, objects, *args, **kwargs):
    return original_frame(w, app, frame, index, objects, *args, **kwargs)


if __name__ == "__main__":
    assert Path(sys.argv[1]).resolve() == routes.SOURCE.resolve()
    display_build.install(routes.write_mfa)
    type(routes.app).frame_handles = routes.handles
    routes.write_mfa._object_effect_chunk = routes.preserve_alpha_only
    routes.write_mfa._write_frame_item = (
        targets.modes.cycle.rewards.pickups.intro.characters.onehit.gameplay.blood.item
    )
    embedded_blood.install(
        routes.write_mfa,
        targets.modes.cycle.rewards.pickups.intro.characters.onehit.gameplay.blood,
    )
    routes.write_mfa._exe_event_sections = sections
    routes.write_mfa.inflated_images = attribution.image_loader(
        routes.write_mfa.inflated_images
    )
    routes.write_mfa.inflated_images = social.image_loader(
        routes.write_mfa.inflated_images
    )
    routes.write_mfa._write_frame = frame
    assert routes.main() == 0
    out = Path(sys.argv[sys.argv.index("--out") + 1])
    (out / "extras-source-audit.json").write_text(json.dumps(changes, indent=2) + "\n")
