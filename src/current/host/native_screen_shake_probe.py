"""Compare native boss quake rendering with the per-save switch off and on.

Normal keys and read-only observation only. One owned game process. Boss damage
comes from actual shots; God Mode protects the player throughout the comparison.
"""

import argparse
import json
import struct
import subprocess
import time
import uuid
from pathlib import Path
from functools import partial
from PIL import ImageGrab
from native_menu import builds
from menu_host.store import digest


def find_viewport(reader):
    run = reader.u32(reader.base + 0xA35DC)
    table = reader.u32(run + 0x1278)
    data = b"".join(
        reader.read(table + i, min(256, 160000 - i)) for i in range(0, 160000, 256)
    )
    for slot in range(20000):
        ptr = struct.unpack_from("<I", data, slot * 8)[0]
        if ptr < 65536:
            continue
        try:
            raw = reader.read(ptr, 160)
        except RuntimeError:
            # Live projectiles can disappear after the object-table snapshot.
            continue
        if (
            struct.unpack_from("<H", raw, 24)[0] != 34
            or struct.unpack_from("<I", raw, 8)[0] != run
            or struct.unpack_from("<H", raw, 0)[0] != slot
            or struct.unpack_from("<H", raw, 124)[0] & 1
        ):
            continue
        oip = struct.unpack_from("<I", raw, 28)[0]
        name = (
            reader.read(oip + 90, 64)
            .decode("utf-16le", errors="replace")
            .split("\0")[0]
        )
        if "Viewport" in name:
            return dict(ptr=ptr, rel=struct.unpack_from("<I", raw, 128)[0], name=name)
    raise AssertionError("Native viewport missing")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--exe", type=Path, required=True)
    p.add_argument("--scene", choices=("sonic", "hellokitty"), default="hellokitty")
    p.add_argument("--slots", type=int, choices=(1, 2), nargs="+", default=(1, 2))
    p.add_argument("--sprites", action="store_true")
    p.add_argument(
        "--knockback",
        action="store_true",
        help="Wait for natural launch and return before shooting",
    )
    p.add_argument("--output", type=Path)
    args = p.parse_args()
    builds.DYNAMIC_BASE = args.exe
    builds.DYNAMIC_SHA = digest(args.exe)
    builds.DYNAMIC_SCREEN_SHAKE = True
    from export_native_run import export
    from export_route_probe import ROOT
    from menu_host.store import Store, save
    from menu_host.draft import Draft
    from native_menu.combined import CombinedController
    from native_menu_probe import pump
    from native_menu_lifecycle_probe import wait_for
    from menu_host.processes import games
    from god_mode_boss_probe import values
    import god_mode_live as capture
    import native_death_visual_probe as screenshots
    from gameplay.screen_shake import GROUP, KEY

    out = args.output or ROOT / "outputs/Fusion-ScreenShake-20261025"
    out.mkdir(parents=True, exist_ok=True)
    screenshots.OUT = capture.OUT = out
    store = Store(
        out / ("profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    report = dict(scope=__doc__, memory_writes=0, sha256=builds.DYNAMIC_SHA, cases=[])
    with store.lock():
        for slot, disabled in ((1, False), (2, True)):
            d = Draft()
            d.set_mode("boss_rush")
            d.update(
                boss_pool=[args.scene],
                route_boss_count=1,
                god_mode=True,
                no_mouse_ghost=True,
                autofire=True,
                skip_intro=True,
                start_character="Boshy",
                no_screen_shaking=disabled,
                sprite_scenery=args.sprites,
                sprite_backgrounds=args.sprites,
                sprite_decor=args.sprites,
                sprite_tiles=args.sprites,
                sprite_actors=args.sprites,
            )
            d.seed = "SHAKE025"
            store.create(slot, d)
        c = CombinedController(store, dynamic=True)
        report["working"] = str(c.folder)
        try:
            c.open()
            c.enter()
            pid = c.window.pid
            # Show the actual native hack list before entering a save.
            c.model.go("gameplay")
            c.model.focus = len(c.model.rows()) - 2
            c.mail.publish()
            pump(c, 0.5)
            screenshots.snapshot(c, "native-shake-option")
            c.model.go("home")
            c.mail.publish()
            for slot in args.slots:
                c.model.slot = slot
                c.model.load_slot()
                c.begin()
                wait_for(c, lambda: c.phase == "playing", seconds=35)
                pump(c, 0.6)
                assert c.window.pid == pid and len(games()) == 1
                cfg = save(c.folder / "SaveFile1.ini")
                assert cfg.getint(GROUP, KEY) == int(slot == 2)
                obs = capture.objects(c.window.reader)
                shaker = next(o for o in obs if o["name"] == "Screen Shaker")
                # Keep Boshy over the platform that remains after phase one.
                if args.scene == "sonic":
                    subprocess.run(["xdotool", "keydown", "Right"], check=True)
                    try:
                        wait_for(
                            c,
                            lambda: next(
                                o
                                for o in capture.objects(c.window.reader)
                                if o["name"] == "Player"
                            )["x"]
                            >= 310,
                            seconds=5,
                        )
                    finally:
                        subprocess.run(["xdotool", "keyup", "Right"], check=True)
                player = next(
                    o for o in capture.objects(c.window.reader) if o["name"] == "Player"
                )
                case = dict(slot=slot, disabled=slot == 2, samples=[], captures=[])
                from Xlib import display

                xd = display.Display()
                w = xd.create_resource_object("window", int(c.window.window, 16))
                g = w.get_geometry()
                point = xd.screen().root.translate_coords(w, 0, 0)
                rectangle = (point.x, point.y, point.x + g.width, point.y + g.height)
                xd.close()
                viewport = find_viewport(c.window.reader)
                case["viewport"] = viewport
                report["cases"].append(case)
                start = time.monotonic()
                last_capture = 0
                last_report = 0
                quake_count = 0
                shooting = not args.knockback
                airborne = False
                returned = False
                if shooting:
                    subprocess.run(["xdotool", "keydown", "x"], check=True)
                try:
                    while time.monotonic() - start < 180:
                        pump(c, 0.08)
                        now = time.monotonic() - start
                        v = values(c.window.reader, shaker, 3)
                        raw_player = c.window.reader.read(player["ptr"], 96)
                        assert struct.unpack_from("<H", raw_player)[0] == player["slot"]
                        px = struct.unpack_from("<i", raw_player, 76)[0]
                        py = struct.unpack_from("<i", raw_player, 84)[0]
                        case["samples"].append(
                            dict(t=round(now, 3), shaker=v, player=[px, py])
                        )
                        if args.knockback:
                            header = c.window.reader.read(viewport["ptr"], 32)
                            assert struct.unpack_from("<H", header, 24)[0] == 34, (
                                "Viewport vanished during knockback"
                            )
                            if py < -640 and not airborne:
                                airborne = True
                                case["airborne_at"] = round(now, 3)
                                screenshots.snapshot(
                                    c, f"{args.scene}-slot{slot}-airborne"
                                )
                            if airborne and py >= 300 and not returned:
                                returned = True
                                case["returned_at"] = round(now, 3)
                                screenshots.snapshot(
                                    c, f"{args.scene}-slot{slot}-returned"
                                )
                                subprocess.run(["xdotool", "keydown", "x"], check=True)
                                shooting = True
                        if now - last_report >= 10:
                            print(
                                "SHAKE",
                                slot,
                                round(now, 1),
                                v,
                                "player",
                                px,
                                py,
                                "shooting",
                                shooting,
                                flush=True,
                            )
                            last_report = now
                        if (
                            v[0] > 0 or abs(v[1]) + abs(v[2]) > 1
                        ) and now - last_capture > 0.08:
                            file = f"{args.scene}-slot{slot}-quake{quake_count:03d}.png"
                            ImageGrab.grab().crop(rectangle).save(out / file)
                            # The viewport is an extension, not an Active. Its
                            # offset 128 is NOT an Active alterable-value pointer.
                            # Check its cached object identity and read only the
                            # native source rectangle verified in Viewport.mfx.
                            header = c.window.reader.read(viewport["ptr"], 32)
                            assert struct.unpack_from("<H", header, 24)[0] == 34
                            rectangle_values = struct.unpack(
                                "<4i", c.window.reader.read(viewport["ptr"] + 692, 16)
                            )
                            case["captures"].append(
                                dict(
                                    file=file,
                                    t=round(now, 3),
                                    shaker=v,
                                    player=[px, py],
                                    source_rectangle=rectangle_values,
                                )
                            )
                            last_capture = now
                            quake_count += 1
                        if quake_count >= 20 and (not args.knockback or returned):
                            break
                    screenshots.snapshot(c, f"{args.scene}-slot{slot}-after-quake")
                finally:
                    subprocess.run(["xdotool", "keyup", "x"], check=True)
                if args.knockback:
                    assert airborne and returned, (
                        "Natural launch and return not both observed"
                    )
                    case["minimum_player_y"] = min(
                        s["player"][1] for s in case["samples"]
                    )
                assert quake_count >= 3, "Natural boss quake was not observed"
                case["quake_count"] = quake_count
                origins = [r["source_rectangle"][:2] for r in case["captures"]]
                case["origin_span"] = [
                    max(p[i] for p in origins) - min(p[i] for p in origins)
                    for i in (0, 1)
                ]
                assert (case["origin_span"] == [0, 0]) == (slot == 2), case[
                    "origin_span"
                ]
                c.window.key("q")
                pump(c, 0.7)
                assert not any(
                    o["name"] == "Player" for o in capture.objects(c.window.reader)
                )
                c.window.key("r")
                pump(c, 0.8)
                assert any(
                    o["name"] == "Player" for o in capture.objects(c.window.reader)
                )
                assert save(c.folder / "SaveFile1.ini").getint(GROUP, KEY) == int(
                    slot == 2
                )
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu", seconds=30)
                c.enter()
                store.resume(slot)
                case["death_retry_menu_saved"] = True
                print("PASS", slot, quake_count, "quakes", flush=True)
            report["completed"] = True
        except BaseException as error:
            report["error"] = repr(error)
            raise
        finally:
            c.close()
            (out / (args.scene + "-live-results.json")).write_text(
                json.dumps(report, indent=2) + "\n"
            )


if __name__ == "__main__":
    main()
