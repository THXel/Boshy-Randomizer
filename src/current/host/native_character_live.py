"""Native start-character menu, sprite presence, death/restart and resume; reads only."""

import json, uuid
from export_route_probe import ROOT
from menu_host.store import Store, save
from native_menu.controller import Controller
from native_menu_probe import pump, snapshot, capture
from native_menu_options_probe import choose, page
from native_menu_lifecycle_probe import wait_for
from native_menu.observe import objects

OUT = ROOT / "outputs/Fusion-NativeCharacters-20261024"


def check(c, expected):
    pump(c, 0.5)
    names = [o["name"] for o in objects(c.runtime.reader)]
    assert expected in names, (expected, [n for n in names if n.startswith("ON")])
    return [n for n in names if n.startswith("ON")]


def main():
    OUT.mkdir(exist_ok=True)
    capture.OUT = OUT
    report = {"scope": __doc__, "cases": [], "memory_writes": 0}
    try:
        for character, sprite in (("Dark Boshy", "ONDarkBoshy"), ("Kirby", "ONKirby")):
            store = Store(OUT / ("profile-" + uuid.uuid4().hex[:8]))
            with store.lock():
                c = Controller(store)
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
                    # The choice, including every intermediate value, uses native inputs.
                    while c.model.draft.options["start_character"] != character:
                        choose(c, "start_character", "Left")
                    snapshot(c, character + "-menu")
                    seed = c.model.draft.seed
                    page(c, "home")
                    choose(c, "new")
                    wait_for(c, lambda: bool(store.active))
                    first = check(c, sprite)
                    capture.snap(c.runtime, character + "-game")
                    profile = save(store.folder(1) / "onlineLicense.ini")
                    assert profile.get("License", "CharacterName") == character
                    c.runtime.key("q")
                    pump(c, 1)
                    c.runtime.key("r")
                    restarted = check(c, sprite)
                    c.runtime.key("F2")
                    wait_for(c, lambda: not store.active and c.window.owned())
                    assert c.model.draft.seed == seed
                    assert c.model.draft.options["start_character"] == character
                    choose(c, "resume")
                    wait_for(c, lambda: bool(store.active))
                    resumed = check(c, sprite)
                    report["cases"].append(
                        dict(
                            character=character,
                            seed=seed,
                            first_sprites=first,
                            restarted_sprites=restarted,
                            resumed_sprites=resumed,
                            seed_and_choice_preserved=True,
                        )
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
