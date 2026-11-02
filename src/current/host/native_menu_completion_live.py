"""Real native Options navigation and translated title; no engine-memory writes."""

import json
import time
import uuid
from pathlib import Path
from menu_host.store import Store, digest, save
from native_menu.classic import ClassicController
from native_menu.observe import objects
from native_menu_probe import pump
from native_classic_live import enter_title, trigger, wait
from export_route_probe import ROOT
from build_profiles import PREFIX
from god_mode_boss_probe import values
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-Completion-20261026"


def main():
    exe = PREFIX / "drive_c/BoshyTransitions/Boshy-dynamic-v28.exe"
    report = dict(build=str(exe), sha256=digest(exe), cases=[], memory_writes=0)
    capture.OUT = OUT
    for language in ("de", "ja"):
        store = Store(OUT / ("options-" + language + "-" + uuid.uuid4().hex[:8]))
        with store.lock():
            c = ClassicController(store, base=exe, expected=report["sha256"])
            c.model.language = language
            before = c.model.draft.shared()
            try:
                c.open()
                enter_title(c)
                pump(c, 9)
                if trigger(c)[1] != -1:
                    c.window.key("Return")
                    wait(c, lambda: trigger(c)[1] == -1)
                capture.point(c.window, 600, 110)
                pump(c, 0.4)
                capture.snap(c.window, language + "-title")
                c.window.key("Down")
                pump(c, 0.3)
                c.window.key("Return")
                wait(c, lambda: c.window.reader.frame() == "Options")
                pump(c, 1)
                capture.snap(c.window, language + "-options-top")
                translated = [
                    o
                    for o in objects(c.window.reader)
                    if o["name"].startswith("Translated Options")
                ]
                assert len(translated) >= 29, len(translated)
                from native_menu.options_labels import ROWS, TOGGLES

                states = {}
                for label, selector, display, key, translations in ROWS:
                    if key in TOGGLES:
                        obj = next(
                            o
                            for o in translated
                            if o["name"] == "Translated Options " + str(display)
                        )
                        states[key] = values(c.window.reader, obj, 1)[0]
                assert states["ShowDeaths"] == 1, states
                assert states["BloodEffect"] == 1, states
                assert states["FPS"] == 0, states
                for i in range(15):
                    c.window.key("Down")
                    pump(c, 0.15)
                    if i in (1, 5, 10, 14):
                        capture.snap(c.window, f"{language}-options-{i + 1}")
                c.window.key("Left")
                pump(c, 0.3)
                capture.snap(c.window, language + "-options-toggle")
                death_toggle = next(
                    o
                    for o in objects(c.window.reader)
                    if o["name"] == "Translated Options 1391"
                )
                assert values(c.window.reader, death_toggle, 1)[0] == 0
                c.window.key("Right")
                pump(c, 0.3)
                assert values(c.window.reader, death_toggle, 1)[0] == 1
                assert c.model.draft.shared() == before
                c.window.key("Escape")
                wait(c, lambda: c.window.reader.frame() == "Title Screen")
                c.enter()
                pump(c, 0.3)
                c.model.go("gameplay")
                c.mail.publish()
                pump(c, 0.5)
                capture.point(c.window, 300, 270)
                pump(c, 0.8)
                assert c.model.focus == 1, c.model.focus
                assert c.model.draft.shared() == before
                capture.snap(c.window, language + "-hover")
                c.model.go("updates")
                c.mail.publish()
                pump(c, 0.5)
                capture.snap(c.window, language + "-history")
                assert c.model.draft.shared() == before
                report["cases"].append(
                    dict(
                        language=language,
                        translated_objects=len(translated),
                        initial_toggle_states=states,
                        death_toggle_both_directions=True,
                        scroll_steps=15,
                        seed_unchanged=True,
                        hover_focus=1,
                    )
                )
                print("PASS", language, flush=True)
            except BaseException as error:
                report["error"] = repr(error)
                raise
            finally:
                c.close()
                (OUT / "menu-live-results.json").write_text(
                    json.dumps(report, indent=2) + "\n"
                )
    report["passed"] = True
    (OUT / "menu-live-results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
