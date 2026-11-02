"""Native menu input, five-language rendering, seed clipboard and saved intro choice."""

import json
import uuid
from export_route_probe import ROOT
from menu_host.store import Store
from native_menu.controller import Controller
from native_menu_probe import pump, snapshot, key, capture
from native_menu_options_probe import choose, page
from native_menu_lifecycle_probe import wait_for
from native_intro_skip_live import state, reached

OUT = ROOT / "outputs/Fusion-NativeIntroSkip-20261024"


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, memory_writes=0, languages=[])
    store = Store(OUT / ("menu-profile-" + uuid.uuid4().hex[:8]))
    with store.lock():
        c = Controller(store)
        c.model.draft.update(
            level_pool=[],
            level_count=0,
            boss_pool=["hellokitty"],
            route_boss_count=1,
            god_mode=True,
            no_mouse_ghost=True,
        )
        try:
            c.open()
            c.enter()
            page(c, "gameplay")
            before = c.model.draft.seed
            choose(c, "skip_intro")
            assert c.model.draft.options["extras"]["skip_intro"]
            assert c.model.draft.seed != before
            shared = c.model.draft.shared()
            for language in ("de", "en", "es", "ru", "ja"):
                if language != "de":
                    page(c, "settings")
                    choose(c, "language")
                    assert c.model.language == language
                    page(c, "gameplay")
                    # Focus the new option without toggling it.
                    i = next(
                        i
                        for i, row in enumerate(c.model.rows())
                        if row.key == "skip_intro"
                    )
                    while c.model.focus != i:
                        key(c, "Down")
                snapshot(c, "intro-option-" + language)
                assert c.model.draft.shared() == shared
                report["languages"].append(language)
            key(c, "F6")
            assert c.clipboard.get() == shared
            key(c, "F5")
            assert c.model.draft.shared() != shared
            key(c, "F7")
            assert c.model.draft.shared() == shared
            report["seed_roundtrip"] = True
            page(c, "home")
            choose(c, "new")
            wait_for(c, lambda: bool(store.active))
            pump(c, 0.5)
            report["initial"] = state(c.runtime, "hellokitty")
            assert reached("hellokitty", report["initial"], 0, 1499)
            c.runtime.key("F2")
            wait_for(c, lambda: not store.active and c.window.owned())
            folder, plan, save = store.resume(1)
            assert plan["gameplay_settings"]["SkipIntro"] == 1
            assert save.getint("FusionGameplayV1", "SkipIntro") == 1
            assert c.model.draft.shared() == shared
            choose(c, "resume")
            wait_for(c, lambda: bool(store.active))
            pump(c, 0.5)
            report["resumed"] = state(c.runtime, "hellokitty")
            assert reached("hellokitty", report["resumed"], 0, 1499)
            c.runtime.key("F2")
            wait_for(c, lambda: not store.active and c.window.owned())
            report["F2_resume"] = True
            report["passed"] = True
        except BaseException as error:
            report["error"] = repr(error)
            raise
        finally:
            c.close()
            (OUT / "menu-live-results.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
