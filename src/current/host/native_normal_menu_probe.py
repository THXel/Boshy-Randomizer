"""Native Normal-mode input, five-language explanation, seed import and resume."""

import json, uuid
from menu_host.store import Store
from native_menu.controller import Controller
from native_menu_probe import snapshot, key, capture, pump
from native_menu_options_probe import choose, page
from native_menu_lifecycle_probe import wait_for
from native_cycle_live import check
from gameplay.cycle_plan import initial
from native_normal_live import OUT


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, languages=[], memory_writes=0)
    s = Store(OUT / ("normal-menu-" + uuid.uuid4().hex[:6]))
    with s.lock():
        c = Controller(s)
        c.model.draft.update(god_mode=True, no_mouse_ghost=True)
        try:
            c.open()
            c.enter()
            page(c, "route")
            before = c.model.draft.seed
            while c.model.draft.options["mode"] != "normal":
                choose(c, "mode", "Right")
            assert c.model.draft.seed != before
            assert all(
                not next(r for r in c.model.rows() if r.key == k).enabled
                for k in ("level_count", "route_boss_count", "items")
            )
            choose(c, "characters")
            shared = c.model.draft.shared()
            for lang in ("de", "en", "es", "ru", "ja"):
                if lang != "de":
                    page(c, "settings")
                    choose(c, "language")
                    page(c, "route")
                assert c.model.language == lang
                while c.model.focus != 0:
                    key(c, "Up")
                snapshot(c, "normal-menu-" + lang)
                report["languages"].append(lang)
                assert c.model.draft.shared() == shared
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
            expected = initial(c.model.draft.options, c.model.draft.seed)
            report["started"] = check(c.runtime, s.folder(1), expected)
            c.runtime.key("F2")
            wait_for(c, lambda: not s.active and c.window.owned())
            _, p, config = s.resume(1)
            assert not p["route"] and config.getint("FusionRouteV4", "Schema") == 0
            snapshot(c, "normal-home-saved")
            choose(c, "resume")
            wait_for(c, lambda: bool(s.active))
            pump(c, 0.3)
            report["resumed"] = check(c.runtime, s.folder(1), expected)
            c.runtime.key("F2")
            wait_for(c, lambda: not s.active and c.window.owned())
            report.update(seed_roundtrip=True, original_progression=True, passed=True)
        except BaseException as e:
            report["error"] = repr(e)
            raise
        finally:
            c.close()
            (OUT / "normal-menu-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
