"""Native chest reveal images loaded at scene entry, independent of EXE banks."""

import hashlib
import json
import struct
from functools import lru_cache
from build_profiles import PREFIX
from gameplay.reward_plan import LOCATIONS, GROUP, mapping
from visuals.scenery_pack import App, object_mapping, ORIGINAL_SHA, CLASSIC_BASE_SHA
from visuals.fusion25 import image_bank, property_bank, animation_slot
from gameplay.native_events import Events
from native_menu.classic_events import load
from transition.router import frame_metadata

NAMES = tuple(sorted({loc["source"] for loc in LOCATIONS}))


@lru_cache(maxsize=1)
def icons():
    from export_native_run import ORIGINAL

    from native_menu.builds import DYNAMIC_BASE, DYNAMIC_SHA

    base = DYNAMIC_BASE
    app = App(base)
    if hashlib.sha256(app.data).hexdigest() != DYNAMIC_SHA:
        raise ValueError("Reward artwork base identity")
    original = App(ORIGINAL)
    if hashlib.sha256(original.data).hexdigest() != ORIGINAL_SHA:
        raise ValueError("Reward artwork original identity")
    ids = object_mapping(app, original.objects()[0], active_only=True)
    images, _ = image_bank(app.payload(0x6666), app.payload(0x5555))
    props = property_bank(app.payload(0x2256), app.payload(0x2257))
    result = {}
    for loc in LOCATIONS:
        body = props[ids[loc["object"]]]
        handle = struct.unpack_from("<H", body, animation_slot(body, 0, 0, 2))[0]
        record = images[handle]
        hx, hy = struct.unpack_from("<hh", record.header, 28)
        result[loc["source"]] = (record.rgba(), hx, hy)
    return result


def prepare(folder):
    root = folder / "native-rewards"
    if root.is_symlink():
        raise ValueError("Linked reward artwork directory")
    root.mkdir(exist_ok=True)
    audit = []
    for index, name in enumerate(NAMES, 1):
        graphic, hx, hy = icons()[name]
        path = root / f"{index:02d}.png"
        graphic.save(path)
        audit.append(
            dict(
                name=name,
                file=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                hx=hx,
                hy=hy,
            )
        )
    (root / "manifest.json").write_text(json.dumps(audit, indent=2) + "\n")
    return audit


def settings(seed, enabled):
    return dict(
        RuntimeIcons=1,
        **{
            "Icon" + key: NAMES.index(reward["name"]) + 1
            for key, reward in mapping(seed, enabled).items()
        },
    )


def transform(frame, sections, objects, instances):
    present = {i["objectInfo"] for i in instances}
    locations = [loc for loc in LOCATIONS if loc["object"] in present]
    if not locations:
        return sections, []
    ini, _, _ = frame_metadata(frame, sections, objects, instances)
    e = Events(sections, low=0x8000, high=0xA000)
    rows = [e.row([e.start()], [e.load(ini, "SaveFile1.ini")])]
    for loc in locations:
        for index, name in enumerate(NAMES, 1):
            _, hx, hy = icons()[name]
            rows.append(
                e.row(
                    [
                        e.start(),
                        e.eq(ini, GROUP, "Schema", 1),
                        e.eq(ini, GROUP, "RuntimeIcons", 1),
                        e.eq(ini, GROUP, "Icon" + loc["key"], index),
                    ],
                    [
                        load(
                            loc["object"],
                            f"native-rewards/{index:02d}.png",
                            frame=2,
                            hx=hx,
                            hy=hy,
                        )
                    ],
                )
            )
    result = [list(s) for s in sections]
    result[0][2:2] = rows
    return result, [
        dict(frame=frame, locations=[loc["key"] for loc in locations], events=len(rows))
    ]


def validate_assets(folder, plan):
    if plan["runtime_reward_icons_schema"] != 1:
        raise ValueError("Unknown runtime reward asset schema")
    if (folder / "native-rewards").is_symlink():
        raise ValueError("Linked reward artwork directory")
    assets = plan["runtime_reward_assets"]
    if len(assets) != len(NAMES):
        raise ValueError("Incomplete reward artwork")
    for index, (name, row) in enumerate(zip(NAMES, assets), 1):
        filename = f"{index:02d}.png"
        path = folder / "native-rewards" / filename
        if row["name"] != name or row["file"] != filename or path.is_symlink():
            raise ValueError("Reward artwork identity")
        if hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]:
            raise ValueError("Changed reward artwork")
