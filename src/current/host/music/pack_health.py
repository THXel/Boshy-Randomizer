"""Validate only the selected optional pack; keep asset errors out of startup."""
import hashlib
import io
import json
import wave
from pathlib import Path
from music.packs import ANIMATIONS


class PackUnavailable(ValueError):
    pass


def manifest(root, pack):
    root = Path(root)
    path = root / "pack.json"
    if root.is_symlink() or path.is_symlink():
        raise ValueError("Linked soundpack")
    data = json.loads(path.read_text())
    if data.get("version") != 1 or data.get("id") != pack:
        raise ValueError("Soundpack identity")
    return data


def read_asset(root, row, limit=128_000_000):
    root = Path(root)
    rel = Path(row["file"])
    path = root / rel
    if rel.is_absolute() or ".." in rel.parts or path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("Soundpack path")
    if path.stat().st_size > limit:
        raise ValueError("Soundpack asset size")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != row["sha256"]:
        raise ValueError("Soundpack checksum")
    return raw


def death_audio(root, pack):
    data = manifest(root, pack)
    tracks = {row["file"]: row for row in data["tracks"]}
    raw = read_asset(root, tracks["death-visuals/death-sequence.wav"], 8_000_000)
    with wave.open(io.BytesIO(raw)) as wav:
        if wav.getnchannels() not in (1, 2) or wav.getsampwidth() != 2 or not 0 < wav.getnframes() / wav.getframerate() <= 120:
            raise ValueError("Death audio format")
    result = {".wav": raw}
    if pack == "undertale":
        if data["death_visuals"].get("music_loop") != "mus_gameover.ogg":
            raise ValueError("Missing game-over music loop")
        music = read_asset(root, tracks["mus_gameover.ogg"])
        if not music.startswith(b"OggS"):
            raise ValueError("Game-over music format")
        result["-loop.ogg"] = music
    return result


class PackHealth:
    """Cache successful checks by file identity, never failures or game ticks."""
    def __init__(self):
        self.verified = {}

    def check(self, root, pack):
        if pack == "original":
            return
        try:
            if pack not in ANIMATIONS:
                raise ValueError("Unknown soundpack")
            from music.soundtrack import pack_rows, mapping
            from music.title import TRACKS
            from visuals.blood_pack import load_pack
            data = manifest(root, pack)
            rows = pack_rows(root, pack)
            mapping("health-check", pack, rows)  # Both level and boss pools exist.
            tracks = {r["file"]: r for r in data["tracks"]}
            title, title_hash = TRACKS[pack]
            if tracks[title]["sha256"] != title_hash or "opening" not in tracks[title].get("roles", []):
                raise ValueError("Opening music identity")
            needed = [tracks[r["file"]] for r in rows] + [tracks[title], tracks["death-visuals/death-sequence.wav"]]
            if pack == "undertale":
                needed.append(tracks["mus_gameover.ogg"])
            needed += data["death_visuals"]["blood"]["frames"]
            paths = [Path(root)/"pack.json"] + [Path(root)/r["file"] for r in needed]
            stamp = []
            for path in paths:
                if path.is_symlink() or not path.resolve().is_relative_to(Path(root).resolve()):
                    raise ValueError("Linked soundpack asset")
                st = path.stat()
                stamp.append((str(path), st.st_size, st.st_mtime_ns, st.st_ctime_ns))
            stamp = tuple(stamp)
            if self.verified.get(pack) == stamp:
                return
            for row in needed:
                raw = read_asset(root, row)
                if row["file"].endswith(".ogg") and not raw.startswith(b"OggS"):
                    raise ValueError("Music format")
            load_pack(root)
            death_audio(root, pack)
            self.verified[pack] = stamp
        except (OSError, ValueError, KeyError, TypeError, StopIteration, wave.Error) as error:
            self.verified.pop(pack, None)
            raise PackUnavailable(pack) from error
