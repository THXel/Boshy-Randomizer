"""Seed-local native music replacement. Sound effects and events stay intact.

Uses the previously audited local fangame catalogue. No audio files are copied
into the source repository; no runtime hooks or death-cue substitutions exist.
"""

import hashlib
import json
import sys
from pathlib import Path
from visuals.scenery_pack import App, REPO
from visuals.fusion25 import rebuild
from music.bank import read, write

sys.path.insert(0, str(REPO / "src/python/audio"))
from music_randomizer import SOURCE_TRACKS, EXCLUDED_TRACKS
from music_categories import cue_kind

from music.packs import PACKS
CATALOGUE = REPO / "assets/catalogues/soundpack-music-kinds.json"


def mapping(seed, pack, rows=None):
    if pack not in PACKS or not isinstance(seed, str) or not 1 <= len(seed) <= 256:
        raise ValueError("Music pack or seed")
    if pack == "original":
        # Version the new category-safe native mapping; archived hook-based runs
        # keep their old mapping. Independent bags never consume route RNG.
        rows = [
            dict(file=n, kind=cue_kind(n))
            for n in SOURCE_TRACKS
            if n not in EXCLUDED_TRACKS
        ]
        prefix = "boshy-native-music-v1"
    else:
        prefix = "boshy-pack-v2"
    result = {}
    for kind in ("level", "boss"):

        def order(value):
            return hashlib.sha256(
                (prefix + "\0" + kind + "\0" + seed + "\0" + value).encode()
            ).digest()

        files = [r["file"] for r in rows if r["kind"] == kind]
        if not files or len(files) != len(set(files)):
            raise ValueError("Missing or duplicate classified " + kind + " music")
        files.sort(key=order)
        cues = sorted((n for n in SOURCE_TRACKS if cue_kind(n) == kind), key=order)
        result.update({cue: files[i % len(files)] for i, cue in enumerate(cues)})
    return result


def pack_rows(root, pack):
    root = Path(root).resolve()
    d = json.loads((root / "pack.json").read_text())
    if d.get("version") != 1 or d.get("id") != pack or pack not in PACKS[1:]:
        raise ValueError("Pack identity")
    audited = json.loads(CATALOGUE.read_text())["packs"][pack]
    rows, seen = [], set()
    for row in d["tracks"]:
        file = row["file"]
        rel = Path(file)
        path = root / rel
        if (
            rel.is_absolute()
            or ".." in rel.parts
            or path.is_symlink()
            or not path.resolve().is_relative_to(root)
            or file in seen
        ):
            raise ValueError("Pack path or duplicate")
        seen.add(file)
        known = audited.get(file)
        if (
            not row.get("shuffle")
            or row.get("roles")
            or not known
            or known["sha256"] != row.get("sha256")
            or known["kind"] not in ("level", "boss")
        ):
            continue
        if not 30 < float(row["seconds"]) <= 1200:
            raise ValueError("Gameplay music duration")
        rows.append(dict(file=file, kind=known["kind"], sha256=known["sha256"]))
    return rows


def prepare(base, expected_sha, seed, pack, pack_root=None, enabled=True):
    app = App(base)
    actual = hashlib.sha256(app.data).hexdigest()
    if actual != expected_sha:
        raise ValueError("Unverified music base")
    if pack not in PACKS or type(enabled) is not bool:
        raise ValueError("Music settings")
    audit = dict(
        version=1,
        enabled=enabled,
        pack=pack,
        seed=seed,
        base_sha256=actual,
        catalogue_sha256=hashlib.sha256(CATALOGUE.read_bytes()).hexdigest(),
        scope="Native sample data only; all events, channels, sound effects, graphics and executable code unchanged",
    )
    if not enabled:
        return app.data, dict(audit, sha256=actual, changed=[])
    sounds, slots = read(app.payload(0x6668), app.payload(0x5557))
    byname = {s.name: s for s in sounds.values() if s.name in SOURCE_TRACKS}
    if set(byname) != set(SOURCE_TRACKS) or sum(
        s.name in SOURCE_TRACKS for s in sounds.values()
    ) != len(SOURCE_TRACKS):
        raise ValueError("Missing or duplicate original music cue")
    rows = pack_rows(pack_root, pack) if pack != "original" else None
    swaps = mapping(seed, pack, rows)
    audio = {}
    for target in sorted(set(swaps.values())):
        if pack == "original":
            audio[target] = byname[target].audio
        else:
            row = next(r for r in rows if r["file"] == target)
            data = (Path(pack_root) / target).read_bytes()
            if hashlib.sha256(data).hexdigest() != row["sha256"]:
                raise ValueError("Music file checksum: " + target)
            if not data.startswith(b"OggS"):
                raise ValueError("Audited native pack requires Ogg audio")
            audio[target] = data
    changed = []
    for cue, target in swaps.items():
        sound = byname[cue]
        sounds[sound.handle] = sound.replace(audio[target])
        changed.append(
            dict(
                handle=sound.handle,
                cue=cue,
                kind=cue_kind(cue),
                target=target,
                audio_sha256=hashlib.sha256(audio[target]).hexdigest(),
            )
        )
    bank, offsets = write(sounds, slots)
    result = rebuild(app, {0x6668: bank, 0x5557: offsets}, sound_bank=True)
    audit.update(
        sha256=hashlib.sha256(result).hexdigest(),
        changed=changed,
        unchanged_sound_effects=len(sounds) - len(changed),
    )
    return result, audit
