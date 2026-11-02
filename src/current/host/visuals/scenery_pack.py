"""Prepare seed-local scenery by cloning images before the engine starts.

Original image records are immutable. Only reviewed scenery object's image
references point to new copies. Alpha, anchors, dimensions, collisions and
frame events are preserved. No live image ownership/freeing is involved.
"""

import difflib
import hashlib
import json
import struct
import sys
from pathlib import Path

from app_paths import LAB, ROOT, REPO

sys.path.insert(0, str(LAB / "KlikBack/src"))
sys.path.insert(0, str(REPO / "src/python/graphics"))
from klikback.core.mmf2.read_app import App
from sprite_chaos import choice, render, read_assets, selected
from intro_cast import image
from visuals.fusion25 import (
    image_bank,
    write_images,
    property_bank,
    write_properties,
    animation_slot,
    rebuild,
)

BASE_SHA = "93c2eb281c853ed52abf98891c2931ea881f04ff114a60e01c57f275dc122be5"
BLOOD_BASE_SHA = "2034c9c66a109e6f75221277f323fe544f20cc11a7103f492f81b6da6004ba6e"
GAMEPLAY_BASE_SHA = "4e569c0740a4a207f81e6263baba29c1e384c00b026acfd35698a5c41ad5f1f5"
UNIFIED_BASE_SHA = "5f850eae32e02965d1360887da052b7c64aa9f6d5ea9309cc4fe5126fa391c3b"
CLASSIC_BASE_SHA = "c55f0530afc985877243a5a5e56f20588a9dabb73490dce35e7d6061cf16067f"
from native_menu.builds import DYNAMIC_SHA, EXTRAS_SHA

SUPPORTED_BASE_SHAS = {
    DYNAMIC_SHA,
    EXTRAS_SHA,
    BASE_SHA,
    BLOOD_BASE_SHA,
    GAMEPLAY_BASE_SHA,
    UNIFIED_BASE_SHA,
    CLASSIC_BASE_SHA,
}
ORIGINAL_SHA = "dc6a1a551254f1d1003d14c0bf58f639a7ea94f99f74b5c635ddaf9bc4ec0806"
PROTECTED = {
    1054: "Sonic/Old Sonic shrinking platform is a landing cue above fire",
    1119: "Known source/runtime animation mismatch",
}
CATEGORIES = ("sprite_backgrounds", "sprite_decor", "sprite_tiles")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record_selection(options, records):
    for key in ("sprite_scenery", *CATEGORIES):
        if key in options and type(options[key]) is not bool:
            raise ValueError("Expected boolean: " + key)
    dim = options.get("sprite_dim", 0)
    if type(dim) is not int or not 0 <= dim <= 80:
        raise ValueError("Background dimming must be between 0 and 80")
    if not options.get("sprite_scenery", False):
        return []
    return [
        r
        for r in records
        if r["category"] in (1, 2, 4)
        and r["oi"] not in PROTECTED
        and selected(r, options)
    ]


