"""One menu-owned music stream, independent of widget rebuilds and save actions."""

import hashlib, json, os, shutil, subprocess, threading, struct
from pathlib import Path
from export_native_run import BASE
from visuals.scenery_pack import App
from music.bank import read
from menu_host.store import atomic

CUE = "Intro Megaman X Infinity Mijinion stage"


def prepare(root):
    root = Path(root) / "audio-cache"
    root.mkdir(parents=True, exist_ok=True)
    app = App(BASE)
    sounds, _ = read(app.payload(0x6668), app.payload(0x5557))
    found = [s for s in sounds.values() if s.name == CUE]
    if len(found) != 1:
        raise ValueError("Menu cue missing")
    audio = found[0].audio
    key = hashlib.sha256(b"menu-pcm-v2-volume25" + audio).hexdigest()
    target = root / (key + ".wav")
    receipt = root / (key + ".json")
    if target.is_file() and receipt.is_file():
        meta = json.loads(receipt.read_text())
        if hashlib.sha256(target.read_bytes()).hexdigest() == meta.get("sha256"):
            return target
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg and os.name == "nt":
        from imageio_ffmpeg import get_ffmpeg_exe

        ffmpeg = get_ffmpeg_exe()
    if not ffmpeg:
        raise RuntimeError("Audio decoder unavailable")
    result = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-i",
            "pipe:0",
            "-f",
            "wav",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-af",
            "volume=0.25",
            "pipe:1",
        ],
        input=audio,
        capture_output=True,
        timeout=30,
    )
    if result.returncode or not result.stdout.startswith(b"RIFF"):
        raise RuntimeError("Menu audio conversion failed")
    raw = bytearray(result.stdout)
    struct.pack_into("<I", raw, 4, len(raw) - 8)
    pos = 12
    while pos + 8 <= len(raw):
        size = struct.unpack_from("<I", raw, pos + 4)[0]
        if raw[pos : pos + 4] == b"data":
            struct.pack_into("<I", raw, pos + 4, len(raw) - pos - 8)
            break
        pos += 8 + size + (size % 2)
    else:
        raise ValueError("PCM data missing")
    atomic(target, bytes(raw))
    atomic(
        receipt,
        (
            json.dumps(dict(cue=CUE, sha256=hashlib.sha256(raw).hexdigest())) + "\n"
        ).encode(),
    )
    return target


class MenuAudio:
    def __init__(self, root, enabled=True):
        self.enabled = enabled
        self.suspended = False
        self.error = ""
        self.process = None
        self.path = None
        self.lock = threading.RLock()
        self.starts = 0
        self.stops = 0
        self.windows_playing = False
        try:
            self.path = prepare(root)
        except Exception as error:
            self.error = str(error)

    def sync(self):
        with self.lock:
            wanted = self.enabled and not self.suspended and self.path is not None
            if not wanted:
                self.stop()
                return
            try:
                if os.name == "nt":
                    if not self.windows_playing:
                        import winsound

                        winsound.PlaySound(
                            str(self.path),
                            winsound.SND_FILENAME
                            | winsound.SND_ASYNC
                            | winsound.SND_LOOP,
                        )
                        self.windows_playing = True
                        self.starts += 1
                elif self.process is None or self.process.poll() is not None:
                    self.process = subprocess.Popen(
                        [
                            "ffplay",
                            "-nodisp",
                            "-loglevel",
                            "error",
                            "-loop",
                            "0",
                            str(self.path),
                        ],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    self.starts += 1
            except Exception as error:
                self.error = str(error)

    def stop(self):
        with self.lock:
            if self.windows_playing:
                import winsound

                winsound.PlaySound(None, 0)
                self.windows_playing = False
                self.stops += 1
            if self.process is not None:
                p = self.process
                self.process = None
                if p.poll() is None:
                    p.terminate()
                    try:
                        p.wait(timeout=2)
                    except subprocess.TimeoutExpired:
                        p.kill()
                        p.wait(timeout=2)
                self.stops += 1

    def suspend(self):
        with self.lock:
            self.suspended = True
            self.stop()

    def resume(self):
        with self.lock:
            self.suspended = False
            self.sync()

    def close(self):
        with self.lock:
            self.enabled = False
            self.stop()
