"""Exercise restored menu pages via native keyboard and mouse events."""

import json
import subprocess
import uuid
from native_menu.classic import ClassicController
from native_menu_probe import key, pump, snapshot
from native_classic_live import wait
from menu_host.store import Store
from export_route_probe import ROOT
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-MenuParity-20261025"


def select(c, row):
    rows = c.model.rows()
    index = next(i for i, r in enumerate(rows) if r.key == row)
    for _ in range((index - c.model.focus) % len(rows)):
        key(c, "Down")
    key(c, "Return")


def main():
    OUT.mkdir(exist_ok=True)
    capture.OUT = OUT
    report = dict(scope=__doc__, memory_writes=0)
    store = Store(OUT / ("profile-" + uuid.uuid4().hex[:8]))
    with store.lock():
        c = ClassicController(store)
        try:
            c.open()
            c.enter()
            pump(c, 0.3)
            key(c, "Return")
            select(c, "gameplay")
            select(c, "start_character")
            assert c.model.page == "character_picker"
            seed = c.model.draft.seed
            key(c, "Right")
            assert c.model.draft.seed == seed
            snapshot(c, "character-picker-first")
            subprocess.run(
                [
                    "xdotool",
                    "mousemove",
                    "--window",
                    c.window.window,
                    "360",
                    "275",
                    "click",
                    "1",
                ],
                check=True,
            )
            wait(c, lambda: c.model.page == "gameplay")
            assert c.model.draft.options["start_character"] == "Boshy"
            assert c.model.draft.seed != seed
            select(c, "start_character")
            key(c, "Next")
            assert c.model.offset == 8
            for lang in ("de", "en", "es", "ru", "ja"):
                c.model.language = lang
                c.mail.publish()
                pump(c, 0.2)
                snapshot(c, "portraits-" + lang)
            key(c, "Escape")
            key(c, "Escape")
            select(c, "preview")
            seed = c.model.draft.seed
            snapshot(c, "route-preview")
            key(c, "Next")
            snapshot(c, "route-preview-second")
            key(c, "Return")
            assert c.model.draft.seed == seed
            key(c, "Escape")
            select(c, "presets")
            snapshot(c, "presets")
            select(c, "preset:training")
            assert c.model.page == "settings"
            assert c.model.draft.options["extras"]["god_mode"]
            assert c.model.draft.options["extras"]["one_hp"]
            assert c.model.draft.seed != seed
            select(c, "gameplay")
            snapshot(c, "training-settings")
            report.update(
                portrait_mouse_selection=True,
                portrait_keyboard_navigation=True,
                languages=["de", "en", "es", "ru", "ja"],
                preview_seed_unchanged=True,
                training_preset_applied=True,
                passed=True,
            )
        except BaseException as e:
            report["error"] = repr(e)
            try:
                capture.snap(c.window, "failure")
            except Exception:
                pass
            raise
        finally:
            c.close()
            (OUT / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
