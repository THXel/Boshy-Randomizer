"""Native Target counts, goal pages, five languages, seed sharing and resume."""

import json, uuid
from menu_host.store import Store
from native_menu.controller import Controller
from native_menu_probe import snapshot, key, capture, pump
from native_menu_options_probe import choose, page
from native_menu_lifecycle_probe import wait_for
from native_cycle_live import check
from gameplay.cycle_plan import initial
from native_targets_live import OUT


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, languages=[], memory_writes=0)
    s = Store(OUT / ("target-menu-" + uuid.uuid4().hex[:6]))
    with s.lock():
        c = Controller(s)
        c.model.draft.update(god_mode=True, no_mouse_ghost=True)
        try:
            c.open()
            c.enter()
            page(c, "route")
            before = c.model.draft.seed
            while c.model.draft.options["mode"] != "target":
                choose(c, "mode", "Right")
            assert c.model.draft.seed != before
            assert all(
                not next(r for r in c.model.rows() if r.key == k).enabled
                for k in ("items",)
            )
            choose(c, "target_count", "Left")
            assert c.model.draft.options["target_count"] == 4
            choose(c, "boss_count", "Right")
            assert c.model.draft.options["boss_count"] == 1
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
                snapshot(c, "target-menu-" + lang)
                page(c, "targets")
                assert len(c.model.rows()) == 5
                snapshot(c, "target-goals-" + lang)
                page(c, "route")
                report["languages"].append(lang)
                assert c.model.draft.shared() == shared
            key(c, "F6")
            assert c.clipboard.get() == shared
            page(c, "route")
            for _ in range(4):
                choose(c, "target_count", "Left")
            for _ in range(2):
                choose(c, "boss_count", "Left")
            assert c.model.draft.options["target_count"] == 19
            assert c.model.draft.options["boss_count"] == 22
            page(c, "targets")
            assert len(c.model.rows()) == 41
            for _ in range(5):
                key(c, "Next")
            assert c.model.offset == 40
            snapshot(c, "target-all-goals-last-page")
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
            assert not p["route"] and config.getint("FusionRouteV4", "Schema") == 4
            snapshot(c, "target-home-saved")
            choose(c, "resume")
            wait_for(c, lambda: bool(s.active))
            pump(c, 0.3)
            report["resumed"] = check(c.runtime, s.folder(1), expected)
            c.runtime.key("F2")
            wait_for(c, lambda: not s.active and c.window.owned())
            report.update(seed_roundtrip=True, goal_pages=True, passed=True)
        except BaseException as e:
            report["error"] = repr(e)
            raise
        finally:
            c.close()
            (OUT / "target-menu-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
