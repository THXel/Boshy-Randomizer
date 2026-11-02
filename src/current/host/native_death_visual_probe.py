"""Real death/respawn with window and desktop captures and read-only particle data."""

import argparse
import json
import time
import uuid
from functools import partial
from PIL import ImageGrab
from Xlib import display
from export_route_probe import ROOT
from export_native_run import export
from menu_host.store import Store
from menu_host.draft import Draft
from native_menu.combined import CombinedController
from native_menu_probe import pump
from native_menu_lifecycle_probe import wait_for
from god_mode_boss_probe import values
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-DeathVisuals-20261025"


def snapshot(c, label):
    capture.snap(c.window, label + "-window")
    d = display.Display()
    w = d.create_resource_object("window", int(c.window.window, 16))
    g = w.get_geometry()
    point = d.screen().root.translate_coords(w, 0, 0)
    root = ImageGrab.grab()
    crop = root.crop((point.x, point.y, point.x + g.width, point.y + g.height))
    crop.save(OUT / (label + "-desktop.png"))
    d.close()
    return dict(x=point.x, y=point.y, width=g.width, height=g.height)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--no-god", action="store_true")
    parser.add_argument("--character", default="Boshy", choices=("Auto", "Boshy"))
    parser.add_argument(
        "--scene", choices=("level", "sonic", "oldsonic"), default="level"
    )
    parser.add_argument("--natural", action="store_true")
    parser.add_argument("--expect-flames", choices=("on", "off"))
    parser.add_argument(
        "--packs",
        nargs="+",
        choices=("original", "kamilia3"),
        default=("original", "kamilia3"),
    )
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    capture.OUT = OUT
    store = Store(
        OUT / ("profile-" + uuid.uuid4().hex[:8]),
        exporter=partial(export, dynamic=True),
    )
    report = dict(
        scope=__doc__,
        memory_writes=0,
        cases=[],
        god_mode=not args.no_god,
        character=args.character,
        scene=args.scene,
        natural_death=args.natural,
    )
    with store.lock():
        c = CombinedController(store, dynamic=True)
        try:
            c.open()
            c.enter()
            for slot, pack in enumerate(args.packs, 1):
                draft = Draft()
                draft.set_mode("normal" if args.scene == "level" else "boss_rush")
                if args.scene != "level":
                    draft.update(
                        boss_pool=[args.scene], route_boss_count=1, skip_intro=True
                    )
                draft.update(
                    god_mode=not args.no_god,
                    no_mouse_ghost=True,
                    start_character=args.character,
                )
                draft.select_pack("blood_pack", pack)
                draft.seed = "DEAD0025"
                store.create(slot, draft)
                c.model.slot = slot
                c.model.load_slot()
                c.begin()
                wait_for(c, lambda: c.phase == "playing")
                pump(c, 1)
                case = dict(pack=pack, samples=[])
                report["cases"].append(case)
                case["alive"] = [
                    o for o in capture.objects(c.window.reader) if o["name"] == "Player"
                ]
                snapshot(c, args.label + "-" + pack + "-alive")
                assert len(case["alive"]) == 1, "Died before the requested death test"
                if args.natural:
                    started = time.monotonic()
                    while any(
                        o["name"] == "Player" for o in capture.objects(c.window.reader)
                    ):
                        assert (
                            time.monotonic() - started < 60
                        ), "No natural death within test window"
                        pump(c, 0.3)
                    case["death_after_seconds"] = time.monotonic() - started
                else:
                    c.window.key("q")
                for delay in (0.1, 0.5, 2, 3):
                    pump(c, delay)
                    obs = capture.objects(c.window.reader)
                    selected = []
                    for obj in obs:
                        if obj["name"] not in ("Player", "Active 2", "blood"):
                            continue
                        try:
                            selected.append(
                                dict(obj, values=values(c.window.reader, obj, 7))
                            )
                        except RuntimeError:
                            # A native short-lived particle may expire during observation.
                            continue
                    case["samples"].append(dict(delay=delay, objects=selected))
                    case["capture"] = snapshot(
                        c, args.label + "-" + pack + "-death-" + str(delay)
                    )
                c.window.key("r")
                pump(c, 1)
                case["respawn"] = [
                    o for o in capture.objects(c.window.reader) if o["name"] == "Player"
                ]
                assert len(case["respawn"]) == 1, "Respawn did not remain alive"
                assert all(
                    not any(o["name"] == "Player" for o in sample["objects"])
                    for sample in case["samples"]
                )
                snapshot(c, args.label + "-" + pack + "-respawn")
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu")
                c.enter()
                # Re-enter the committed slot rather than only restarting its frame.
                c.model.slot = slot
                c.model.load_slot()
                c.begin()
                wait_for(c, lambda: c.phase == "playing")
                pump(c, 1)
                observed = capture.objects(c.window.reader)
                case["resume"] = [o for o in observed if o["name"] == "Player"]
                case["fire_particles_on_resume"] = sum(
                    o["name"] == "OPE_fireParticle" for o in observed
                )
                assert (
                    len(case["resume"]) == 1
                ), "Saved-slot resume did not remain alive"
                snapshot(c, args.label + "-" + pack + "-resume")
                c.window.key("F2")
                wait_for(c, lambda: c.phase == "menu")
                c.enter()
                print("CAPTURED", pack, flush=True)
        finally:
            c.close()
            (OUT / (args.label + "-results.json")).write_text(
                json.dumps(report, indent=2) + "\n"
            )


if __name__ == "__main__":
    main()