def object_mapping(app, original_objects, *, active_only=False):
    """Map reviewed objects; runtime backdrops can change static object order.

    Artwork consumers only need Actives. Restricting their matching to that
    ordered subsequence avoids ambiguous repeated backdrop/extension names.
    """
    if active_only:
        original_objects = [o for o in original_objects if o["type"] == 2]
    names = app.payload(0x2254).decode("utf-16le").split("\0")
    if names.pop() != "":
        raise ValueError("Object name terminator")
    headers = app.payload(0x2253)
    if len(headers) != len(names) * 16:
        raise ValueError("Object header count")
    from visuals.runtime_scenery import PREFIX, records

    allowed_helpers = {
        PREFIX + str(r["oi"]) + "/" + str(layer)
        for r in records()
        if r["type"] == 1
        for layer in range(8)
    }
    built = []
    indices = []
    seen_helpers = set()
    spider_seen = False
    from native_menu.options_locale import targets

    reviewed_additions = {
        **{"Translated Options " + str(oi): 2 for oi in targets()},
        "Randomizer Death Screen": 2,
        "Randomizer Death Soul": 2,
        "Randomizer Death Caption": 2,
        **{
            name: (33 if oi in (4506, 4507) else 2)
            for oi, name in __import__(
                "native_menu.presentation_events", fromlist=["NAMES"]
            ).NAMES.items()
        },
        "Run Result Panel": 2,
        "Run Result View": 33,
        "Run Result Input": 33,
    }
    from visuals.background_groups import catalogue, PREFIX as BG_PREFIX

    reviewed_additions.update(
        {
            BG_PREFIX + str(i): (48 if r["type"] == 48 else 2)
            for i, r in enumerate(catalogue()["objects"])
        }
    )
    reviewed_additions.update(
        {
            name: 2
            for name in (
                "Dresser keyboard focus",
                "Dresser unlocked filter",
                "Dresser controls",
            )
        }
    )
    reviewed_additions["Options LiveTracker"] = 2
    reviewed_additions["Options Open LiveTracker"] = 40
    reviewed_additions["Randomizer Update Card"] = 2
    reviewed_additions["Randomizer Background Shade"] = 2
    from native_menu.target_hud import ROWS as TARGET_ROWS

    reviewed_additions["Target Checklist Button"] = 2
    reviewed_additions.update({"Target Checklist Row " + str(i): 2 for i in range(len(TARGET_ROWS))})
    seen_additions = set()
    for index, name in enumerate(names):
        handle, kind = struct.unpack_from("<HH", headers, index * 16)
        if handle != index:
            raise ValueError("Unexpected optimized object handles")
        if name in reviewed_additions:
            if kind != reviewed_additions[name] or name in seen_additions:
                raise ValueError("Unexpected completion/options helper")
            seen_additions.add(name)
            continue
        if name == "Randomizer Spider":
            if kind != 2 or spider_seen:
                raise ValueError("Unexpected native spider helper")
            spider_seen = True
            continue
        if name.startswith(PREFIX):
            if name not in allowed_helpers or kind != 2 or name in seen_helpers:
                raise ValueError("Unexpected native scenery helper")
            seen_helpers.add(name)
            continue
        if active_only and kind != 2:
            continue
        built.append((name, kind))
        indices.append(index)
    additions = [
        ("Randomizer Panel", 2),
        ("Randomizer Input", 33),
        ("Randomizer View", 33),
        ("Randomizer Cast Left", 2),
        ("Randomizer Cast Right", 2),
        ("Randomizer Cast Centre", 2),
        ("Randomizer Session", 33),
    ]
    if active_only:
        additions = [row for row in additions if row[1] == 2]
    source = [(o["name"], o["type"]) for o in original_objects]
    mapping = {}
    for tag, a, b, c, d in difflib.SequenceMatcher(
        None, source, built, autojunk=False
    ).get_opcodes():
        if tag == "equal":
            mapping.update(
                {
                    original_objects[a + i]["handle"]: indices[c + i]
                    for i in range(b - a)
                }
            )
        elif (
            tag == "insert"
            and built[c:d] == additions
            and a < len(original_objects)
            and original_objects[a]["handle"] == 93
        ):
            # Exact title-only additions in the reviewed combined build. The
            # mapping still points to each original object's shifted index.
            continue
        elif (
            tag == "insert"
            and built[c:d] == [("Randomizer Attribution", 3)]
            and a == 18
        ):
            continue
        elif tag != "delete":
            raise ValueError("Compiled object order/identity changed")
    return mapping


