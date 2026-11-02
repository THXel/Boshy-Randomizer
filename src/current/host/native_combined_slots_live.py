"""Create/resume/delete all three original save digits through native input."""

import json
import uuid
from native_menu.combined import CombinedController as ClassicController
from export_native_run import export
from functools import partial
from menu_host.store import save
from native_classic_live import OUT as CLASSIC_OUT

OUT = CLASSIC_OUT.parent / "Fusion-CombinedSlots-20261025"
OUT.mkdir(exist_ok=True)
from native_menu_probe import key, pump
from native_classic_live import trigger
from native_menu_lifecycle_probe import wait_for, pulse_inputs
from menu_host.store import Store, digest
from menu_host.processes import games
import god_mode_live as capture


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, slots=[], memory_writes=0)
    store = Store(
        OUT / ("slots-profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, classic=True),
    )
    with store.lock():
        c = ClassicController(store)
        try:
            c.open()
            c.enter()
            identity = (c.window.pid, c.window.window)
            pump(c, 0.5)
            for slot in (1, 2, 3):
                while c.model.slot < slot:
                    key(c, "Right")
                    pump(c, 0.2)
                assert c.model.slot == slot and trigger(c) == [slot - 1, 0]
                c.model.draft.set_mode(("normal", "target", "randomizer")[slot - 1])
                c.model.draft.update(
                    level_pool=["save1.ini"],
                    level_count=1,
                    boss_pool=[],
                    route_boss_count=0,
                    difficulty=slot - 1,
                    start_character=("Mario", "Link", "Yoshi")[slot - 1],
                    characters=True,
                    god_mode=True,
                    no_mouse_ghost=True,
                )
                c.model.draft.seed = ("00000011", "00000022", "00000033")[slot - 1]
                key(c, "Return")
                assert c.model.page == "settings"
                key(c, "Return")
                assert c.operation == "new"
                wait_for(c, lambda: c.phase == "playing")
                pump(c, 0.8)
                assert c.window.reader.frame() == "First World - Prehistorik"
                assert len(games()) == 1
                assert identity == (c.window.pid, c.window.window)
                saved = store.summary(slot)
                before_deaths = save(c.folder / "SaveFile1.ini").getint(
                    "Stats", "Deaths"
                )
                sha = digest(store.folder(slot) / "Boshy.exe")
                c.window.key("q")
                pump(c, 1)
                c.window.key("r")
                pump(c, 0.7)
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu" and not store.active)
                c.enter()
                pump(c, 0.5)
                assert identity == (c.window.pid, c.window.window)
                assert c.model.slot == slot and trigger(c) == [slot - 1, 0], (
                    slot,
                    c.model.slot,
                    trigger(c),
                )
                assert c.model.draft.seed == saved["seed"]
                assert store.summary(slot)["deaths"] > before_deaths
                capture.snap(c.window, "classic-saved-slot-" + str(slot))
                key(c, "Return")
                wait_for(c, lambda: c.phase == "playing")
                pump(c, 0.8)
                assert digest(store.folder(slot) / "Boshy.exe") == sha
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu" and not store.active)
                c.enter()
                pump(c, 0.5)
                assert identity == (c.window.pid, c.window.window)
                assert c.model.slot == slot and trigger(c) == [slot - 1, 0]
                report["slots"].append(
                    dict(
                        slot=slot,
                        created=True,
                        resumed=True,
                        deaths_persist=True,
                        native_selection_preserved=True,
                        same_process=True,
                        mode=c.model.draft.options["mode"],
                        seed=saved["seed"],
                        sha256=sha,
                    )
                )
            for slot in (3, 2, 1):
                while c.model.slot > slot:
                    key(c, "Left")
                    pump(c, 0.2)
                pid, window = c.window.pid, c.window.window
                streams = pulse_inputs(pid)
                key(c, "Delete")
                wait_for(c, lambda: not c.future and not c.model.busy)
                pump(c, 0.5)
                assert store.current(slot) is None
                assert (c.window.pid, c.window.window) == (
                    pid,
                    window,
                ) and c.window.owned()
                after = pulse_inputs(pid)
                assert streams and streams == after, (streams, after)
                report["slots"][slot - 1].update(
                    deleted=True, same_menu_process=True, audio_stream_unchanged=True
                )
                capture.snap(c.window, "classic-deleted-slot-" + str(slot))
            report["events"] = c.events
            report["same_process_identity"] = identity
            report["passed"] = True
        except BaseException as error:
            report["error"] = repr(error)
            try:
                capture.snap(c.window, "classic-slots-failure")
            except Exception:
                pass
            raise
        finally:
            c.close()
            (OUT / "slots-live-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
