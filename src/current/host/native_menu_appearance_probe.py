"""Real native-menu art, mouse controls, animation resource use and localization."""

import copy
import json
import struct
import subprocess
import time
import uuid
from pathlib import Path
from export_route_probe import ROOT
from menu_host.store import Store
from native_menu.controller import Controller, BASE_SHA256
from native_menu import layout
from native_menu.observe import objects
from native_menu_probe import pump, snapshot, capture
from native_menu_options_probe import choose, page
from native_menu_lifecycle_probe import pulse_inputs

OUT = ROOT / "outputs/Fusion-MenuAppearance-20261024"


def rss(pid):
    values = dict(
        line.split(":", 1)
        for line in Path(f"/proc/{pid}/status").read_text().splitlines()
        if ":" in line
    )
    return int(values["VmRSS"].split()[0])


def click(c, x, y):
    seq = c.mail.sequence
    subprocess.run(["wmctrl", "-ia", c.window.window], check=True)
    subprocess.run(
        [
            "xdotool",
            "mousemove",
            "--window",
            c.window.window,
            str(x),
            str(y),
            "click",
            "1",
        ],
        check=True,
    )
    end = time.monotonic() + 4
    while time.monotonic() < end:
        c.tick()
        if c.mail.sequence > seq:
            return
        time.sleep(0.03)
    raise AssertionError("No native click")


def row_click(c, index):
    x, y, r, b = layout.row_rect(c.model.page, index)
    click(c, (x + r) // 2, (y + b) // 2)


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, menu_sha256=BASE_SHA256, memory_writes=0)
    store = Store(OUT / ("live-profile-" + uuid.uuid4().hex[:8]))
    with store.lock():
        c = Controller(store)
        try:
            c.open()
            c.enter()
            pump(c, 2)
            snapshot(c, "native-home")
            seed = c.model.draft.seed
            opts = copy.deepcopy(c.model.draft.options)
            report["initial_seed"] = seed
            report["theme"] = c.renderer.art[1][c.renderer.theme][0]
            report["cast"] = c.renderer.cast
            frame_samples = []
            for n in range(6):
                frames = {}
                for obj in objects(c.window.reader):
                    if obj["name"].startswith("Randomizer Cast"):
                        # Verified Fusion rAni is immediately before rSpr/rVal.
                        fields = struct.unpack(
                            "<20i",
                            c.window.reader.read(obj["ptr"] + obj["rel"] - 116, 80),
                        )
                        assert fields[18] == 8
                        frames[obj["name"]] = fields[17]
                assert len(frames) == 3
                frame_samples.append(frames)
                capture.snap(c.window, f"native-animation-{n}")
                pump(c, 0.17 + n * 0.013)
            assert all(
                len({s[name] for s in frame_samples}) > 1 for name in frame_samples[0]
            )
            report["native_animation_frames"] = frame_samples
            streams = pulse_inputs(c.window.pid)
            generation = c.mail.generation
            panel = (c.folder / "native-panel.png").read_bytes()
            samples = []
            for i in range(5):
                pump(c, 8)
                samples.append(rss(c.window.pid))
                print(
                    json.dumps(
                        dict(
                            animation_seconds=(i + 1) * 8,
                            rss_kib=samples[-1],
                            generation=c.mail.generation,
                        )
                    ),
                    flush=True,
                )
            assert c.model.draft.seed == seed and c.model.draft.options == opts
            assert c.mail.generation == generation
            assert (c.folder / "native-panel.png").read_bytes() == panel
            report["native_animation_without_panel_reload"] = True
            report["animation_rss_kib"] = samples
            report["animation_peak_growth_kib"] = max(samples) - samples[0]
            assert max(samples) - samples[0] < 16384, samples
            assert streams and pulse_inputs(c.window.pid) == streams
            report["same_audio_stream_during_animation"] = True
            row_click(c, 1)
            assert c.model.slot == 2
            row_click(c, 2)
            assert c.model.slot == 3
            row_click(c, 6)
            assert c.model.page == "settings"
            row_click(c, 3)
            assert c.model.page == "gameplay"
            row_click(c, 0)
            assert c.model.draft.options["extras"]["god_mode"]
            snapshot(c, "native-gameplay")
            click(c, 230, 220)
            assert c.model.page == "settings"
            row_click(c, 4)
            assert c.model.page == "cosmetics"
            click(c, 600, 220)
            assert c.model.offset == 8
            row_click(c, 0)
            assert c.model.draft.blood_pack == "kamilia3"
            snapshot(c, "native-graphics-page2")
            report["mouse_save_slots_settings_gameplay_paging"] = True
            for language in ("de", "en", "es", "ru", "ja"):
                page(c, "settings")
                while c.model.language != language:
                    choose(c, "language")
                page(c, "home")
                snapshot(c, "native-home-" + language)
                page(c, "gameplay")
                snapshot(c, "native-gameplay-" + language)
            report["languages"] = ["de", "en", "es", "ru", "ja"]
            report["passed"] = True
        except BaseException as e:
            report["error"] = repr(e)
            if c.window.owned():
                capture.snap(c.window, "appearance-failure")
            raise
        finally:
            c.close()
            (OUT / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