def prepare(base, original, seed, options):
    if not isinstance(seed, str) or not 1 <= len(seed) <= 256:
        raise ValueError("Invalid seed")
    app = App(base)
    base_sha = sha(app.data)
    if base_sha not in SUPPORTED_BASE_SHAS:
        raise ValueError("Unsupported compiled base")
    original_app = App(original)
    if sha(original_app.data) != ORIGINAL_SHA:
        raise ValueError("Unsupported source game")
    records = json.loads(
        (REPO / "assets/catalogues/sprite_chaos_catalogue.json").read_text()
    )["records"]
    rows = record_selection(options, records)
    audit = {
        "schema": 1,
        "seed": seed,
        "options": options,
        "base_sha256": base_sha,
        "protected_objects": PROTECTED,
        "changed": [],
        "scope": "offline cloned scenery images; native actor palettes remain save controlled",
    }
    if not rows:
        audit.update(sha256=base_sha, unchanged=True)
        return app.data, audit
    original_objects = original_app.objects()[0]
    mapping = object_mapping(app, original_objects)
    images, index_size = image_bank(app.payload(0x6666), app.payload(0x5555))
    properties = property_bank(app.payload(0x2256), app.payload(0x2257))
    originals = list(properties)
    assets = read_assets(original, ORIGINAL_SHA, rows)
    decoded = {}
    modified = {}

    def source_image(handle):
        if handle not in decoded:
            decoded[handle] = image(assets[handle], max_side=4096)
        return decoded[handle]

    for row in rows:
        oi = row["oi"]
        if oi not in mapping:
            raise ValueError("Reviewed object missing from compiled game: " + str(oi))
        built = mapping[oi]
        body = bytearray(properties[built])
        if row["type"] == 1:
            expected = (18, row["obstacle"], row["width"], row["height"], row["image"])
            if len(body) != 18 or struct.unpack("<4IH", body) != expected:
                raise ValueError("Backdrop geometry/collision changed: " + str(oi))
            at = 16
        elif row["type"] == 2:
            at = animation_slot(body, row["anim"], row["direction"], row["frame"])
            if struct.unpack_from("<H", body, at)[0] != row["image"]:
                raise ValueError("Scenery animation image changed: " + str(oi))
        else:
            raise ValueError("Unsupported scenery type")
        stored = images[row["image"]]
        im = stored.rgba()
        if stored.size != (row["width"], row["height"]) or struct.unpack_from(
            "<4h", stored.header, 28
        ) != tuple(row[k] for k in ["hx", "hy", "ax", "ay"]):
            raise ValueError("Image geometry/anchors changed: " + str(oi))
        source_alpha = source_image(row["image"]).getchannel("A").tobytes()
        if im.getchannel("A").tobytes() != source_alpha:
            raise ValueError("Compiled/source transparency differs: " + str(oi))
        style = choice(seed, row)
        shuffled = options.get(
            {1: "sprite_backgrounds", 2: "sprite_decor", 4: "sprite_tiles"}[
                row["category"]
            ],
            False,
        )
        result = render(
            im,
            source_image(style),
            row["category"],
            options.get("sprite_dim", 0),
            shuffle=shuffled,
        )
        handle = index_size
        index_size += 1
        if handle >= 32768:
            raise ValueError("Image handle capacity exceeded")
        clone = stored.clone(handle, result)
        assert clone.rgba().tobytes() == result.tobytes(), "Image encoding roundtrip"
        images[handle] = clone
        struct.pack_into("<H", body, at, handle)
        properties[built] = bytes(body)
        modified.setdefault(built, set()).add(at)
        audit["changed"].append(
            {
                "source_oi": oi,
                "compiled_oi": built,
                "name": row["name"],
                "category": row["category"],
                "frames": row["frames"],
                "original_image": row["image"],
                "new_image": handle,
                "image_offset": at,
                "style": style,
                "width": im.width,
                "height": im.height,
                "alpha_sha256": sha(source_alpha),
                "pixels_sha256": sha(result.tobytes()),
            }
        )
    for index, (before, after) in enumerate(zip(originals, properties)):
        restored = bytearray(after)
        for at in modified.get(index, []):
            restored[at : at + 2] = before[at : at + 2]
        if bytes(restored) != before:
            raise ValueError("Non-image object property changed")
    ib, ix = write_images(images, index_size)
    pb, px = write_properties(properties)
    result = rebuild(app, {0x6666: ib, 0x5555: ix, 0x2256: pb, 0x2257: px})
    audit.update(
        sha256=sha(result),
        original_images_preserved=len(images) - len(rows),
        original_image_records_sha256=sha(
            b"".join(im.bytes() for im in list(images.values())[: -len(rows)])
        ),
        cloned_images=len(rows),
        changed_objects=len(modified),
        unchanged_chunk_ids=[
            hex(c.id)
            for c in app.chunks
            if c.id not in (0x6666, 0x5555, 0x2256, 0x2257, 0x2242)
        ],
    )
    return result, audit
