"""Private spider playtests; pre-launch countdown fixtures, read-only live state."""

import argparse
import io
import json
import math
import struct
import subprocess
import time
import uuid
from functools import partial
from pathlib import Path
from native_menu import builds
from menu_host.store import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument(
        "--cases",
        nargs="+",
        default=["edge0", "edge1", "edge2", "edge3", "contact", "off", "boss"],
    )
    args = parser.parse_args()
    builds.DYNAMIC_BASE = args.exe
    builds.DYNAMIC_SHA = digest(args.exe)
    builds.DYNAMIC_SPIDER = True
    from export_route_probe import ROOT
    from export_native_run import export
    from menu_host.store import Store, save, RC4, atomic
    from menu_host.draft import Draft
    from menu_host.processes import games
    from native_menu.combined import CombinedController
    from native_menu_probe import pump, snapshot as menu_snapshot
    from native_menu_lifecycle_probe import wait_for
    from native_menu.observe import objects
    from god_mode_boss_probe import values
    from gameplay import spider_plan as plan, spider_events as event
    from gameplay.native_extras import advance
    from gameplay.spider_object import NAME
    import god_mode_live as capture
    import native_death_visual_probe as screenshots

    out = ROOT / "outputs/Fusion-Spider-20261025"
    out.mkdir(exist_ok=True)
    capture.OUT = screenshots.OUT = out
    seeds = {}
    for i in range(500):
        seed = f"SPDR{i:04d}"
        config = plan.settings(seed, {"spider": True})
        seeds.setdefault(advance(config["InitialState"], 2) % 4, seed)
        if len(seeds) == 4:
            break
    report = dict(
        scope=__doc__,
        sha256=builds.DYNAMIC_SHA,
        memory_writes=0,
        fixture="Enabled test saves have Remaining=1 before launch. Native 15-second grace, RNG and gameplay unchanged.",
        cases=[],
    )

    def state(c):
        path = c.folder / "onlineLicense.ini"
        if not path.exists():
            return None
        cfg = save(path)
        return dict(cfg[plan.STATE]) if cfg.has_section(plan.STATE) else None

    for batch in range(0, len(args.cases), 3):
        names = args.cases[batch : batch + 3]
        store = Store(
            out / ("profile-" + uuid.uuid4().hex[:8]),
            exporter=partial(export, dynamic=True),
        )
        with store.lock():
            for slot, name in enumerate(names, 1):
                d = Draft()
                d.set_mode("boss_rush" if name == "boss" else "normal")
                if name == "boss":
                    d.update(
                        boss_pool=["hellokitty"], route_boss_count=1, skip_intro=True
                    )
                d.update(
                    spider=name != "off",
                    god_mode=name != "contact",
                    no_mouse_ghost=True,
                    start_character="Auto",
                    characters=False,
                    sprite_scenery=True,
                    sprite_backgrounds=True,
                    sprite_decor=True,
                    sprite_tiles=True,
                    sprite_actors=True,
                )
                d.seed = seeds[int(name[-1])] if name.startswith("edge") else seeds[0]
                store.create(slot, d)
                if name != "off":
                    path = store.folder(slot) / "onlineLicense.ini"
                    cfg = save(path)
                    cfg[plan.STATE]["Remaining"] = "1"
                    buf = io.StringIO()
                    cfg.write(buf)
                    atomic(path, RC4(b"BLOB", buf.getvalue().encode("latin1")))
                store.resume(slot)
            c = CombinedController(store, dynamic=True)
            try:
                c.open()
                c.enter()
                pid = c.window.pid
                c.model.go("gameplay")
                c.model.focus = 10
                for lang in ("de", "en", "es", "ru", "ja"):
                    c.model.language = lang
                    c.mail.publish()
                    menu_snapshot(c, "spider-menu-" + lang)
                c.model.go("home")
                c.mail.publish()
                for slot, name in enumerate(names, 1):
                    c.model.slot = slot
                    c.model.load_slot()
                    c.begin()
                    wait_for(c, lambda: c.phase == "playing", seconds=35)
                    assert c.window.pid == pid and len(games()) == 1
                    obs = objects(c.window.reader)
                    spider = next(o for o in obs if o["name"] == NAME)
                    case = dict(
                        name=name,
                        slot=slot,
                        seed=c.model.draft.seed,
                        profile=str(store.root),
                        entry=state(c),
                        controller=spider,
                        samples=[],
                    )
                    report["cases"].append(case)
                    start = time.monotonic()
                    finished = False
                    seen = False
                    captured = False
                    limit = 20 if name == "off" else 30
                    while time.monotonic() - start < limit:
                        pump(c, 0.08)
                        v = values(c.window.reader, spider, 12)
                        st = state(c)
                        elapsed = time.monotonic() - start
                        if v[event.ACTIVE]:
                            if not seen:
                                case["attack_after_seconds"] = round(elapsed, 3)
                                seen = True
                                print(
                                    "SPIDER",
                                    name,
                                    case["attack_after_seconds"],
                                    flush=True,
                                )
                            raw = c.window.reader.read(spider["ptr"] + 232, 4)
                            angle_float = struct.unpack("<f", raw)[0]
                            angle_int = struct.unpack("<i", raw)[0]
                            coords = (
                                struct.unpack(
                                    "<i", c.window.reader.read(spider["ptr"] + 76, 4)
                                )[0],
                                struct.unpack(
                                    "<i", c.window.reader.read(spider["ptr"] + 84, 4)
                                )[0],
                            )
                            case["samples"].append(
                                dict(
                                    t=round(elapsed, 3),
                                    values=v,
                                    position=coords,
                                    angle_float=angle_float,
                                    angle_int=angle_int,
                                )
                            )
                            run = c.window.reader.u32(c.window.reader.base + 0xA35DC)
                            scroll = struct.unpack(
                                "<ii", c.window.reader.read(run + 0xB0, 8)
                            )
                            screen = (coords[0] - scroll[0], coords[1] - scroll[1])
                            if (
                                not captured
                                and 0 <= screen[0] < 640
                                and 0 <= screen[1] < 480
                            ):
                                screenshots.snapshot(c, "spider-" + name + "-visible")
                                captured = True
                        elif seen or (st and int(st["hits"]) > 0):
                            finished = True
                            break
                    case["after_attack"] = state(c)
                    case["alive_after"] = any(
                        o["name"] == "Player" for o in objects(c.window.reader)
                    )
                    case["render_capture"] = captured
                    if name == "off":
                        assert not seen and not case["samples"] and state(c) is None
                    else:
                        assert seen and finished, case
                        # At the original left-edge spawn, contact occurs while
                        # the spider's hotspot is still outside the viewport.
                        # Four God-Mode edge cases separately prove rendering.
                        assert captured or (
                            name == "contact"
                            and int(case["after_attack"]["hits"]) == 1
                            and not case["alive_after"]
                        ), case
                        assert 13 <= case["attack_after_seconds"] <= 23, case[
                            "attack_after_seconds"
                        ]
                        assert int(case["after_attack"]["attacks"]) == 1
                        assert int(case["after_attack"]["hits"]) == int(
                            name == "contact"
                        )
                        assert case["alive_after"] == (name != "contact")
                        for sample in case["samples"]:
                            vx, vy = sample["values"][event.DX : event.DY + 1]
                            assert abs(math.hypot(vx, vy) * 50 - 475) < 0.01, (vx, vy)
                        assert (
                            len(
                                {
                                    tuple(s["values"][event.DX : event.DY + 1])
                                    for s in case["samples"]
                                }
                            )
                            == 1
                        )
                        if name.startswith("edge"):
                            assert int(case["samples"][0]["values"][event.SIDE]) == int(
                                name[-1]
                            )
                    screenshots.snapshot(c, "spider-" + name + "-after")
                    if name == "contact":
                        before = state(c)
                        pump(c, 2)
                        assert state(c) == before
                        c.window.key("r")
                        pump(c, 1)
                        assert any(
                            o["name"] == "Player" for o in objects(c.window.reader)
                        )
                        assert state(c) == before
                    c.window.key("F2")
                    wait_for(c, lambda: c.phase == "menu", seconds=30)
                    c.enter()
                    store.resume(slot)
                    saved = (
                        save(store.folder(slot) / "onlineLicense.ini")
                        if (store.folder(slot) / "onlineLicense.ini").exists()
                        else None
                    )
                    case["saved"] = (
                        dict(saved[plan.STATE])
                        if saved and saved.has_section(plan.STATE)
                        else None
                    )
                    c.model.slot = slot
                    c.model.load_slot()
                    c.begin()
                    wait_for(c, lambda: c.phase == "playing", seconds=35)
                    pump(c, 1)
                    assert state(c) == case["saved"]
                    sp = next(o for o in objects(c.window.reader) if o["name"] == NAME)
                    assert values(c.window.reader, sp, 1)[0] == 0
                    c.window.key("F2")
                    wait_for(c, lambda: c.phase == "menu", seconds=30)
                    c.enter()
                    store.resume(slot)
                    case["passed"] = True
                    print("PASS", name, case["after_attack"], flush=True)
            except BaseException as error:
                report["error"] = repr(error)
                try:
                    screenshots.snapshot(c, "spider-failure")
                except Exception:
                    pass
                raise
            finally:
                subprocess.run(["xdotool", "keyup", "Left", "Right", "x"], check=False)
                c.close()
                (out / "live-results.json").write_text(
                    json.dumps(report, indent=2) + "\n"
                )
    report["passed"] = True
    (out / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
