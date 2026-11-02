"""Save-local native music files; identical game executable across music seeds.

Only classified gameplay music playback changes. Original channels, loop counts,
volume/frequency/position controls, conditions and all sound effects survive.
The private host still prepares local audio assets; single-EXE packaging is later.
"""

import hashlib
import struct
import tempfile
from pathlib import Path
from functools import lru_cache
from music.soundtrack import SOURCE_TRACKS, PACKS, mapping, pack_rows, cue_kind
from music.bank import read
from visuals.scenery_pack import App
from gameplay.native_events import Events
from gameplay.rewards import ini_string
from transition.events import action, commands, event, expression, integer
from transition.router import frame_metadata, guarded, params

GROUP = "FusionMusicV1"
NAMES = tuple(sorted(SOURCE_TRACKS))
DIRECTORY = "native-music"


@lru_cache(maxsize=1)
def original_audio():
    from export_native_run import ORIGINAL
    from visuals.scenery_pack import ORIGINAL_SHA

    app = App(ORIGINAL)
    if hashlib.sha256(app.data).hexdigest() != ORIGINAL_SHA:
        raise ValueError("Original music identity")
    # The rebuilt bank has an independently verified, lossless original audio
    # inventory. Original EXE bank encoding differs from Fusion 295.
    from native_menu.builds import DYNAMIC_BASE, DYNAMIC_SHA

    app = App(DYNAMIC_BASE)
    if hashlib.sha256(app.data).hexdigest() != DYNAMIC_SHA:
        raise ValueError("Reference music bank identity")
    bank, _ = read(app.payload(0x6668), app.payload(0x5557))
    audio = {s.name: s.audio for s in bank.values() if s.name in NAMES}
    if set(audio) != set(NAMES):
        raise ValueError("Incomplete original music")
    return audio


def prepare(folder, seed, pack, pack_root, enabled):
    if pack not in PACKS or type(enabled) is not bool:
        raise ValueError("Runtime music options")
    settings = dict(Schema=1, Enabled=int(enabled))
    if not enabled:
        return [], settings
    rows = pack_rows(pack_root, pack) if pack != "original" else None
    swaps = mapping(seed, pack, rows)
    root = Path(folder) / DIRECTORY
    root.mkdir()
    assets = []
    for index, cue in enumerate(NAMES):
        target = swaps[cue]
        if pack == "original":
            audio = original_audio()[target]
        else:
            row = next(r for r in rows if r["file"] == target)
            audio = (Path(pack_root) / target).read_bytes()
            if hashlib.sha256(audio).hexdigest() != row["sha256"]:
                raise ValueError("Changed audited music")
        suffix = (
            "ogg"
            if audio.startswith(b"OggS")
            else "mp3" if audio.startswith(b"ID3") else None
        )
        if suffix is None:
            raise ValueError("Unsupported native music file")
        digest = hashlib.sha256(audio).hexdigest()
        # Different slot tracks have different names even if the engine caches
        # file-backed samples across frame changes.
        filename = f"{index:02d}-{digest[:16]}.{suffix}"
        (root / filename).write_bytes(audio)
        settings[f"Cue{index:02d}"] = DIRECTORY + "\\" + filename
        assets.append(
            dict(
                cue=cue,
                kind=cue_kind(cue),
                target=target,
                file=filename,
                sha256=digest,
            )
        )
    return assets, settings


def validate_assets(folder, plan):
    if plan["runtime_music_schema"] != 1:
        raise ValueError("Runtime music schema")
    settings = plan["runtime_music_settings"]
    enabled = plan["music_enabled"]
    if settings.get("Schema") != 1 or settings.get("Enabled") != int(enabled):
        raise ValueError("Runtime music settings")
    rows = plan["runtime_music_assets"]
    if len(rows) != (len(NAMES) if enabled else 0):
        raise ValueError("Incomplete runtime music")
    root = Path(folder) / DIRECTORY
    if root.is_symlink():
        raise ValueError("Linked runtime music directory")
    for index, row in enumerate(rows):
        name = row["file"]
        digest = row["sha256"]
        if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("Runtime music checksum")
        if name not in (
            f"{index:02d}-{digest[:16]}.ogg",
            f"{index:02d}-{digest[:16]}.mp3",
        ):
            raise ValueError("Runtime music filename")
        if row["cue"] != NAMES[index] or row["kind"] != cue_kind(NAMES[index]):
            raise ValueError("Runtime music cue")
        if settings.get(f"Cue{index:02d}") != DIRECTORY + "\\" + name:
            raise ValueError("Runtime music path")
        path = root / name
        if (
            path.is_symlink()
            or hashlib.sha256(path.read_bytes()).hexdigest() != row["sha256"]
        ):
            raise ValueError("Changed runtime music")


