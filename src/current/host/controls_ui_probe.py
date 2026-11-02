"""Five-language gameplay controls and real native new/resume/Q/F2 callbacks."""

import json, time, tkinter as tk, traceback
from pathlib import Path
from PIL import Image
from Xlib import display, X
from menu_host.ui import Menu
from menu_host.store import Store, digest
from export_route_probe import ROOT

OUT = ROOT / "outputs/Fusion-Controls-20261024"


def snap(root, name):
    root.update_idletasks()
    d = display.Display()
    w = d.create_resource_object("window", root.winfo_id())
    g = w.get_geometry()
    raw = w.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
    Image.frombytes("RGB", (g.width, g.height), raw.data, "raw", "BGRX").save(
        OUT / (name + ".png")
    )
    d.close()


def main():
    store = Store(OUT / "ui-profile")
    report = {"scope": __doc__, "events": []}
    state = {}
    with store.lock():
        root = tk.Tk()
        m = Menu(root, store)

        def fail(error):
            report["error"] = repr(error)
            report["traceback"] = traceback.format_exc()
            report["passed"] = False
            try:
                snap(root, "ui-failure")
            except Exception:
                pass
            try:
                if store.active:
                    m.runtime.close("ui-probe-failure")
            finally:
                root.destroy()

        def safe(fn):
            def call():
                try:
                    fn()
                except BaseException as e:
                    fail(e)

            return call

        def until(predicate, action, start=None):
            start = start or time.monotonic()
            if time.monotonic() - start > 100:
                raise TimeoutError("UI test wait: " + m.error)
            if m.error:
                raise RuntimeError(m.error)
            if predicate():
                action()
            else:
                root.after(250, safe(lambda: until(predicate, action, start)))

        def setup():
            for lang in ("de", "en", "es", "ru", "ja"):
                m.lang.set(lang)
                m.language_changed()
                m.tabs.select(1)
                root.update()
                snap(root, "menu-" + lang)
                assert (
                    len(m.lists["level_pool"][1]) == 21
                    and len(m.lists["boss_pool"][1]) == 22
                )
            m.lang.set("de")
            m.language_changed()
            for key in ("god_mode", "autofire", "no_mouse_ghost"):
                old = m.draft.seed
                m.widgets[key].invoke()
                assert m.draft.seed != old and m.draft.options["extras"][key]
                report["events"].append(dict(test=key + " checkbox renews seed",passed=True))
            m.draft.update(
                level_pool=["save1.ini"],
                level_count=1,
                boss_pool=["hellokitty"],
                route_boss_count=1,
            )
            m.sync()
            code = m.draft.shared()
            m.shared.set(code)
            m.import_seed()
            assert m.draft.shared() == code
            state["seed"] = m.draft.seed
            m.tabs.select(1)
            snap(root, "menu-ready")
            m.widgets["new"].invoke()
            snap(root, "menu-preparing")
            until(lambda: m.future is None and bool(store.active), playing)

        def playing():
            assert store.summary(1)["seed"] == state["seed"]
            assert m.widgets["new"].instate(["disabled"])
            state["exe"] = digest(store.folder(1) / "Boshy.exe")
            state["deaths"] = store.summary(1)["deaths"]
            report["events"].append(
                dict(test="new-run button launches native God Mode game", passed=True)
            )
            m.runtime.key("q")
            root.after(2200, safe(restart))

        def restart():
            m.runtime.key("r")
            root.after(900, safe(return_f2))

        def return_f2():
            m.runtime.key("F2")
            until(lambda: not store.active and m.future is None, returned)

        def returned():
            saved = store.summary(1)
            assert saved["deaths"] > state["deaths"]
            assert saved["seed"] == state["seed"]
            assert not m.widgets["resume"].instate(["disabled"])
            m.widgets["copy"].invoke()
            assert root.clipboard_get() == m.draft.shared()
            assert all(m.widgets[k].instate(["disabled"]) for k in ("god_mode","autofire","no_mouse_ghost"))
            snap(root, "menu-after-f2")
            report["events"].append(
                dict(
                    test="F2 returns to actual host UI with persisted save",
                    passed=True,
                    save=saved,
                )
            )
            state["resume_deaths"] = saved["deaths"]
            # Recreate runtime and draft to reload the persisted run setting.
            m.runtime = type(m.runtime)(store)
            m.draft = type(m.draft)()
            m.load_selected_settings()
            assert all(m.draft.options["extras"][k] for k in ("god_mode","autofire","no_mouse_ghost"))
            m.widgets["resume"].invoke()
            until(lambda: m.future is None and bool(store.active), resumed)

        def resumed():
            saved = store.summary(1)
            assert saved["deaths"] == state["resume_deaths"]
            assert digest(store.folder(1) / "Boshy.exe") == state["exe"]
            report["events"].append(
                dict(
                    test="resume reloads saved God Mode and preserves native run",
                    passed=True,
                )
            )
            m.widgets["return"].invoke()
            until(lambda: not store.active and m.future is None, clear)

        def clear():
            snap(root, "menu-after-return-button")
            m.widgets["delete"].invoke()
            assert not store.current(1)
            assert not m.widgets["new"].instate(["disabled"])
            report["events"].append(
                dict(test="return and clear-slot buttons", passed=True)
            )
            report["passed"] = True
            snap(root, "menu-slot-cleared")
            m.close()

        root.after(800, safe(setup))
        root.mainloop()
        if store.active:
            m.runtime.close("probe-finally")
        m.executor.shutdown(wait=True)
    (OUT / "ui-results.json").write_text(json.dumps(report, indent=2) + "\n")
    assert report.get("passed"), report
    print(
        "PASS five languages, changed seed, UI new/resume/F2/return/clear", flush=True
    )


if __name__ == "__main__":
    main()
