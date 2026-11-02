"""Build a private Undertale pack from a user's local game and exported resources.

No downloads. Source files remain untouched. The output is staged and renamed
only after every required asset has been decoded and checked. Use --tool with
UndertaleModCli, or --assets with a prior export from undertale_export.csx.
"""

import argparse
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import tempfile
import wave
from pathlib import Path
from PIL import Image, ImageDraw
from music.soundtrack import CATALOGUE
from music.title import TRACKS
from music.bitmap_font import BitmapFont, CyrillicFont
from music.death_text import MESSAGES

RATE = 22050
BREAK_TICK, SHATTER_TICK, MUSIC_TICK, FULL_TICK = 33, 100, 183, 267


def digest(data):
    return hashlib.sha256(data).hexdigest()


def local_file(root, name):
    root = Path(root).resolve()
    path = root / name
    if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file():
        raise ValueError("Missing or linked Undertale asset: " + name)
    return path


def audio(path):
    return subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(path), "-f", "s16le", "-ac", "2",
        "-ar", str(RATE), "-", 
    ], timeout=45)


def timeline(assets, *, soul=False):
    def sprite(name, size):
        with Image.open(local_file(assets, name)) as im:
            if im.format != "PNG" or im.size != size:
                raise ValueError("Unexpected Undertale sprite geometry: " + name)
            return im.convert("RGBA")

    heart = sprite("spr_heart_0.png", (16, 16))
    broken = sprite("spr_heartbreak_0.png", (20, 16))
    shards = [sprite(f"spr_heartshards_{i}.png", (10, 10)) for i in range(4)]
    logo = sprite("spr_gameoverbg_0.png", (640, 240))
    # Undertale uses 30 Hz. Preserve its 20/40/50-frame waits at Boshy's 50 Hz.
    # Six deterministic pieces keep the effect independent of the run seed.
    schedule = (sorted(set(range(0, MUSIC_TICK, 50)) | {0, BREAK_TICK, SHATTER_TICK, MUSIC_TICK} | set(range(SHATTER_TICK, MUSIC_TICK, 5))) if soul
                else sorted(set(range(0, MUSIC_TICK, 50)) | {0, MUSIC_TICK, FULL_TICK} | set(range(MUSIC_TICK, FULL_TICK, 5))))
    frames = []
    font = BitmapFont(assets)
    for tick in schedule:
        canvas = Image.new("RGBA", (640, 480), (0, 0, 0, 0) if soul else "black")
        if soul and tick < SHATTER_TICK:
            part = heart if tick < BREAK_TICK else broken
            canvas.alpha_composite(part, (320 - part.width // 2, 240 - part.height // 2))
        elif soul and tick < MUSIC_TICK:
            age = (tick - SHATTER_TICK) * 30 / 50
            for i, degrees in enumerate((15, 70, 130, 195, 250, 310)):
                angle = math.radians(degrees)
                x = round(315 + 7 * math.cos(angle) * age)
                y = round(235 - 7 * math.sin(angle) * age + .1 * age * age)
                canvas.alpha_composite(shards[(int(age / 4) + i) % 4], (x, y))
        if not soul and tick >= MUSIC_TICK:
            overlay = Image.new("RGBA", (640, 480))
            overlay.alpha_composite(logo, (0, 0))
            draw = ImageDraw.Draw(overlay)
            draw.rounded_rectangle((280, 408, 320, 442), radius=3, outline="white", width=2)
            font.draw(overlay, "R", (292, 408))
            draw.arc((333, 413, 355, 435), 30, 310, fill="white", width=2)
            draw.polygon(((351, 410), (351, 419), (343, 415)), fill="white")
            opacity = min(1, (tick - MUSIC_TICK) / (FULL_TICK - MUSIC_TICK))
            overlay.putalpha(overlay.getchannel("A").point(lambda a: round(a * opacity)))
            canvas.alpha_composite(overlay)
        frames.append(canvas)
    ticks = [b - a for a, b in zip(schedule, schedule[1:] + [schedule[-1] + 1])]
    return frames, ticks


def caption_timeline(assets, language):
    """Small text surfaces, so translations do not duplicate full-screen frames."""
    message = MESSAGES[language]
    font = (CyrillicFont() if language == "ru" else
            BitmapFont(assets, "fnt_ja_main" if language == "ja" else "fnt_main"))
    end = FULL_TICK + 3 * len(message)
    schedule = sorted(set(range(0, FULL_TICK, 50)) | set(range(FULL_TICK, end + 1, 3)))
    frames = []
    for tick in schedule:
        image = Image.new("RGBA", (400, 80))
        visible = message[:max(0, (tick - FULL_TICK) // 3)]
        font.draw(image, visible, (0, 0))
        frames.append(image)
    return frames, [b-a for a,b in zip(schedule,schedule[1:]+[schedule[-1]+1])]


def build(game, assets, destination):
    game, assets, destination = map(Path, (game, assets, destination))
    if destination.exists():
        raise FileExistsError("Refusing to replace a soundpack: " + str(destination))
    destination.parent.mkdir(parents=True, exist_ok=True)
    catalogue = json.loads(CATALOGUE.read_text())["packs"]["undertale"]
    with tempfile.TemporaryDirectory(prefix=".undertale-", dir=destination.parent) as tmp:
        pack = Path(tmp) / "pack"
        pack.mkdir()
        tracks = []
        names = {name: [] for name in catalogue}
        names[TRACKS["undertale"][0]] = ["opening"]
        names["mus_gameover.ogg"] = ["gameover"]
        for name, roles in names.items():
            source = local_file(game, name)
            raw = source.read_bytes()
            expected = catalogue[name]["sha256"] if name in catalogue else TRACKS["undertale"][1] if roles == ["opening"] else None
            if not raw.startswith(b"OggS") or (expected and digest(raw) != expected):
                raise ValueError("Undertale track differs from audited catalogue: " + name)
            probe = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_format", "-of", "json", str(source)
            ], timeout=15))
            seconds = float(probe["format"]["duration"])
            if not 30 < seconds <= 1200:
                raise ValueError("Unexpected music duration: " + name)
            (pack / name).write_bytes(raw)
            tracks.append(dict(file=name, sha256=digest(raw), seconds=seconds, roles=roles, shuffle=not roles))
        visual = pack / "death-visuals"
        visual.mkdir()

        def png(name, image):
            path = visual / name
            image.save(path)
            return dict(file="death-visuals/" + name, sha256=digest(path.read_bytes()))

        captions = {}
        for language in MESSAGES:
            caption_images, caption_ticks = caption_timeline(assets, language)
            caption_rows = [png(f"caption-{language}-{i:02d}.png", image)
                            for i, image in enumerate(caption_images)]
            captions[language] = dict(frames=caption_rows, ticks=caption_ticks,
                                     loop=len(caption_rows)-1)
        frames, ticks = timeline(assets)
        soul_images, soul_ticks = timeline(assets, soul=True)
        soul_rows = [png(f"soul-{i:02d}.png", image) for i, image in enumerate(soul_images)]
        screen = [png(f"screen-{i:02d}.png", image) for i, image in enumerate(frames)]
        # The screen owns the one soul. Suppress only player blood for this pack;
        # enemy blood continues to use untouched animation zero.
        blank = png("blood-00.png", Image.new("RGBA", (1, 1)))
        sources = [(BREAK_TICK, audio(local_file(assets, "snd_break1.wav"))),
                   (SHATTER_TICK, audio(local_file(assets, "snd_break2.wav")))]
        import numpy as np
        # Only the break effects play once. The native channel starts the looping
        # Ogg when this short intro finishes, including its intentional silence.
        end = round(MUSIC_TICK * RATE / 50)
        if any(round(tick * RATE / 50) + len(raw) // 4 > end for tick, raw in sources):
            raise ValueError("Undertale break sound exceeds the intro")
        mix = np.zeros((end, 2), dtype=np.int32)
        for tick, raw in sources:
            pcm = np.frombuffer(raw, dtype="<i2").reshape(-1, 2)
            at = round(tick * RATE / 50)
            mix[at:at + len(pcm)] += pcm
        path = visual / "death-sequence.wav"
        with wave.open(str(path), "wb") as stream:
            stream.setparams((2, 2, RATE, 0, "NONE", "not compressed"))
            stream.writeframes(np.clip(mix, -32768, 32767).astype("<i2").tobytes())
        tracks.append(dict(file="death-visuals/death-sequence.wav", sha256=digest(path.read_bytes()), seconds=end / RATE, roles=["death"], shuffle=False))
        manifest = dict(version=1, id="undertale", name="Undertale", tracks=tracks,
                        source=dict(game="Undertale", local_import=True),
                        death_visuals=dict(version=1,
                            blood=dict(frames=[blank], fps=50, size=[1, 1], origin=[0, 0]),
                            screen=dict(frames=screen, ticks=ticks, loop=len(screen) - 1),
                            music_loop="mus_gameover.ogg",
                            captions=captions,
                            soul=dict(frames=soul_rows, ticks=soul_ticks, loop=len(soul_rows) - 1)))
        (pack / "pack.json").write_text(json.dumps(manifest, indent=2) + "\n")
        pack.rename(destination)
    return dict(pack=str(destination), gameplay_tracks=len(catalogue), screen_frames=len(frames), death_seconds=end / RATE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--assets", type=Path)
    source.add_argument("--tool", type=Path)
    args = parser.parse_args()
    if args.assets:
        result = build(args.game, args.assets, args.output)
    else:
        with tempfile.TemporaryDirectory(prefix="boshy-undertale-import-") as temp:
            script = Path(__file__).with_name("undertale_export.csx")
            subprocess.run([str(args.tool.resolve()), "load", str(local_file(args.game, "data.win")), "-s", str(script)],
                           env={**os.environ, "BOSHY_UNDERTALE_EXPORT": temp}, check=True, timeout=180)
            result = build(args.game, temp, args.output)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
