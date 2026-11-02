"""Actual deaths, respawns, mirror controls and three-slot isolation in one process."""

import json, uuid, subprocess
from functools import partial
from PIL import Image
import numpy as np
from export_route_probe import ROOT
from export_native_run import export
from menu_host.store import Store, save, digest
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu_probe import key, pump
from native_menu_lifecycle_probe import wait_for
from native_menu.observe import objects
from gameplay import native_extras as ex
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-NativeExtras-20261025"


def alive(c):
    return any(o["name"] == "Player" for o in objects(c.window.reader))


def state(c):
    return save(c.folder / "onlineLicense.ini")


def observe(c):
    p = state(c)
    return dict(
        character=p.get("License", "CharacterName"),
        counter=p.getint(ex.STATE, "Sequence", fallback=0),
        rng=p.getint(ex.STATE, "Rng", fallback=0),
        sprites=[
            o["name"] for o in objects(c.window.reader) if o["name"].startswith("ON")
        ],
    )


def position(c):
    return next(o["x"] for o in objects(c.window.reader) if o["name"] == "Player")


def main():
    capture.OUT = OUT
    report = dict(scope=__doc__, memory_writes=0, cases=[])
    s = Store(
        OUT / ("profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    with s.lock():
        for slot, mode, mirror, cycle in [
            (1, "randomizer", False, True),
            (2, "normal", True, True),
            (3, "randomizer", False, False),
        ]:
            d = Draft()
            d.set_mode(mode)
            d.update(
                level_pool=["save1.ini"],
                level_count=1,
                boss_pool=[],
                route_boss_count=0,
                god_mode=True,
                no_mouse_ghost=True,
                start_character="Kirby",
                death_character=cycle,
                mirror=mirror,
            )
            d.seed = "0000001D"
            s.create(slot, d)
        c = CombinedController(s, dynamic=True)
        try:
            c.open()
            c.enter()
            pump(c, 0.5)
            identity = (c.window.pid, c.window.window)
            for slot, mirror, cycle, target in [
                (1, False, True, False),
                (2, True, True, False),
                (3, False, False, False),
                (3, False, True, True),
            ]:
                if target:
                    s.archive(3)
                    d = Draft()
                    d.set_mode("target")
                    d.update(god_mode=True, no_mouse_ghost=True, death_character=True)
                    d.seed = "0000001D"
                    s.create(3, d)
                    c.model.load_slot()
                    c.preview_signature = None
                    c.refresh_slots()
                    c.mail.publish()
                    pump(c, 0.4)
                while c.model.slot < slot:
                    key(c, "Right")
                    pump(c, 0.2)
                case = dict(
                    slot=slot,
                    mirror=mirror,
                    cycle=cycle,
                    mode=c.model.draft.options["mode"],
                    deaths=[],
                )
                report["cases"].append(case)
                untouched = {
                    i: digest(s.folder(i) / "SaveFile1.ini")
                    for i in (1, 2, 3)
                    if i != slot
                }
                key(c, "Return")
                wait_for(c, lambda: c.phase == "playing")
                pump(c, 0.8)
                capture.snap(
                    c.window,
                    f"slot-{slot}-target-initial" if target else f"slot-{slot}-initial",
                )
                before = position(c)
                subprocess.run(["xdotool", "keydown", "Right"], check=True)
                try:
                    pump(c, 0.3)
                finally:
                    subprocess.run(["xdotool", "keyup", "Right"], check=True)
                after = position(c)
                case["right_key_x_delta"] = after - before
                # The original mirror shader flips the picture, not world coordinates.
                # Native input mapping is preserved; visual direction is reversed.
                assert after > before, (mirror, before, after)
                initial = "Dark Boshy" if target else "Kirby"
                assert state(c).get("License", "CharacterName") == initial
                setup = ex.settings("0000001D", c.model.draft.options["extras"])
                rng = setup["InitialState"]
                previous = initial
                for n in range(1, 4):
                    p = state(c)
                    unlocks = (
                        dict(p["Unlockables"]) if p.has_section("Unlockables") else {}
                    )
                    if cycle:
                        rng = ex.advance(rng)
                        expected = ex.choose(setup, rng, unlocks, previous)
                    else:
                        expected = previous
                    c.window.key("q")
                    pump(c, 0.8)
                    assert not alive(c)
                    p = state(c)
                    assert p.get("License", "CharacterName") == expected, (
                        expected,
                        dict(p["License"]),
                    )
                    c.window.key("r")
                    pump(c, 0.8)
                    assert alive(c)
                    result = observe(c)
                    assert result["character"] == expected
                    if cycle:
                        assert result["counter"] == n and result["rng"] == rng, result
                    required = {
                        "Megaman": "ONMegaman",
                        "Bubblun": "ONBob",
                        "Meat Boy": "ONMeat boy",
                        "Kirby": "ONKirby",
                    }.get(expected)
                    if required:
                        assert required in result["sprites"], result
                    capture.snap(
                        c.window,
                        (
                            f"slot-{slot}-target-death-{n}"
                            if target
                            else f"slot-{slot}-death-{n}"
                        ),
                    )
                    case["deaths"].append(result)
                    previous = expected
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu" and not s.active)
                c.enter()
                pump(c, 0.4)
                capture.snap(c.window, f"slot-{slot}-return-menu")
                for i, h in untouched.items():
                    assert digest(s.folder(i) / "SaveFile1.ini") == h
                key(c, "Return")
                wait_for(c, lambda: c.phase == "playing")
                pump(c, 0.8)
                resumed = observe(c)
                assert resumed["character"] == previous
                if cycle:
                    assert resumed["counter"] == 3 and resumed["rng"] == rng
                assert identity == (c.window.pid, c.window.window)
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu" and not s.active)
                c.enter()
                pump(c, 0.4)
                case.update(
                    resumed=resumed,
                    same_process=True,
                    other_slots_unchanged=True,
                    passed=True,
                )
                print("PASS", slot, case, flush=True)
            # Original mirror shader must affect real pixels, not merely the option.
            a = np.array(Image.open(OUT / "slot-1-initial.png").convert("RGB")).astype(
                float
            )
            b = np.array(Image.open(OUT / "slot-2-initial.png").convert("RGB")).astype(
                float
            )
            patch = (slice(250, 470), slice(0, 640))
            direct = float(np.mean(abs(a[patch] - b[patch])))
            flipped = float(np.mean(abs(a[:, ::-1][patch] - b[patch])))
            report["mirror_pixels"] = dict(
                direct_difference=direct, flipped_difference=flipped
            )
            assert flipped < direct * 0.6, report["mirror_pixels"]
            report.update(passed=True, identity=identity)
        except BaseException as error:
            report["error"] = repr(error)
            try:
                capture.snap(c.window, "failure")
            except Exception:
                pass
            raise
        finally:
            try:
                c.close()
            finally:
                (OUT / "live-results.json").write_text(
                    json.dumps(report, indent=2) + "\n"
                )
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
