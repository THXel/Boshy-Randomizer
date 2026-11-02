"""Real Fusion -> local feed -> PinguLexa -> existing OBS source checks."""

import json
import subprocess
import time
import uuid
import urllib.request
from functools import partial
from export_route_probe import ROOT
from export_native_run import export
from menu_host.store import Store
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu_probe import pump, snapshot as menu_snapshot
from native_menu_lifecycle_probe import wait_for
from native_menu.observe import objects
from god_mode_boss_probe import values
from tracker.publisher import feed_path
from native_menu import builds
import god_mode_live as capture
import native_death_visual_probe as screenshots

OUT = ROOT / "outputs/Fusion-Tracker-20261025"


def status():
    return json.load(
        urllib.request.urlopen("http://127.0.0.1:8801/boshy/status", timeout=4)
    )["state"]


def current(c):
    c.tracker.tick(c, force=True)
    return status()


def main():
    capture.OUT = screenshots.OUT = OUT
    report = dict(
        build_sha256=builds.DYNAMIC_SHA, memory_writes=0, cases=[], prelaunch=status()
    )
    store = Store(
        OUT / ("profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    with store.lock():
        d = Draft()
        d.set_mode("normal")
        d.update(no_mouse_ghost=True, start_character="Auto", characters=False)
        d.seed = "TRACKERNORMAL"
        store.create(1, d)
        d = Draft()
        d.set_mode("boss_rush")
        d.update(
            boss_pool=["hellokitty"],
            route_boss_count=1,
            god_mode=True,
            one_hp=True,
            autofire=True,
            skip_intro=True,
            no_mouse_ghost=True,
        )
        d.seed = "TRACKERBOSS"
        store.create(2, d)
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            pump(c, 1)
            menu = current(c)
            assert menu["native_tracker"]["mode"] == "menu", menu
            report["menu"] = menu
            c.model.slot = 3
            c.model.load_slot()
            c.model.go("presets")
            c.mail.publish()
            for lang in ("de", "en", "es", "ru", "ja"):
                c.model.language = lang
                c.mail.publish()
                menu_snapshot(c, "chaos-menu-" + lang)
            c.model.language = "de"
            c.model.focus = next(
                i for i, r in enumerate(c.model.rows()) if r.key == "preset:chaos"
            )
            before = c.model.draft.seed
            c.mail.publish()
            pump(c, 0.3)
            c.window.key("Return")
            pump(c, 1)
            assert c.model.draft.seed != before
            assert c.model.draft.options["extras"]["shot_mode"] == "death_and_spot"
            assert c.model.draft.options["characters"]
            report["chaos_native_menu"] = True
            for slot in (1, 2):
                c.model.slot = slot
                c.model.load_slot()
                c.begin()
                wait_for(c, lambda: c.phase == "playing", seconds=35)
                pump(c, 2)
                entry = current(c)
                assert entry.get("native_tracker"), entry
                assert (
                    entry["native_tracker"]["slot"] == slot
                    and entry["lss_path"] == ""
                    and entry["personal_bests"] == {}
                )
                assert entry["native_tracker"]["play_mode"] == (
                    "normal" if slot == 1 else "boss_rush"
                )
                case = dict(slot=slot, entry=entry)
                report["cases"].append(case)
                screenshots.snapshot(c, "tracker-slot-" + str(slot) + "-game")
                if slot == 1:
                    c.window.key("q")
                    pump(c, 1)
                    dead = current(c)
                    assert dead["deaths_run"] == entry["deaths_run"] + 1, (dead, entry)
                    assert not any(
                        o["name"] == "Player" for o in objects(c.window.reader)
                    )
                    case["death"] = dead
                    c.window.key("r")
                    pump(c, 1)
                    assert current(c)["deaths_run"] == dead["deaths_run"]
                else:
                    subprocess.run(["xdotool", "keydown", "x"], check=True)
                    seen = False
                    dead = False
                    start = time.monotonic()
                    try:
                        while time.monotonic() - start < 95:
                            pump(c, 0.2)
                            boss = next(
                                (
                                    o
                                    for o in objects(c.window.reader)
                                    if o["name"] == "hellokitty"
                                ),
                                None,
                            )
                            if boss:
                                seen = True
                                if values(c.window.reader, boss, 3)[1] <= 0:
                                    dead = True
                                    break
                            elif seen:
                                dead = True
                                break
                    finally:
                        subprocess.run(["xdotool", "keyup", "x"], check=True)
                    assert seen and dead
                    pump(c, 2)
                    case["victory"] = current(c)
                    print(
                        "BOSS VICTORY",
                        case["victory"]["native_tracker"]["bosses"][0],
                        flush=True,
                    )
                    # Keep the normal victory animation; a receipt may follow its exit.
                    pump(c, 30)
                    for _ in range(18):
                        if c.window.reader.frame() == "Eleventh Boss - Solgryn":
                            break
                        subprocess.run(["xdotool", "keydown", "Right"], check=True)
                        try:
                            c.window.key("Shift_L")
                            c.window.key("z")
                            pump(c, 0.45)
                        finally:
                            subprocess.run(["xdotool", "keyup", "Right"], check=True)
                        pump(c, 0.25)
                    wait_for(
                        c,
                        lambda: c.window.reader.frame() == "Eleventh Boss - Solgryn",
                        seconds=15,
                    )
                    pump(c, 1)
                    case["after_exit"] = current(c)
                    assert next(
                        r
                        for r in case["after_exit"]["native_tracker"]["bosses"]
                        if r["key"] == "hellokitty"
                    )["done"]
                    assert not next(
                        r
                        for r in case["after_exit"]["native_tracker"]["bosses"]
                        if r["key"] == "solgryn"
                    )["done"]
                    # Allow the external observer to capture the live OBS source.
                    (OUT / "capture-ready.json").write_text(
                        json.dumps(dict(phase="boss-award", state=case["after_exit"]))
                    )
                    print("OBS CAPTURE READY", flush=True)
                    pump(c, 15)
                before_menu = current(c)
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu", seconds=30)
                c.enter()
                pump(c, 1)
                assert current(c)["native_tracker"]["mode"] == "menu"
                c.model.slot = slot
                c.model.load_slot()
                c.begin()
                wait_for(c, lambda: c.phase == "playing", seconds=35)
                pump(c, 1)
                resumed = current(c)
                assert (
                    resumed["native_tracker"]["run_id"]
                    == entry["native_tracker"]["run_id"]
                )
                assert resumed["deaths_run"] == before_menu["deaths_run"]
                assert (
                    resumed["native_tracker"]["elapsed"]
                    >= before_menu["native_tracker"]["elapsed"]
                )
                case["resumed"] = resumed
                if slot == 2:
                    assert next(
                        r
                        for r in resumed["native_tracker"]["bosses"]
                        if r["key"] == "hellokitty"
                    )["done"]
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu", seconds=30)
                c.enter()
                case["passed"] = True
                print("PASS SLOT", slot, flush=True)
            report["passed"] = True
        except BaseException as exc:
            report["error"] = repr(exc)
            raise
        finally:
            subprocess.run(["xdotool", "keyup", "x", "Right", "Left"], check=False)
            c.close()
            time.sleep(2)
            report["after_close"] = status()
            report["feed_after_close"] = json.loads(feed_path().read_text())
            (OUT / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")
    assert not report["after_close"].get("native_tracker")


if __name__ == "__main__":
    main()
