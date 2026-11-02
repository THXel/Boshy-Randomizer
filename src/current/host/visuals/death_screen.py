"""Native, once-per-player-death pack screen and audio on the original channel.

The original death handler still owns destruction, stats, blood and retry.
Only its screen/sound presentation changes when a known blood pack is selected.
"""

import copy
import hashlib
import io
import json
import struct
from functools import lru_cache
from pathlib import Path
from PIL import Image
from gameplay.native_events import Events
from gameplay.normal_plan import FRAMES
from gameplay.spider_events import window
from native_menu.events import alt, value, file_path, condition
from transition.events import action, commands, event, expression, integer
from transition.router import frame_metadata, params
from visuals.embedded_blood import PACK_ROOT, PACKS, raw_image
from visuals.player_blood import GROUP

OBJECT = 4400
FIRST_IMAGE = 21000
NAME = "Randomizer Death Screen"
from visuals.death_soul import OBJECT as SOUL_OBJECT
from visuals.death_caption import OBJECT as CAPTION_OBJECT, position as caption_position


def checked(root, row):
    rel = Path(row["file"])
    path = root / rel
    if (
        rel.is_absolute()
        or ".." in rel.parts
        or path.is_symlink()
        or not path.resolve().is_relative_to(root.resolve())
    ):
        raise ValueError("Death asset path")
    raw = path.read_bytes()
    if len(raw) > 8_000_000 or hashlib.sha256(raw).hexdigest() != row["sha256"]:
        raise ValueError("Death asset checksum")
    return raw


@lru_cache(maxsize=1)
def assets():
    result, handle = {}, FIRST_IMAGE
    for name, animation in PACKS.items():
        root = PACK_ROOT / name
        manifest = json.loads((root / "pack.json").read_text())
        screen = manifest["death_visuals"]["screen"]
        rows, ticks, loop = screen["frames"], screen["ticks"], screen["loop"]
        if (
            not 1 <= len(rows) <= 100
            or len(rows) != len(ticks)
            or type(loop) is not int
            or not 0 <= loop < len(rows)
        ):
            raise ValueError("Death screen timeline")
        if any(type(n) is not int or not 1 <= n <= 50 for n in ticks):
            raise ValueError("Death screen durations")
        images, frames = [], []
        for row, duration in zip(rows, ticks):
            with Image.open(io.BytesIO(checked(root, row))) as im:
                if im.format != "PNG" or im.size != (640, 480):
                    raise ValueError("Death screen geometry")
                images.append(im.convert("RGBA"))
            frames.extend([handle] * duration)
            handle += 1
        sound = next(
            r
            for r in manifest["tracks"]
            if r["file"] == "death-visuals/death-sequence.wav"
        )
        audio = checked(root, sound)
        if not audio.startswith(b"RIFF"):
            raise ValueError("Death audio format")
        result[name] = dict(
            animation=animation,
            images=images,
            handles=list(range(handle - len(images), handle)),
            frames=frames,
            loop=sum(ticks[:loop]),
            audio=audio,
        )
    return result


def prepare(folder, pack=None):
    """Runtime audio only: compiled graphics do not need loading on launch."""
    from music.pack_health import death_audio
    root = Path(folder) / "native-death"
    root.mkdir(exist_ok=True)
    if root.is_symlink():
        raise ValueError("Linked death asset directory")
    for name in ([pack] if pack else PACKS):
        if name == "original":
            continue
        for suffix, audio in death_audio(PACK_ROOT / name, name).items():
            path = root / (name + suffix)
            if path.is_symlink():
                raise ValueError("Linked death sound")
            if not path.exists() or path.read_bytes() != audio:
                from menu_host.store import atomic
                atomic(path, audio)


def image_loader(original):
    def load(app):
        images = dict(original(app))
        for data in assets().values():
            for handle, image in zip(data["handles"], data["images"]):
                if handle in images:
                    raise ValueError("Death image handle collision")
                from visuals.death_graphics import encode
                images[handle] = encode(image, (0, 0))
        from visuals.death_soul import assets as soul_assets
        soul = soul_assets()
        for handle, image, origin in zip(soul['handles'], soul['images'], soul['origins']):
            if handle in images:
                raise ValueError("Soul image handle collision")
            from visuals.death_graphics import encode
            images[handle] = encode(image, origin)
        from visuals.death_caption import assets as caption_assets
        for data in caption_assets().values():
            for handle, image, origin in zip(data["handles"],data["images"],data["origins"]):
                if handle in images:
                    raise ValueError("Caption image handle collision")
                images[handle] = encode(image, origin)
        return images

    return load


