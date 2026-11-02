"""Live native lifecycle: create, Q death, F2 return, cold resume and two slots."""

import json, time
from pathlib import Path
from menu_host.store import Store, digest
from menu_host.runtime import Runtime
from menu_host.draft import Draft
from export_route_probe import ROOT
from Xlib import display, X
from PIL import Image

OUT = ROOT / "outputs/Fusion-Menu-20261024"


def snap(runtime, name):
    d = display.Display()
    w = d.create_resource_object("window", int(runtime.window, 16))
    g = w.get_geometry()
    raw = w.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
    Image.frombytes("RGB", (g.width, g.height), raw.data, "raw", "BGRX").save(
        OUT / (name + ".png")
    )
    d.close()


def wait_menu(runtime):
    end = time.monotonic() + 15
    while time.monotonic() < end:
        if runtime.poll() == "menu":
            return
        time.sleep(0.2)
    raise AssertionError("F2 did not return to host")


def main():
    store = Store(OUT / "live-profile")
    report = {"scope": __doc__, "events": []}
    with store.lock():
        draft = Draft()
        draft.update(
            level_pool=["save1.ini"],
            level_count=1,
            boss_pool=["hellokitty"],
            route_boss_count=1,
        )
        if store.current(1):
            raise RuntimeError("Use a fresh test profile")
        store.create(1, draft)
        runtime = Runtime(store)
        try:
            frame = runtime.start(1)
            assert frame == "First World - Prehistorik", frame
            snap(runtime, "first-start")
            before = store.summary(1)
            runtime.key("q")
            time.sleep(2)
            snap(runtime, "death")
            runtime.key("r")
            time.sleep(1)
            runtime.key("F2")
            wait_menu(runtime)
            saved = store.summary(1)
            assert saved["deaths"] > before["deaths"], (before, saved)
            report["events"].append(
                dict(test="Q death and F2", passed=True, before=before, after=saved)
            )
            report["first_session"] = runtime.events
            # New host/store object, same disk data: no seed export on resume.
        finally:
            if store.active:
                runtime.close("probe-cleanup")
    store = Store(OUT / "live-profile")
    with store.lock():
        runtime = Runtime(store)
        try:
            before = store.summary(1)
            exe = digest(store.folder(1) / "Boshy.exe")
            frame = runtime.start(1)
            assert frame == "First World - Prehistorik"
            resumed = store.summary(1)
            assert (resumed["seed"], resumed["spot"], resumed["deaths"]) == (
                before["seed"],
                before["spot"],
                before["deaths"],
            )
            snap(runtime, "cold-resume")
            runtime.key("F2")
            wait_menu(runtime)
            assert digest(store.folder(1) / "Boshy.exe") == exe
            report["events"].append(
                dict(
                    test="cold resume",
                    passed=True,
                    before=before,
                    after=store.summary(1),
                )
            )
            untouched = (store.folder(1) / "SaveFile1.ini").read_bytes()
            draft = Draft()
            draft.update(
                level_pool=["save7.ini"],
                level_count=1,
                boss_pool=[],
                route_boss_count=0,
                music=True,
            )
            draft.select_pack("music_pack", "kamilia3")
            draft.select_pack("blood_pack", "wannafest22")
            store.create(2, draft)
            frame = runtime.start(2)
            snap(runtime, "second-slot")
            runtime.key("F2")
            wait_menu(runtime)
            assert (store.folder(1) / "SaveFile1.ini").read_bytes() == untouched
            assert store.summary(1)["seed"] != store.summary(2)["seed"]
            report["events"].append(
                dict(
                    test="second slot, other native audio/blood build",
                    passed=True,
                    frame=frame,
                    save=store.summary(2),
                )
            )
            other = (store.folder(2) / "SaveFile1.ini").read_bytes()
            store.archive(1)
            assert (
                not store.current(1)
                and (store.folder(2) / "SaveFile1.ini").read_bytes() == other
            )
            report["events"].append(dict(test="clear one slot", passed=True))
        finally:
            if store.active:
                runtime.close("probe-cleanup")
    report["passed"] = True
    (OUT / "lifecycle.json").write_text(json.dumps(report, indent=2) + "\n")
    print(
        "PASS create, native Q/F2, cold resume, separate second slot, clear slot",
        flush=True,
    )


if __name__ == "__main__":
    main()
