"""Private native shot tests: ordinary keys, read-only profiles, no memory writes."""

import argparse
import json
import subprocess
import struct
import uuid
from functools import partial
from pathlib import Path
from native_menu import builds
from menu_host.store import digest


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--exe", type=Path, required=True)
    ap.add_argument(
        "--modes",
        nargs="+",
        default=["random_interval", "death", "spot", "death_and_spot", "off"],
    )
    ap.add_argument("--auto-first", action="store_true")
    args = ap.parse_args()
    builds.DYNAMIC_BASE = args.exe
    builds.DYNAMIC_SHA = digest(args.exe)
    builds.DYNAMIC_SHOTS = True
    from export_native_run import export
    from export_route_probe import ROOT
    from menu_host.store import Store, save
    from menu_host.draft import Draft
    from native_menu.combined import CombinedController
    from native_menu_probe import pump, snapshot as menu_snapshot
    from native_menu_lifecycle_probe import wait_for
    from menu_host.processes import games
    from gameplay.shot_plan import STATE
    from native_menu.observe import objects
    from visuals.scenery_pack import App, object_mapping
    from visuals.fusion25 import property_bank, animation_slot, image_bank
    import recover_boshy_classic as original
    import god_mode_live as capture
    import native_death_visual_probe as screenshots

    out = ROOT / "outputs/Fusion-Shots-20261025"
    capture.OUT = screenshots.OUT = out
    app = App(args.exe)
    mapping = object_mapping(
        app, list(original.routes.objects.values()), active_only=True
    )
    body = property_bank(app.payload(0x2256), app.payload(0x2257))[mapping[106]]
    expected_images = [
        struct.unpack_from("<H", body, animation_slot(body, 0, 0, f))[0]
        for f in range(36)
    ]
    images, _ = image_bank(app.payload(0x6666), app.payload(0x5555))
    expected_sizes = [images[handle].size for handle in expected_images]
    del app, body, images
    report = dict(scope=__doc__, sha256=builds.DYNAMIC_SHA, memory_writes=0, cases=[])

    def state(c):
        p = save(c.folder / "onlineLicense.ini")
        return dict(p[STATE]) if p.has_section(STATE) else None

    for batch in range(0, len(args.modes), 3):
        store = Store(
            out / ("profile-" + uuid.uuid4().hex[:8]),
            exporter=partial(export, dynamic=True),
        )
        with store.lock():
            modes = args.modes[batch : batch + 3]
            for slot, mode in enumerate(modes, 1):
                d = Draft()
                d.set_mode("boss_rush")
                d.update(
                    boss_pool=["hellokitty"],
                    route_boss_count=1,
                    god_mode=True,
                    no_mouse_ghost=True,
                    autofire=True,
                    skip_intro=True,
                    start_character="Auto"
                    if args.auto_first and batch == 0 and slot == 1
                    else "Boshy",
                    characters=not (args.auto_first and batch == 0 and slot == 1),
                    shot_mode=mode,
                    shot_interval_seconds=2,
                    sprite_scenery=True,
                    sprite_backgrounds=True,
                    sprite_decor=True,
                    sprite_tiles=True,
                    sprite_actors=True,
                )
                d.seed = "SHOTS025"
                store.create(slot, d)
            c = CombinedController(store, dynamic=True)
            try:
                c.open()
                c.enter()
                pid = c.window.pid
                c.model.go("shots")
                c.mail.publish()
                pump(c, 0.5)
                for language in ("de", "en", "es", "ru", "ja"):
                    c.model.language = language
                    c.mail.publish()
                    menu_snapshot(c, "shots-menu-" + language)
                c.model.go("home")
                c.mail.publish()
                for slot, mode in enumerate(modes, 1):
                    case = dict(
                        mode=mode, slot=slot, profile=str(store.root), samples=[]
                    )
                    report["cases"].append(case)
                    c.model.slot = slot
                    c.model.load_slot()
                    case["start_character"] = c.model.draft.options["start_character"]
                    case["character_cycle"] = c.model.draft.options["characters"]
                    c.begin()
                    wait_for(c, lambda: c.phase == "playing", seconds=35)
                    pump(c, 0.5)
                    assert c.window.pid == pid and len(games()) == 1
                    case["entry"] = state(c)
                    if mode != "off":
                        profile_path = c.folder / "onlineLicense.ini"
                        stamps = []
                        for _ in range(20):
                            stamps.append(profile_path.stat().st_mtime_ns)
                            pump(c, 0.1)
                        case["profile_write_observation"] = {
                            "seconds": 2,
                            "samples": 20,
                            "distinct_timestamps": len(set(stamps)),
                        }

                    # Shoot through native autofire without altering boss health.
                    subprocess.run(["xdotool", "keydown", "x"], check=True)
                    try:
                        for i in range(6):
                            pump(c, 1.05)
                            st = state(c)
                            case["samples"].append(st)
                            if st is not None:
                                shots = [
                                    o
                                    for o in objects(c.window.reader)
                                    if o["name"] == "Bullet 2"
                                    and o["oi"] == mapping[106]
                                ]
                                # Runtime image IDs are renumbered by the engine.
                                # Check rendered geometry against original artwork;
                                # already-fired bullets retain their creation style.
                                actual = [(o["w"], o["h"]) for o in shots]
                                same_state = state(c)["frame"] == st["frame"]
                                if actual and same_state:
                                    expected = expected_sizes[int(st["frame"])]
                                    case.setdefault("rendered_projectiles", []).append(
                                        dict(
                                            frame=int(st["frame"]),
                                            expected_size=expected,
                                            actual_sizes=actual,
                                            current_style_visible=expected in actual,
                                        )
                                    )
                                    if mode != "random_interval":
                                        assert set(actual) == {expected}, (
                                            st,
                                            actual,
                                            expected,
                                        )
                            if i in (0, 2, 4):
                                screenshots.snapshot(c, mode + f"-shots-{i}")
                    finally:
                        subprocess.run(["xdotool", "keyup", "x"], check=True)
                    if mode != "off":
                        assert case.get("rendered_projectiles"), (
                            "No rendered projectiles verified"
                        )
                        assert any(
                            r["current_style_visible"]
                            for r in case["rendered_projectiles"]
                        )
                    if mode == "random_interval":
                        assert len({s["frame"] for s in case["samples"]}) >= 3, case[
                            "samples"
                        ]
                        assert int(case["samples"][-1]["sequence"]) > int(
                            case["entry"]["sequence"]
                        )
                    elif mode != "off":
                        assert all(
                            s["sequence"] == case["entry"]["sequence"]
                            for s in case["samples"]
                        )
                    before = state(c)
                    c.window.key("q")
                    pump(c, 0.65)
                    assert not any(
                        o["name"] == "Player" for o in objects(c.window.reader)
                    )
                    dead = state(c)
                    if mode != "off":
                        expected = int(before["sequence"]) + int(
                            mode in ("death", "death_and_spot")
                        )
                        if mode != "random_interval":
                            assert int(dead["sequence"]) == expected, (
                                mode,
                                before,
                                dead,
                            )
                    pump(c, 2.2)
                    assert state(c) == dead, "Cycle continued on Game Over"
                    case["death"] = dead
                    screenshots.snapshot(c, mode + "-death")
                    c.window.key("r")
                    pump(c, 0.45)
                    assert any(o["name"] == "Player" for o in objects(c.window.reader))
                    after = state(c)
                    if mode not in ("off", "random_interval"):
                        assert after["sequence"] == dead["sequence"], (
                            "Retry added a second change"
                        )
                    case["retry"] = after
                    c.window.key("F2")
                    wait_for(c, lambda: c.phase == "menu", seconds=30)
                    c.enter()
                    store.resume(slot)
                    saved = save(store.folder(slot) / "onlineLicense.ini")
                    case["saved"] = (
                        dict(saved[STATE]) if saved.has_section(STATE) else None
                    )
                    pump(c, 2.1)
                    c.model.slot = slot
                    c.model.load_slot()
                    c.begin()
                    wait_for(c, lambda: c.phase == "playing", seconds=35)
                    pump(c, 0.2)
                    resumed = state(c)
                    if mode != "off":
                        for key in ("frame", "sequence", "rng"):
                            assert resumed[key] == case["saved"][key], (
                                "Resume changed",
                                mode,
                                key,
                                resumed,
                                case["saved"],
                            )
                    case["resumed"] = resumed
                    c.window.key("F2")
                    wait_for(c, lambda: c.phase == "menu", seconds=30)
                    c.enter()
                    store.resume(slot)
                    case["passed"] = True
                    print("PASS", mode, case["entry"], case["death"], flush=True)
            except BaseException as error:
                report["error"] = repr(error)
                try:
                    screenshots.snapshot(c, "shots-failure")
                except Exception:
                    pass
                raise
            finally:
                subprocess.run(["xdotool", "keyup", "x", "Left", "Right"], check=False)
                c.close()
                (out / "live-results.json").write_text(
                    json.dumps(report, indent=2) + "\n"
                )
    report["passed"] = True
    (out / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
