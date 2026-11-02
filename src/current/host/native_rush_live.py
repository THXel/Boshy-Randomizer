"""Native mode selection, real exports, death/restart, F2 and resume for both rushes."""

import copy, json, uuid
from export_route_probe import ROOT
from menu_host.store import Store, digest
from menu_host.processes import games
from native_menu.controller import Controller
from native_menu_probe import pump, snapshot, capture
from native_menu_options_probe import choose, page
from native_menu_lifecycle_probe import wait_for

OUT = ROOT / "outputs/Fusion-NativeRush-20261024"


def main():
    OUT.mkdir(exist_ok=True)
    capture.OUT = OUT
    report = {"scope": __doc__, "memory_writes": 0, "cases": []}
    try:
        for mode, frame in (
            ("boss_rush", "First Boss - Hello Kitty"),
            ("level_rush", "First World - Prehistorik"),
        ):
            store = Store(OUT / (mode + "-" + uuid.uuid4().hex[:8]))
            with store.lock():
                c = Controller(store)
                c.model.draft.update(
                    level_pool=["save1.ini"],
                    level_count=1,
                    boss_pool=["hellokitty"],
                    route_boss_count=1,
                    god_mode=True,
                    no_mouse_ghost=True,
                )
                try:
                    c.open()
                    c.enter()
                    page(c, "route")
                    while c.model.draft.options["mode"] != mode:
                        choose(c, "mode", "Right")
                    snapshot(c, mode + "-menu")
                    seed = c.model.draft.seed
                    options = copy.deepcopy(c.model.draft.options)
                    page(c, "home")
                    choose(c, "new")
                    wait_for(c, lambda: bool(store.active))
                    assert c.runtime.reader.frame() == frame
                    assert len(games()) == 1, games()
                    plan = json.loads((store.folder(1) / "plan.json").read_text())
                    assert plan["options"] == options and plan["seed"] == seed
                    exe = digest(store.folder(1) / "Boshy.exe")
                    pump(c, 0.3)
                    capture.snap(c.runtime, mode + "-started")
                    before = store.summary(1)
                    c.runtime.key("q")
                    pump(c, 1)
                    c.runtime.key("r")
                    pump(c, 1)
                    c.runtime.key("F2")
                    wait_for(c, lambda: not store.active and c.window.owned())
                    assert (
                        c.model.draft.options == options and c.model.draft.seed == seed
                    )
                    assert store.summary(1)["deaths"] > before["deaths"]
                    choose(c, "resume")
                    wait_for(c, lambda: bool(store.active))
                    assert c.runtime.reader.frame() == frame
                    assert digest(store.folder(1) / "Boshy.exe") == exe
                    assert len(games()) == 1
                    c.runtime.key("F2")
                    wait_for(c, lambda: not store.active and c.window.owned())
                    assert (
                        c.model.draft.options == options and c.model.draft.seed == seed
                    )
                    snapshot(c, mode + "-resumed-return")
                    report["cases"].append(
                        {
                            "mode": mode,
                            "route": plan["route"],
                            "start_frame": frame,
                            "seed": seed,
                            "game_sha256": exe,
                            "death_restart": True,
                            "resume_same_export": True,
                            "settings_preserved": True,
                            "full_route_playthrough": False,
                        }
                    )
                    print(json.dumps(report["cases"][-1]), flush=True)
                finally:
                    c.close()
        report["passed"] = True
    except BaseException as error:
        report["error"] = repr(error)
        raise
    finally:
        (OUT / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
