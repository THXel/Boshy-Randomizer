"""Prepare, validate and stage immutable per-save native scenery PNGs."""

import hashlib
import io
import tempfile
from pathlib import Path
from functools import lru_cache
from PIL import Image
from visuals.runtime_scenery import records, DIRECTORY
from visuals import background_groups
from visuals.scenery_pack import (
    read_assets,
    image,
    choice,
    render,
    record_selection,
    ORIGINAL_SHA,
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


@lru_cache(maxsize=1)
def originals():
    from export_native_run import ORIGINAL

    return read_assets(ORIGINAL, ORIGINAL_SHA, records())


@lru_cache(maxsize=256)
def graphic(handle):
    return image(originals()[handle], max_side=4096)


def prepare(folder, seed, options):
    selected = {r["oi"] for r in record_selection(options, records())} - background_groups.owned()
    root = Path(folder) / DIRECTORY
    root.mkdir()
    assets = []
    settings = dict(Schema=1, **background_groups.settings(seed, options))
    for index, row in enumerate(records()):
        original = graphic(row["image"])
        style = choice(seed, row)
        if row["oi"] in selected:
            result = render(
                original,
                graphic(style),
                row["category"],
                options.get("sprite_dim", 0),
                # Whole landscapes are selected by background_groups. Backgrounds
                # outside that audited catalogue retain their original artwork;
                # never replace an isolated layer with an unrelated sprite.
                shuffle=row["category"] != 1 and options.get(
                    {1: "sprite_backgrounds", 2: "sprite_decor", 4: "sprite_tiles"}[
                        row["category"]
                    ],
                    False,
                ),
            )
        else:
            result = original
        if row["category"] == 4 and row["oi"] in selected:
            from visuals.readability import preserve_edges
            result = preserve_edges(original, result)
        assert (
            result.size == original.size
            and result.getchannel("A").tobytes() == original.getchannel("A").tobytes()
        )
        data = io.BytesIO()
        result.save(data, format="PNG")
        raw = data.getvalue()
        digest = sha(raw)
        filename = f"{index:03d}-{digest[:16]}.png"
        (root / filename).write_bytes(raw)
        settings["Image" + str(index)] = DIRECTORY + "\\" + filename
        assets.append(
            dict(
                index=index,
                oi=row["oi"],
                image=row["image"],
                file=filename,
                sha256=digest,
                alpha_sha256=sha(original.getchannel("A").tobytes()),
                changed=result.tobytes() != original.tobytes(),
            )
        )
    # A run with wholly original scenery can use the embedded image bank.
    # Keep its verified PNG assets for older engines and plan compatibility.
    settings["EmbeddedOnly"] = int(not any(row["changed"] for row in assets))
    return assets, settings


def validate_assets(folder, plan):
    if plan["runtime_scenery_schema"] != 1:
        raise ValueError("Runtime scenery schema")
    rows = plan["runtime_scenery_assets"]
    settings = plan["runtime_scenery_settings"]
    if (
        len(rows) != len(records())
        or settings.get("Schema") != 1
        or len(settings) != len(rows) + 1 + (11 if "BackgroundSchema" in settings else 0)
        + (1 if "EmbeddedOnly" in settings else 0)
    ):
        raise ValueError("Incomplete runtime scenery")
    if "BackgroundSchema" in settings:
        expected = background_groups.settings(plan["seed"], plan["options"]["extras"])
        if any(settings.get(k) != v for k,v in expected.items()):
            raise ValueError("Background group selection changed")
    embedded = settings.get("EmbeddedOnly", 0)
    if embedded not in (0, 1):
        raise ValueError("Invalid embedded scenery setting")
    root = Path(folder) / DIRECTORY
    if root.is_symlink():
        raise ValueError("Linked runtime scenery directory")
    for index, (row, source) in enumerate(zip(rows, records())):
        digest = row["sha256"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Runtime scenery checksum")
        filename = f"{index:03d}-{digest[:16]}.png"
        if (row["index"], row["oi"], row["image"], row["file"]) != (
            index,
            source["oi"],
            source["image"],
            filename,
        ):
            raise ValueError("Runtime scenery identity")
        if settings.get("Image" + str(index)) != DIRECTORY + "\\" + filename:
            raise ValueError("Runtime scenery path")
        path = root / filename
        if path.is_symlink() or sha(path.read_bytes()) != digest:
            raise ValueError("Changed runtime scenery")
        with Image.open(path) as im:
            rgba = im.convert("RGBA")
            if (
                rgba.size != (source["width"], source["height"])
                or sha(rgba.getchannel("A").tobytes()) != row["alpha_sha256"]
            ):
                raise ValueError("Runtime scenery geometry")
            if embedded and rgba.tobytes() != graphic(source["image"]).tobytes():
                raise ValueError("Embedded scenery must match original artwork")
        if row["alpha_sha256"] != sha(
            graphic(source["image"]).getchannel("A").tobytes()
        ):
            raise ValueError("Runtime scenery mask")


def link_assets(source, target, plan):
    validate_assets(source, plan)
    dest = Path(target) / DIRECTORY
    dest.mkdir()
    for row in plan["runtime_scenery_assets"]:
        (dest / row["file"]).hardlink_to(Path(source) / DIRECTORY / row["file"])


def stage(source, target, plan):
    target = Path(target)
    root = target / DIRECTORY
    if root.is_symlink():
        raise ValueError("Linked working scenery")
    with tempfile.TemporaryDirectory(prefix=".scenery-stage-", dir=target) as temp:
        temp = Path(temp)
        link_assets(source, temp, plan)
        if root.exists():
            root.rename(temp / "previous")
        try:
            (temp / DIRECTORY).rename(root)
        except OSError:
            if (temp / "previous").exists() and not root.exists():
                (temp / "previous").rename(root)
            raise
