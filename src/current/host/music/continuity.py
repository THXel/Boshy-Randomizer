"""Identify native music in game-only captures by normalized waveform matching.

Read-only offline evidence, including playback position before/after enemy kill.
No claim of subjective sound quality; native sound effects may lower correlation.
"""

import json, subprocess
from pathlib import Path
import numpy as np
from music.bank import read
from music.soundtrack import App
from build_profiles import executable


def decoded(data):
    raw = subprocess.run(
        [
            "ffmpeg",
            "-v",
            "error",
            "-i",
            "pipe:0",
            "-f",
            "f32le",
            "-ac",
            "1",
            "-ar",
            "22050",
            "pipe:1",
        ],
        input=data,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout
    # Same decimation for reference and capture, avoiding different filter phase.
    return np.frombuffer(raw, dtype="<f4").astype(float)[::5]


def match(reference, needle):
    if not 0 < len(needle) <= len(reference):
        raise ValueError("Insufficient audio samples for matching")
    needle = needle - np.mean(needle)
    n = len(needle)
    size = 1 << (len(reference) + n - 1).bit_length()
    convolution = np.fft.irfft(
        np.fft.rfft(reference, size) * np.fft.rfft(needle[::-1], size), size
    )[n - 1 : len(reference)]
    sums = np.r_[0, np.cumsum(reference)]
    squares = np.r_[0, np.cumsum(reference**2)]
    energy = squares[n:] - squares[:-n] - (sums[n:] - sums[:-n]) ** 2 / n
    denom = np.sqrt(np.maximum(energy, 0) * np.dot(needle, needle))
    valid = (energy > max(1e-10, float(np.max(energy)) * 1e-8)) & (denom > 1e-12)
    score = np.zeros_like(convolution)
    score[valid] = convolution[valid] / denom[valid]
    score = np.clip(score, -1, 1)
    index = int(np.argmax(score))
    return dict(reference_seconds=index / 4410, correlation=float(score[index]))


def match_after(reference, needle, before, elapsed, tolerance=0.2):
    """Disambiguate repeated musical phrases near the expected next position.

    First establish track identity against the whole recording. For continuity,
    matching an identical chorus minutes later is not evidence of a playback jump.
    This bounded second match still rejects silence and unexpected restarts.
    """
    expected = round((before["reference_seconds"] + elapsed) * 4410)
    margin = round(tolerance * 4410)
    start = expected - margin
    indices = np.arange(start, expected + margin + len(needle)) % len(reference)
    local = match(reference[indices], needle)
    local["reference_seconds"] = (start / 4410 + local["reference_seconds"]) % (
        len(reference) / 4410
    )
    return local


def check(folder, pack, scene):
    folder = Path(folder)
    capture = (
        np.frombuffer((folder / "game-audio.s16le").read_bytes(), dtype="<i2")
        .reshape(-1, 2)
        .mean(axis=1)
        / 32768
    )
    signal = capture[::5]
    # Avoid capture startup and the final buffer edge; native effects have ended.
    start = int(0.25 * 4410)
    end = len(signal) - int(0.85 * 4410)
    width = int(0.5 * 4410)
    app = App(executable("music-" + pack))
    bank, _ = read(app.payload(0x6668), app.payload(0x5557))
    cue = {"mario-routes": "Mario Boss Smithy", "ninja-routes": "NinjaGaiden (2)"}[
        scene
    ]
    ref = decoded(next(s.audio for s in bank.values() if s.name == cue))
    before = match(ref, signal[start : start + width])
    after = match(ref, signal[end : end + width])
    elapsed = (end - start) / 4410
    advance = after["reference_seconds"] - before["reference_seconds"]
    if advance < 0:
        advance += len(ref) / 4410
    result = dict(
        cue=cue,
        pack=pack,
        before=before,
        after=after,
        capture_elapsed=elapsed,
        playback_advance=advance,
        advance_error=abs(elapsed - advance),
        method=__doc__,
    )
    # Quantization and native mixing reduce amplitude correlation. Require
    # recognizable music, separation from an unrelated track, AND continuous
    # playback position. Merely finding any non-silent output cannot pass.
    other = next(
        s.audio
        for s in bank.values()
        if s.name in ("greengreens", "First Boss Music", "Castlevania")
        and s.audio != next(x.audio for x in bank.values() if x.name == cue)
    )
    negative = decoded(other)
    control = [
        match(negative, signal[start : start + width]),
        match(negative, signal[end : end + width]),
    ]
    result["unrelated_track_control"] = control
    result["passed"] = (
        min(before["correlation"], after["correlation"]) > 0.3
        and all(
            a["correlation"] - b["correlation"] > 0.15
            for a, b in zip((before, after), control)
        )
        and abs(elapsed - advance) < 0.08
    )
    (folder / "music-continuity.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