def convert_frame(number, frame, objects):
    if number not in FRAMES:
        return frame, objects
    result = copy.deepcopy(frame)
    objs = dict(objects) if isinstance(objects, dict) else dict(enumerate(objects))
    assert OBJECT not in objs
    obj = copy.deepcopy(objs[41])
    obj.update(handle=OBJECT, name=NAME, values=[0, 0], qualifiers=[])
    props = bytearray(obj["properties"])
    struct.pack_into("<I", props, 16, struct.unpack_from("<I", props, 16)[0] | 0x6000)
    # Decorative overlay: use a box instead of generating per-pixel collision
    # masks for every full-screen animation image. It has no collision events.
    struct.pack_into("<H", props, 42, struct.unpack_from("<H", props, 42)[0] | 4)
    obj["properties"] = bytes(props)
    obj["animations"] = [
        dict(
            slot=data["animation"],
            name="Death " + name,
            directions=[
                dict(
                    direction=0,
                    minSpeed=100,
                    maxSpeed=100,
                    repeat=0,
                    backTo=data["loop"],
                    frames=data["frames"],
                )
            ],
        )
        for name, data in assets().items()
    ]
    # A neutral default animation is hidden at frame start.
    obj["animations"].insert(0, copy.deepcopy(objs[41]["animations"][0]))
    objs[OBJECT] = obj
    result["instances"].append(
        dict(
            handle=59400,
            objectInfo=OBJECT,
            x=-1000,
            y=-1000,
            layer=max(i["layer"] for i in frame["instances"]),
            parentType=0,
            parentObjectInfo=0,
            tail="00 " * 8,
        )
    )
    from visuals.death_soul import convert_frame as soul_frame
    result, objs = soul_frame(result, objs, OBJECT)
    from visuals.death_caption import convert_frame as caption_frame
    return caption_frame(result, objs, OBJECT)


def death_sound(c):
    return (
        not c[0]
        and c[1:3] == (-2, 11)
        and params(c[-1])[-1][1] == expression(integer(3))
    )


def transform(frame, sections, objects, instances):
    if frame not in FRAMES:
        return sections, []
    save, player, _ = frame_metadata(frame, sections, objects, instances)
    e = Events(sections, low=0x1000, high=0xFFFE)
    result, audit = [], []
    for si, rows in enumerate(sections):
        output = []
        for ri, row in enumerate(rows):
            cs = commands(row)
            if not (
                any(not c[0] and c[1:4] == (2, 24, player) for c in cs)
                and any(c[0] and c[1:3] == (-1, -16) and b"Die\0" in c[-1] for c in cs)
            ):
                output.append(row)
                continue
            if not any(death_sound(c) for c in cs):
                output.append(row)
                continue
            assert any(not c[0] and c[1:4] == (2, 24, player) for c in cs), (
                frame,
                si,
                ri,
                "not player death",
            )
            assert any(c[0] and c[1:3] == (-1, -16) and b"Die\0" in c[-1] for c in cs)

            def conditions(extra):
                out = []
                for c in cs:
                    if c[0]:
                        raw = bytearray(c[-1])
                        struct.pack_into("<H", raw, 14, e.ident())
                        out.append(bytes(raw))
                return out + extra

            fallback = [e.eq(save, GROUP, "Animation", n, 1) for n in PACKS.values()]
            output.append(
                event(row, conditions(fallback), [c[-1] for c in cs if not c[0]])
            )
            for pack, animation in PACKS.items():
                from visuals.death_soul import begin as soul_begin
                changed = soul_begin(player) if pack == "undertale" else []
                for c in cs:
                    if c[0]:
                        continue
                    if death_sound(c):
                        ps = params(c[-1])
                        assert ps[-1][1] == expression(integer(3))
                        changed += [
                            action(
                                -2,
                                28,
                                0,
                                [
                                    file_path("native-death\\" + pack + ".wav"),
                                    ps[-1][1],
                                ],
                            )
                        ]
                    else:
                        changed.append(c[-1])
                if pack == "undertale":
                    from visuals.death_caption import begin as caption_begin
                    changed += caption_begin(save)
                changed += [
                    value(OBJECT, 0, integer(1)),
                    value(OBJECT, 1, integer(int(pack == "undertale"))),
                    action(2, 17, OBJECT, [expression(integer(animation))]),
                    action(2, 2, OBJECT, [expression(window(0))]),
                    action(2, 3, OBJECT, [expression(window(1))]),
                    action(2, 27, OBJECT, []),
                ]
                output.append(
                    event(
                        row,
                        conditions([e.eq(save, GROUP, "Animation", animation)]),
                        changed,
                    )
                )
            audit.append(
                dict(frame=frame, section=si, row=ri, player=player, sound_channel=3)
            )
        result.append(output)
    assert len(audit) == 1, (frame, audit)
    gameover = {
        i["objectInfo"]
        for i in instances
        if any(
            468 in d["frames"]
            for a in objects[i["objectInfo"]].get("animations", [])
            for d in a["directions"]
        )
    }
    assert len(gameover) == 1, (frame, "original Game Over artwork", gameover)
    result.append(
        [
            e.row([e.start()], [action(2, 26, OBJECT, []), action(2, 26, SOUL_OBJECT, []), action(2, 26, CAPTION_OBJECT, [])]),
            # Once the short break sequence ends, loop only the music on the
            # original death channel. R/F2 retain their original stop behavior.
            e.row(
                [e.cmp(alt(OBJECT, 1), integer(1)),
                 condition(-2, -8, 0, [expression(integer(3))], e.ident())],
                [value(OBJECT, 1, integer(2)),
                 action(-2, 29, 0, [file_path("native-death\\undertale-loop.ogg"),
                                    expression(integer(3)), expression(integer(0), 27)])],
            ),
            e.row(
                [e.cmp(alt(OBJECT, 0), integer(1))],
                [
                    action(2, 2, OBJECT, [expression(window(0))]),
                    action(2, 3, OBJECT, [expression(window(1))]),
                    *caption_position(),
                    *[action(2, 26, oi, []) for oi in sorted(gameover)],
                ],
            ),
        ]
    )
    return result, audit
