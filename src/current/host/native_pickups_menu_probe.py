"""Native pickup toggles, five-language help, seed roundtrip and saved-run locking."""

import json, uuid
from menu_host.store import Store
from native_menu.controller import Controller
from native_menu_probe import snapshot, key, capture, pump
from native_menu_options_probe import choose, page
from native_menu_lifecycle_probe import wait_for
from export_route_probe import ROOT

OUT = ROOT / "outputs/Fusion-NativePickups-20261024"


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
            page(c, "gameplay")
            assert (
                c.model.draft.options["extras"]["quiet_pickups"]
                and not c.model.draft.options["extras"]["fast_chests"]
            )
            seed = c.model.draft.seed
            choose(c, "fast_chests")
            assert c.model.draft.seed != seed
            seed = c.model.draft.seed
            choose(c, "quiet_pickups")
            assert (
                c.model.draft.seed != seed
                and not c.model.draft.options["extras"]["quiet_pickups"]
            )
            choose(c, "quiet_pickups")
            shared = c.model.draft.shared()
            for lang in ("de", "en", "es", "ru", "ja"):
                if lang != "de":
                    page(c, "settings")
                    choose(c, "language")
                    page(c, "gameplay")
                assert c.model.language == lang
                for option in ("fast_chests", "quiet_pickups"):
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
            assert (
                p["gameplay_settings"]["FastChests"]
                == p["gameplay_settings"]["QuietPickups"]
                == 1
            )
            assert (
                save.getint("FusionGameplayV1", "FastChests")
                == save.getint("FusionGameplayV1", "QuietPickups")
                == 1
            )
            page(c, "gameplay")
            assert all(not row.enabled for row in c.model.rows())
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
