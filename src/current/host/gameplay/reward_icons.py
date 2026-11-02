"""Point each chest's revealed frame at the assigned native reward icon.

Closed/open chest frames, properties and engine-owned images are unchanged.
Only frame 2 of animation 0/direction 0 is replaced, before process startup.
"""

import hashlib, struct
from gameplay.reward_plan import LOCATIONS, mapping
from visuals.scenery_pack import App, object_mapping
from visuals.fusion25 import property_bank, write_properties, animation_slot, rebuild


def prepare(base, original, expected_sha, seed, enabled):
    app = App(base)
    actual = hashlib.sha256(app.data).hexdigest()
    if actual != expected_sha:
        raise ValueError("Reward icon base mismatch")
    audit = dict(schema=1, base_sha256=actual, seed=seed, enabled=enabled, changed=[])
    if not enabled:
        return app.data, dict(audit, sha256=actual)
    original_app = App(original)
    ids = object_mapping(app, original_app.objects()[0], active_only=True)
    props = property_bank(app.payload(0x2256), app.payload(0x2257))
    icons = {}
    for loc in LOCATIONS:
        body = props[ids[loc["object"]]]
        at = animation_slot(body, 0, 0, 2)
        icons[loc["source"]] = struct.unpack_from("<H", body, at)[0]
    rewards = mapping(seed, enabled)
    for loc in LOCATIONS:
        oi = ids[loc["object"]]
        body = bytearray(props[oi])
        at = animation_slot(body, 0, 0, 2)
        before = bytes(body)
        image = icons[rewards[loc["key"]]["name"]]
        struct.pack_into("<H", body, at, image)
        props[oi] = bytes(body)
        assert before[:at] == body[:at] and before[at + 2 :] == body[at + 2 :]
        audit["changed"].append(
            dict(
                key=loc["key"],
                oi=oi,
                offset=at,
                image=image,
                reward=rewards[loc["key"]],
            )
        )
    bank, index = write_properties(props)
    result = rebuild(app, {0x2256: bank, 0x2257: index})
    return result, dict(audit, sha256=hashlib.sha256(result).hexdigest())
