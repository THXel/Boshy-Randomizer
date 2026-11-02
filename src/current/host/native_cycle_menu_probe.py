"""Character cycle menu toggle, five-language help, seed roundtrip and saved-run locking."""

import json, uuid
from menu_host.store import Store
from native_menu.controller import Controller
from native_menu_probe import snapshot, key, capture, pump
from native_menu_options_probe import choose, page
from native_menu_lifecycle_probe import wait_for
from export_route_probe import ROOT

OUT = ROOT / "outputs/Fusion-NativeCycle-20261025"


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, languages=[], memory_writes=0)
    s = Store(OUT / ("menu-profile-" + uuid.uuid4().hex[:8]))
    with s.lock():
        c = Controller(s)
        c.model.draft.update(
            level_pool=["save1.ini"],
            level_count=1,
            boss_pool=[],
            route_boss_count=0,
            god_mode=True,
            no_mouse_ghost=True,
        )
        try:
            c.open()
            c.enter()
            page(c, "route")
            assert not c.model.draft.options["characters"]
            seed = c.model.draft.seed
            choose(c, "characters")
            assert c.model.draft.seed != seed and c.model.draft.options["characters"]
            shared = c.model.draft.shared()
            for lang in ("de", "en", "es", "ru", "ja"):
                if lang != "de":
                    page(c, "settings")
                    choose(c, "language")
                    page(c, "route")
                assert c.model.language == lang
                for option in ("characters",):
                    i = next(
                        i for i, row in enumerate(c.model.rows()) if row.key == option
                    )
                    while c.model.focus != i:
                        key(c, "Down")
                    snapshot(c, option + "-" + lang)
                assert c.model.draft.shared() == shared
                report["languages"].append(lang)
            key(c, "F6")
            assert c.clipboard.get() == shared
            key(c, "F5")
            assert c.model.draft.shared() != shared
            key(c, "F7")
            assert c.model.draft.shared() == shared
            page(c, "home")
            choose(c, "new")
            wait_for(c, lambda: bool(s.active))
            pump(c, 0.3)
            c.runtime.key("F2")
            wait_for(c, lambda: not s.active and c.window.owned())
            _, p, save = s.resume(1)
            from gameplay.cycle_plan import initial, GROUP, validate
            from menu_host.store import save as read_save
            from native_cycle_live import check

            expected = initial(p["options"], p["seed"])
            assert p["start_character"] == expected
            assert save.getint(GROUP, "Enabled") == 1
            validate(p, save, read_save(s.folder(1) / "onlineLicense.ini"))
            choose(c, "resume")
            wait_for(c, lambda: bool(s.active))
            pump(c, 0.4)
            report["auto_start"] = check(c.runtime, s.folder(1), expected)
            c.runtime.key("F2")
            wait_for(c, lambda: not s.active and c.window.owned())
            page(c, "route")
            assert not next(
                row for row in c.model.rows() if row.key == "characters"
            ).enabled
            assert c.model.draft.shared() == shared
            report.update(
                defaults=True,
                seed_roundtrip=True,
                saved_rules=True,
                locked=True,
                passed=True,
            )
        except BaseException as e:
            report["error"] = repr(e)
            raise
        finally:
            c.close()
            (OUT / "menu-live-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
