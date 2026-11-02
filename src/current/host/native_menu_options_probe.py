"""Real native input covers graphics, route controls, rush modes and clipboard."""

import copy, json, uuid
from menu_host.store import Store
from native_menu.controller import Controller
from native_menu_probe import key, pump, capture, snapshot
from export_route_probe import ROOT
from run_settings import decode

OUT = ROOT / "outputs/Fusion-NativeOptions-20261024"
OUT.mkdir(exist_ok=True)
capture.OUT = OUT


def choose(c, name, press="Return"):
    rows = c.model.rows()
    i = next(i for i, row in enumerate(rows) if row.key == name)
    while c.model.focus != i:
        key(c, "Down")
    key(c, press)


def page(c, name):
    while c.model.page != "home":
        key(c, "Escape")
    if name != "home":
        choose(c, "settings")
        if name != "settings":
            choose(c, name)


def main():
    report = {"scope": __doc__, "events": [], "memory_writes": 0}
    store = Store(OUT / ("profile-" + uuid.uuid4().hex[:8]))
    with store.lock():
        c = Controller(store)
        try:
            c.open()
            c.enter()
            pump(c, 0.3)
            page(c, "cosmetics")
            for name in (
                "music",
                "sprite_scenery",
                "sprite_backgrounds",
                "sprite_decor",
                "sprite_tiles",
                "sprite_actors",
            ):
                before = c.model.draft.seed
                old = c.model.draft.options["extras"][name]
                choose(c, name)
                assert c.model.draft.options["extras"][name] is not old
                assert c.model.draft.seed != before
            choose(c, "sprite_dim", "Right")
            assert c.model.draft.options["extras"]["sprite_dim"] == 40
            for expected in (60, 0, 20, 40):
                key(c, "Right")
                assert c.model.draft.options["extras"]["sprite_dim"] == expected
                decode(c.model.draft.shared())
            for expected in (20, 0, 60, 40):
                key(c, "Left")
                assert c.model.draft.options["extras"]["sprite_dim"] == expected
            for name in ("music_pack", "blood_pack"):
                choose(c, name)
                assert getattr(c.model.draft, name) == "kamilia3"
                key(c, "Right")
                assert getattr(c.model.draft, name) == "wannafest22"
                key(c, "Right")
                assert getattr(c.model.draft, name) == "original"
            snapshot(c, "graphics-page2")
            report["events"].append(
                "All graphics toggles, dim wrap in both directions and both pack selectors passed"
            )
            print(report["events"][-1], flush=True)
            # Each catalogue checkbox receives native Enter and restores its value.
            for target in ("levels", "bosses"):
                page(c, target)
                for index, row in enumerate(c.model.rows()):
                    assert c.model.focus == index
                    before = copy.deepcopy(c.model.draft.options)
                    key(c, "Return")
                    key(c, "Return")
                    assert c.model.draft.options == before
                    if index + 1 < len(c.model.rows()):
                        key(c, "Down")
                snapshot(c, target + "-last-page")
            report["events"].append(
                "All 21 level and 22 boss checkboxes operated through native events"
            )
            print(report["events"][-1], flush=True)
            page(c, "route")
            for name in ("level_count", "route_boss_count", "difficulty"):
                before = c.model.draft.options[name]
                choose(c, name, "Right")
                key(c, "Left")
                assert c.model.draft.options[name] == before
            for expected in ("boss_rush", "level_rush", "normal", "target", "randomizer"):
                choose(c, "mode", "Right")
                assert c.model.draft.options["mode"] == expected
                snapshot(c, expected)
            report["events"].append("All route controls and all three run modes passed")
            page(c, "seed")
            original = c.model.draft.shared()
            key(c, "F6")
            assert c.clipboard.get() == original and c.model.message == c.model.t(
                "copied"
            )
            key(c, "F5")
            assert c.model.draft.shared() != original
            key(c, "F7")
            assert c.model.draft.shared() == original
            c.clipboard.put("not-a-shared-seed")
            key(c, "F7")
            assert c.model.draft.shared() == original and c.model.message == c.model.t(
                "invalid_seed"
            )
            snapshot(c, "invalid-seed-de")
            page(c, "settings")
            for language in ("en", "es", "ru", "ja", "de"):
                choose(c, "language")
                assert c.model.language == language
                key(c, "F7")
                assert c.model.message == c.model.t("invalid_seed")
                assert c.model.draft.shared() == original
                snapshot(c, "invalid-seed-" + language)
            c.clipboard.put(original)
            key(c, "F7")
            assert c.model.draft.shared() == original
            report["events"].append(
                "F6 copy, F5 regenerate, F7 restore, invalid import and five-language errors passed"
            )
            report["passed"] = True
        except BaseException as error:
            report["error"] = repr(error)
            try:
                snapshot(c, "failure")
            except Exception:
                pass
            raise
        finally:
            c.close()
            (OUT / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