def link_assets(source, target, plan):
    """Copy validated immutable files into an isolated staging/candidate folder."""
    validate_assets(source, plan)
    dest = Path(target) / DIRECTORY
    dest.mkdir()
    for row in plan["runtime_music_assets"]:
        (dest / row["file"]).hardlink_to(Path(source) / DIRECTORY / row["file"])


def stage(source, target, plan):
    """Replace the previous slot's music only while the native menu owns audio."""
    target = Path(target)
    root = target / DIRECTORY
    if root.is_symlink():
        raise ValueError("Linked working music")
    with tempfile.TemporaryDirectory(prefix=".music-stage-", dir=target) as t:
        temp = Path(t)
        link_assets(source, temp, plan)
        if root.exists():
            root.rename(temp / "previous")
        try:
            (temp / DIRECTORY).rename(root)
        except OSError:
            previous = temp / "previous"
            if previous.exists() and not root.exists():
                previous.rename(root)
            raise


def cue(command):
    if command[0] or command[1] != -2 or command[2] not in (11, 12):
        return None
    ps = params(command[-1])
    if ps[0][0] != 6:
        return None
    name = ps[0][1][8:].split(b"\0", 1)[0].decode("latin1")
    return name if name in NAMES else None


def transform(frame, sections, objects, instances):
    # Lobby audio is not gameplay and has no player/save lifecycle.
    if not any(objects[i["objectInfo"]]["name"] == "Player" for i in instances):
        return sections, []
    if not any(cue(c) for rows in sections for row in rows for c in commands(row)):
        return sections, []
    ini, _, _ = frame_metadata(frame, sections, objects, instances)
    e = Events(sections, low=0x1000, high=0xFFFE)
    result, changed = [], []

    def clone(conditions):
        cloned = []
        for condition in conditions:
            data = bytearray(condition)
            struct.pack_into("<H", data, 14, e.ident())
            cloned.append(bytes(data))
        return cloned

    for rows in sections:
        out = []
        for row in rows:
            cs = commands(row)
            if not any(cue(c) for c in cs):
                out.append(row)
                continue
            conditions = [c[-1] for c in cs if c[0]]
            original = [c[-1] for c in cs if not c[0]]
            replacement = []
            for c in cs:
                if c[0]:
                    continue
                name = cue(c)
                if name is None:
                    replacement.append(c[-1])
                    continue
                index = NAMES.index(name)
                path = (
                    struct.pack("<hhH", -1, 8, 6)
                    + struct.pack("<hhH", 0, 2, 6)
                    + ini_string(GROUP, f"Cue{index:02d}", "", ini)
                )
                ps = params(c[-1])
                replacement.append(
                    action(
                        -2,
                        28 if c[2] == 11 else 29,
                        0,
                        [expression(path, 45), *[p[1] for p in ps[1:]]],
                    )
                )
                changed.append(name)
            out.append(
                event(
                    row,
                    clone(guarded(conditions, [e.eq(ini, GROUP, "Enabled", 1, 1)])),
                    original,
                )
            )
            out.append(
                event(
                    row,
                    clone(guarded(conditions, [e.eq(ini, GROUP, "Enabled", 1)])),
                    replacement,
                )
            )
        result.append(out)
    result[0].insert(0, e.row([e.start()], [e.load(ini, "SaveFile1.ini")]))
    # Reserve the original music channel before any automatic-channel SFX.
    # Hello Kitty's roar otherwise claims channel 2 before file playback starts.
    # Fusion's file-backed playback does not recover it like embedded samples do.
    reserve = Events(result, low=0x1000, high=0xFFFE)
    result[0].insert(
        1,
        reserve.row(
            [reserve.start(), reserve.eq(ini, GROUP, "Enabled", 1)],
            [action(-2, 30, 0, [expression(integer(2))])],
        ),
    )
    return result, [
        dict(
            frame=frame,
            cues=changed,
            channels_and_loops_preserved=True,
            automatic_sfx_excluded_from_music_channel=2,
        )
    ]
