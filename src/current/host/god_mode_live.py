"""Native God Mode on/off, real mouse contact and Q/R checks; memory reads only."""

import json, struct, subprocess, time
from pathlib import Path
from Xlib import display, X
from PIL import Image
from menu_host.runtime import Runtime, windows
from menu_host.store import Store
from menu_host.processes import games
from export_route_probe import ROOT

OUT = ROOT / "outputs/Fusion-GodMode-20261024"


def objects(reader):
    run = reader.u32(reader.base + 0xA35DC)
    assert reader.u32(run + 0x40) == 20000
    table = reader.u32(run + 0x1278)
    data = b"".join(
        reader.read(table + i, min(256, 160000 - i)) for i in range(0, 160000, 256)
    )
    result = []
    for slot in range(20000):
        ptr = struct.unpack_from("<I", data, slot * 8)[0]
        if ptr < 65536:
            continue
        raw = reader.read(ptr, 160)
        if (
            struct.unpack_from("<I", raw, 8)[0] != run
            or struct.unpack_from("<H", raw, 0)[0] != slot
            or struct.unpack_from("<H", raw, 24)[0] != 2
            or struct.unpack_from("<H", raw, 124)[0] & 1
        ):
            continue
        oi = struct.unpack_from("<H", raw, 18)[0]
        oip = struct.unpack_from("<I", raw, 28)[0]
        name = (
            reader.read(oip + 90, 64)
            .decode("utf-16le", errors="replace")
            .split("\0")[0]
        )
        result.append(
            dict(
                ptr=ptr,
                slot=slot,
                rel=struct.unpack_from("<I", raw, 128)[0],
                w=struct.unpack_from("<i", raw, 96)[0],
                h=struct.unpack_from("<i", raw, 100)[0],
                oi=oi,
                name=name,
                x=struct.unpack_from("<i", raw, 76)[0],
                y=struct.unpack_from("<i", raw, 84)[0],
            )
        )
    return result


def snap(runtime, name):
    d = display.Display()
    w = d.create_resource_object("window", int(runtime.window, 16))
    g = w.get_geometry()
    raw = w.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
    Image.frombytes("RGB", (g.width, g.height), raw.data, "raw", "BGRX").save(
        OUT / (name + ".png")
    )
    d.close()


def point(runtime, x, y):
    subprocess.run(["wmctrl", "-ia", runtime.window], check=True)
    subprocess.run(
        ["xdotool", "mousemove", "--window", runtime.window, str(x), str(y)], check=True
    )


def main():
    report = {"scope": __doc__, "checks": [], "memory_writes": 0}
    s = Store(OUT / "profile")
    with s.lock():
        for slot, enabled in [(1, False), (2, True)]:
            r = Runtime(s)
            try:
                assert r.start(slot) == "First World - Prehistorik"
                time.sleep(1)
                obs = objects(r.reader)
                player = [o for o in obs if o["name"] == "Player"]
                assert len(player) == 1, player
                before = s.summary(slot)
                snap(r, f"god-{enabled}-before")
                print("START", enabled, player, flush=True)
                # Real mouse hazard: move onto the visible player, then leave it there.
                point(r, player[0]["x"], player[0]["y"])
                samples = []
                for i in range(8):
                    time.sleep(0.5)
                    obs = objects(r.reader)
                    samples.append(
                        [o for o in obs if o["name"] in ("Player", "mouse kill")]
                    )
                snap(r, f"god-{enabled}-mouse")
                alive = any(o["name"] == "Player" for o in obs)
                assert alive == enabled, (enabled, alive, samples)
                if enabled:
                    assert any(
                        any(o["name"] == "mouse kill" for o in sample)
                        for sample in samples
                    )
                # Q must still produce normal player death even with God Mode on.
                if enabled:
                    r.key("q")
                    time.sleep(1)
                    assert not any(o["name"] == "Player" for o in objects(r.reader))
                    snap(r, "god-on-Q-death")
                r.key("r")
                time.sleep(1)
                assert any(o["name"] == "Player" for o in objects(r.reader))
                snap(r, f"god-{enabled}-restarted")
                r.key("F2")
                end = time.monotonic() + 15
                while time.monotonic() < end and r.poll() != "menu":
                    time.sleep(0.2)
                assert s.active is None and not windows() and not games()
                after = s.summary(slot)
                assert after["deaths"] > before["deaths"]
                assert after["seed"] == before["seed"]
                report["checks"].append(
                    dict(
                        god_mode=enabled,
                        passed=True,
                        before=before,
                        after=after,
                        samples=samples,
                        mouse_hazard="survived" if enabled else "died",
                        q_death_checked=enabled,
                        restart=True,
                    )
                )
                print("PASS", enabled, flush=True)
            finally:
                if s.active:
                    r.close("god-probe-cleanup")
                (OUT / "live-results.json").write_text(
                    json.dumps(report, indent=2) + "\n"
                )
        report["passed"] = True
        (OUT / "live-results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
