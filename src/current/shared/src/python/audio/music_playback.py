"""Host-side PCM playback repair, also applied to frozen runs without changing seeds."""

import hashlib
import json
import os
import struct
import subprocess
import tempfile
import wave
from pathlib import Path
from native_session import atomic

PREFIX = '..\\menu-runtime\\music\\'
REVISION = b'boshy-pcm-s16-44100-stereo-v1\0'


def pcm_info(path):
    with wave.open(str(path), 'rb') as f:
        if (f.getnchannels(), f.getsampwidth(), f.getframerate(), f.getcomptype()) != (
            2,
            2,
            44100,
            'NONE',
        ) or not 0 < f.getnframes() <= 44100 * 1200:
            raise ValueError('Unsupported PCM format')
        count = f.getnframes()
        remaining = count * 4
        while remaining:
            block = f.readframes(min(65536, (remaining + 3) // 4))
            if not block:
                raise ValueError('Truncated PCM data')
            remaining -= len(block)
        if remaining:
            raise ValueError('PCM alignment')
        return count


def convert(source, cache):
    data = source.read_bytes()
    source_hash = hashlib.sha256(data).hexdigest()
    identity = hashlib.sha256(REVISION + data).hexdigest()[:24]
    target = cache / (identity + '.wav')
    metadata = cache / (identity + '.json')
    try:
        record = json.loads(metadata.read_text(encoding='utf-8'))
        if (
            record['source'] == source_hash
            and record['output'] == hashlib.sha256(target.read_bytes()).hexdigest()
            and pcm_info(target) == record['frames']
        ):
            return target
    except (OSError, ValueError, KeyError, EOFError, wave.Error):
        pass
    fd, name = tempfile.mkstemp(prefix='.pcm-', suffix='.wav', dir=cache)
    os.close(fd)
    temp = Path(name)
    try:
        subprocess.run(
            [
                (
                    __import__('imageio_ffmpeg').get_ffmpeg_exe()
                    if os.name == 'nt'
                    else 'ffmpeg'
                ),
                '-nostdin',
                '-v',
                'error',
                '-y',
                '-i',
                str(source),
                '-map',
                '0:a:0',
                '-vn',
                '-sn',
                '-dn',
                '-map_metadata',
                '-1',
                '-ac',
                '2',
                '-ar',
                '44100',
                '-c:a',
                'pcm_s16le',
                '-t',
                '1201',
                '-f',
                'wav',
                str(temp),
            ],
            check=True,
            capture_output=True,
            timeout=90,
        )
        frames = pcm_info(temp)
        output_hash = hashlib.sha256(temp.read_bytes()).hexdigest()
        os.replace(temp, target)
        atomic(
            metadata,
            (
                json.dumps(dict(source=source_hash, output=output_hash, frames=frames))
                + '\n'
            ).encode(),
        )
        return target
    finally:
        temp.unlink(missing_ok=True)


def exclude_tracks(raw, folder, manifest):
    """Apply the current pool exclusion to archived runs without rerolling others."""
    from music_randomizer import EXCLUDED_TRACKS

    path = folder / 'music-map.json'
    if not path.exists():
        return raw, None
    record = json.loads(path.read_text(encoding='utf-8'))
    count = struct.unpack_from('<I', raw, 36)[0]
    names = [
        raw[40 + i * 168 : 108 + i * 168].split(b'\0')[0].decode('latin1')
        for i in range(count)
    ]
    swaps = record['tracks']
    if (
        record['run_id'] != manifest['run_id']
        or len(set(names)) != count
        or set(swaps) != set(names)
    ):
        raise ValueError('Music map identity')
    indices = {name: i for i, name in enumerate(names)}
    result = bytearray(raw)
    changed = False
    for name in names:
        target = swaps[name]
        source_index = indices[name]
        seen = set()
        while target in EXCLUDED_TRACKS:
            if target in seen or target not in indices:
                raise ValueError('Excluded music cycle')
            seen.add(target)
            source_index = indices[target]
            target = swaps[target]
        if seen:
            start = 108 + indices[name] * 168
            source = 108 + source_index * 168
            result[start : start + 100] = raw[source : source + 100]
            changed = True
    # Read the original mapping throughout; apply updates only after traversal.
    if changed:
        updated = dict(swaps)
        for name in names:
            target = swaps[name]
            while target in EXCLUDED_TRACKS:
                target = swaps[target]
            updated[name] = target
        record['tracks'] = updated
        record['version'] = 2
    return bytes(result), record if changed else None


def prepare(base, manifest):
    """Preserve the run and apply current playback repairs and pool exclusions."""
    if not manifest['options'].get('extras', {}).get('music', False):
        return False
    base = Path(base)
    folder = base / 'menu-runtime'
    plan = folder / 'music.bin'
    cache = folder / 'music'
    raw = plan.read_bytes()
    try:
        count = struct.unpack_from('<I', raw, 36)[0]
        if (
            raw[:4] != b'BRM1'
            or raw[4:36] != manifest['run_id'].encode('ascii')
            or not 1 <= count <= 64
            or len(raw) != 40 + 168 * count
        ):
            raise ValueError('Music plan identity')
        raw, mapping_update = exclude_tracks(raw, folder, manifest)
        result = bytearray(raw)
        converted = {}
        for i in range(count):
            start = 40 + i * 168 + 68
            name = raw[start : start + 100].split(b'\0')[0].decode('ascii')
            if not name.startswith(PREFIX):
                raise ValueError('Music path')
            filename = name[len(PREFIX) :]
            if (
                not filename
                or any(
                    c not in 'abcdefghijklmnopqrstuvwxyz0123456789.' for c in filename
                )
                or filename in ('.', '..')
            ):
                raise ValueError('Music filename')
            source = cache / filename
            if source.is_symlink() or source.resolve().parent != cache.resolve():
                raise ValueError('Music source boundary')
            if filename not in converted:
                converted[filename] = convert(source, cache)
            path = (PREFIX + converted[filename].name).encode('ascii')
            if len(path) >= 100:
                raise ValueError('Music path length')
            result[start : start + 100] = path.ljust(100, b'\0')
        if mapping_update is not None:
            atomic(
                folder / 'music-map.json',
                (json.dumps(mapping_update, indent=2) + '\n').encode(),
            )
        atomic(plan, bytes(result))
        return True
    except Exception:
        # Never leave a half-converted or previous-session playback plan active.
        atomic(plan, b'BRM1' + bytes(36))
        raise
