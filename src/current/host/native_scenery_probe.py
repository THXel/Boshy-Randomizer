"""Exercise three scenery saves in one native process, with real death/retry."""

import argparse
import ctypes
import os
import struct
import time
import json
import subprocess
import uuid
from pathlib import Path
from functools import partial
from native_menu import builds
from menu_host.store import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--exe", type=Path, required=True)
    parser.add_argument("--label", required=True)
    parser.add_argument("--phase", action="store_true")
    parser.add_argument(
        "--scene",
        choices=("prehistorik", "castlevania", "greengreens", "sonic"),
        default="prehistorik",
    )
    args = parser.parse_args()
    builds.DYNAMIC_BASE = args.exe
    builds.DYNAMIC_SHA = digest(args.exe)
    builds.DYNAMIC_SCENERY = True
    from export_native_run import export
    from export_route_probe import ROOT
    from menu_host.store import Store
    from menu_host.draft import Draft
    from native_menu.combined import CombinedController
    from native_menu_probe import pump
    from native_menu_lifecycle_probe import wait_for
    from menu_host.processes import games
    from visuals import scenery_assets
    import native_death_visual_probe as screenshots
    import god_mode_live as capture

    out = ROOT / "outputs/Fusion-Scenery-20261025"
    out.mkdir(exist_ok=True)
    screenshots.OUT = capture.OUT = out
    store = Store(
        out / ("profile-" + args.label + "-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    report = dict(
        scope=__doc__,
        scene=args.scene,
        game_sha256=builds.DYNAMIC_SHA,
        memory_writes=0,
        cases=[],
    )
    with store.lock():
        for slot in (1, 2, 3):
            d = Draft()
            if args.scene == "sonic":
                d.set_mode("boss_rush")
                d.update(boss_pool=["sonic"], route_boss_count=1, skip_intro=True)
            else:
                d.set_mode("level_rush")
                d.update(
                    level_pool=[
                        {"castlevania": "save7.ini", "greengreens": "save2.ini"}.get(
                            args.scene, "save1.ini"
                        )
                    ],
                    level_count=1,
                    boss_pool=[],
                    route_boss_count=0,
                )
            d.update(
                god_mode=args.scene == "sonic",
                no_mouse_ghost=True,
                autofire=args.phase,
                start_character="Boshy",
                sprite_scenery=slot != 1,
                sprite_backgrounds=True,
                sprite_decor=True,
                sprite_tiles=True,
                sprite_actors=slot != 1,
                sprite_dim=20,
            )
            d.seed = "SCENE025" + str(slot)
            store.create(slot, d)
        c = CombinedController(store, dynamic=True)
        report["working"] = str(c.folder)

        def observe():
            obs = capture.objects(c.window.reader)
            return dict(
                frame=c.window.reader.frame(),
                player=[o for o in obs if o["name"] == "Player"],
                skeletons=[
                    o
                    for o in obs
                    if o["name"] in ("EnemyWidgetTurn 2", "EnemyWidgetTurn 3")
                ],
                helpers=[o for o in obs if o["name"].startswith("Randomizer Scenery ")],
            )

        try:
            c.open()
            c.enter()
            pid = c.window.pid
            for n, slot in enumerate((2,) if args.phase else (1, 2, 3, 1)):
                c.model.slot = slot
                c.model.load_slot()
                stage = c.session.stage
                watcher = []

                def watched_stage(selected_slot):
                    stage(selected_slot)
                    libc = ctypes.CDLL(None, use_errno=True)
                    fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
                    if fd < 0:
                        raise OSError(ctypes.get_errno(), "inotify")
                    if (
                        libc.inotify_add_watch(
                            fd, os.fsencode(c.folder / "native-scenery"), 0x20
                        )
                        < 0
                    ):
                        os.close(fd)
                        raise OSError(ctypes.get_errno(), "inotify watch")
                    watcher.append(fd)

                c.session.stage = watched_stage
                try:
                    c.begin()
                finally:
                    c.session.stage = stage
                wait_for(c, lambda: c.phase == "playing")
                pump(c, 0.8)
                opened = []
                try:
                    data = os.read(watcher[0], 262144)
                    at = 0
                    while at < len(data):
                        wd, mask, cookie, length = struct.unpack_from("iIII", data, at)
                        name = (
                            data[at + 16 : at + 16 + length].split(b"\0", 1)[0].decode()
                        )
                        if name:
                            opened.append(name)
                        at += 16 + length
                except BlockingIOError:
                    pass
                finally:
                    os.close(watcher[0])
                case = dict(slot=slot, alive=observe(), native_image_reads=opened)
                report["cases"].append(case)
                assert len(case["alive"]["player"]) == 1, "Missing player before test"
                assert all(
                    struct.unpack(
                        "<H", c.window.reader.read(o["ptr"] + o["rel"] - 4, 4)[:2]
                    )[0]
                    & 1
                    for o in case["alive"]["helpers"]
                ), "Cached scenery helper became visible"
                assert (
                    c.window.pid == pid and len(games()) == 1
                ), "More than one game process"
                label = f"{args.label}-{n}-slot{slot}"
                screenshots.snapshot(c, label + "-alive")
                scenery_assets.validate_assets(
                    c.folder, json.loads((store.folder(slot) / "plan.json").read_text())
                )
                if args.scene != "sonic":
                    try:
                        subprocess.run(
                            [
                                "xdotool",
                                "keydown",
                                "--window",
                                c.window.window,
                                "Right",
                            ],
                            check=True,
                        )
                        pump(c, 0.18)
                    finally:
                        subprocess.run(
                            ["xdotool", "keyup", "--window", c.window.window, "Right"],
                            check=True,
                        )
                    pump(c, 0.3)
                    case["moved"] = observe()
                    assert (
                        len(case["moved"]["player"]) == 1
                    ), "Player disappeared during movement"
                    a, b = case["alive"]["player"][0], case["moved"]["player"][0]
                    assert b["x"] > a["x"] and abs(b["y"] - a["y"]) < 30, (
                        "Terrain collision changed",
                        a,
                        b,
                    )
                if args.phase:
                    assert args.scene == "sonic"
                    from god_mode_boss_probe import values

                    # Keep Boshy over the centre platform when the sides vanish.
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
                    samples = []
                    started = time.monotonic()
                    subprocess.run(["xdotool", "keydown", "x"], check=True)
                    try:
                        while time.monotonic() - started < 75:
                            pump(c, 1)
                            obs = capture.objects(c.window.reader)
                            boss = next(
                                (o for o in obs if o["name"] == "Active 4sonic"), None
                            )
                            phase = dict(
                                seconds=round(time.monotonic() - started, 1),
                                overlay=any(o["name"] == "Active 20sonic" for o in obs),
                                boss_values=(
                                    values(c.window.reader, boss, 5) if boss else None
                                ),
                                platforms=[
                                    o for o in obs if o["name"] == "Active 23sonic"
                                ],
                                fire=[
                                    o
                                    for o in obs
                                    if o["name"] in ("Active 17sonic", "firah")
                                ],
                                player=[o for o in obs if o["name"] == "Player"],
                            )
                            samples.append(phase)
                            if len(samples) % 5 == 0:
                                print(
                                    "PHASE",
                                    phase["seconds"],
                                    phase["boss_values"],
                                    "overlay",
                                    phase["overlay"],
                                    flush=True,
                                )
                            if not phase["overlay"] and any(
                                o["w"] == 168 for o in phase["platforms"]
                            ):
                                pump(c, 2)
                                break
                        else:
                            raise AssertionError(
                                "Sonic phase not reached by real shots"
                            )
                    finally:
                        subprocess.run(["xdotool", "keyup", "x"], check=True)
                        case["phase_samples"] = samples
                    screenshots.snapshot(c, label + "-shrunk-platform-fire")
                    assert samples[-1]["player"], "Player missing in fire phase"
                c.window.key("q")
                pump(c, 0.8)
                case["death"] = observe()
                screenshots.snapshot(c, label + "-death")
                assert not case["death"]["player"], "Q did not kill player"
                c.window.key("r")
                pump(c, 0.8)
                case["retry"] = observe()
                screenshots.snapshot(c, label + "-retry")
                assert len(case["retry"]["player"]) == 1, "Retry lost player"
                assert len(case["retry"]["helpers"]) == len(
                    case["alive"]["helpers"]
                ), "Scenery cache grew on restart"
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu")
                c.enter()
                case["saved"] = store.summary(slot)
                print("PASS", args.scene, "slot", slot, "same pid", pid, flush=True)
            report["passed"] = True
        except BaseException as error:
            report["error"] = str(error)
            raise
        finally:
            c.close()
            (out / (args.label + "-results.json")).write_text(
                json.dumps(report, indent=2) + "\n"
            )


if __name__ == "__main__":
    main()
