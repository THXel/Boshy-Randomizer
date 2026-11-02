"""Native God Mode with all sprite categories and boss fire phases.

Only boss HP and test-entry positions are staged. No death-loop/event edits or
runtime invulnerability patches: protection comes exclusively from the new EXE
and the exported per-run setting. These are phase tests, not complete fights.
"""

import io, json, struct, time, sys
from menu_host.store import Store, save, RC4
from transition.router import STAGES, GROUP as ROUTE_GROUP
from menu_host.draft import Draft
from menu_host.runtime import Runtime
from god_mode_live import objects, snap, OUT


def values(reader, obj, n=5):
    p = reader.u32(obj["ptr"] + obj["rel"])
    data = reader.read(p, n * 16)
    return [
        struct.unpack_from(
            "<i" if struct.unpack_from("<I", data, i * 16)[0] == 0 else "<d",
            data,
            i * 16 + 8,
        )[0]
        for i in range(n)
    ]


def cas(runtime, address, value, reason, writes):
    assert runtime.owned()
    old = runtime.reader.u32(address)
    runtime.reader.p.stdin.write(f"cas32 {address:x} {old:x} {value&0xffffffff:x}\n")
    runtime.reader.p.stdin.flush()
    ok = runtime.reader.line()["written"]
    if ok:
        writes.append(dict(address=address, old=old, new=value, reason=reason))
    return ok


def position(runtime, obj, x, y, writes):
    assert obj["name"] == "Player"
    for offset, value in [(76, x), (84, y)]:
        for attempt in range(4):
            assert (
                struct.unpack_from("<H", runtime.reader.read(obj["ptr"], 32), 0)[0]
                == obj["slot"]
            )
            if cas(
                runtime,
                obj["ptr"] + offset,
                value,
                "player test-entry position",
                writes,
            ):
                break
        else:
            raise RuntimeError("Moving position fixture")


def main():
    report = (
        json.loads((OUT / "boss-results.json").read_text())
        if len(sys.argv) > 1
        else {"scope": __doc__, "cases": []}
    )
    store = Store(OUT / "boss-profile")
    with store.lock():
        for slot, scene, bosskey in [
            (1, "sonic", "sonic"),
            (2, "oldsonic", "oldsonic"),
            (3, "solgryn", None),
        ]:
            if len(sys.argv) > 1 and scene != sys.argv[1]:
                continue
            if not store.current(slot):
                d = Draft()
                d.update(
                    level_pool=[],
                    level_count=0,
                    boss_pool=[bosskey] if bosskey else ["hellokitty"],
                    route_boss_count=1,
                    god_mode=True,
                    sprite_scenery=True,
                    sprite_backgrounds=True,
                    sprite_decor=True,
                    sprite_tiles=True,
                    sprite_actors=True,
                    music=True,
                )
                d.select_pack("music_pack", "kamilia3")
                d.select_pack("blood_pack", "wannafest22")
                store.create(slot, d)
                if scene == "solgryn":
                    # Enter the finale checkpoint directly in this private test save.
                    path = store.folder(slot) / "SaveFile1.ini"
                    c = save(path)
                    stage = STAGES["boss_solgryn.ini"]
                    c[ROUTE_GROUP]["CurrentStage"] = str(stage["id"])
                    for key, field in (
                        ("frame", "frame"),
                        ("xpos", "x"),
                        ("ypos", "y"),
                    ):
                        c["Positions"][key] = str(stage[field])
                    buf = io.StringIO()
                    c.write(buf)
                    path.write_bytes(RC4(b"BLOB", buf.getvalue().encode("latin1")))
            r = Runtime(store)
            case = dict(
                scene=scene,
                checkpoint_fixture=(scene == "solgryn"),
                writes=[],
                samples=[],
            )
            report["cases"].append(case)
            try:
                case["frame"] = r.start(slot)
                time.sleep(0.7)
                obs = objects(r.reader)
                name = "randomness" if scene == "solgryn" else "Active 4sonic"
                boss = next(o for o in obs if o["name"] == name)
                case["boss_before"] = values(r.reader, boss)
                index = 3 if scene == "solgryn" else 1
                target = 0 if scene == "solgryn" else 35
                address = r.reader.u32(boss["ptr"] + boss["rel"]) + index * 16
                assert r.reader.u32(address) == 0
                assert cas(
                    r,
                    address + 8,
                    target,
                    "boss HP phase-entry fixture",
                    case["writes"],
                )
                if scene != "solgryn":
                    position(
                        r,
                        next(o for o in obs if o["name"] == "Player"),
                        320,
                        400,
                        case["writes"],
                    )
                start = time.monotonic()
                entered = False
                while time.monotonic() - start < (63 if scene == "solgryn" else 34):
                    obs = objects(r.reader)
                    boss = next((o for o in obs if o["name"] == name), None)
                    vals = values(r.reader, boss) if boss else []
                    player = next((o for o in obs if o["name"] == "Player"), None)
                    assert player, "Native God Mode did not protect the player"
                    if scene == "solgryn" and vals and vals[0] == 5999 and not entered:
                        position(r, player, 300, -8, case["writes"])
                        entered = True
                    case["samples"].append(
                        dict(
                            seconds=round(time.monotonic() - start, 2),
                            boss_values=vals,
                            player=player,
                            objects=[
                                o
                                for o in obs
                                if "sonic" in o["name"].lower()
                                or (
                                    scene == "solgryn"
                                    and o["name"]
                                    in (
                                        "Active 9",
                                        "Active 10",
                                        "Active 14",
                                        "randomness",
                                    )
                                )
                            ],
                        )
                    )
                    if len(case["samples"]) % 15 == 0:
                        snap(r, scene + "-fire-" + str(len(case["samples"])))
                        print(
                            scene, round(time.monotonic() - start, 1), vals, flush=True
                        )
                    time.sleep(0.35)
                snap(r, scene + "-fire-final")
                if scene == "solgryn":
                    names = {
                        o["name"]
                        for sample in case["samples"]
                        for o in sample["objects"]
                    }
                    assert entered and {"Active 9", "Active 10"} <= names, (
                        entered,
                        names,
                    )
                else:
                    widths = {
                        o["w"]
                        for sample in case["samples"]
                        for o in sample["objects"]
                        if o["name"] == "Active 23sonic"
                    }
                    assert widths and min(widths) == 168, widths
                    case["platform_widths"] = sorted(widths)
                    obs = objects(r.reader)
                    boss = next(o for o in obs if o["name"] == name)
                    position(
                        r,
                        next(o for o in obs if o["name"] == "Player"),
                        boss["x"],
                        boss["y"],
                        case["writes"],
                    )
                    time.sleep(1)
                    assert any(o["name"] == "Player" for o in objects(r.reader))
                r.key("q")
                time.sleep(1)
                assert not any(o["name"] == "Player" for o in objects(r.reader))
                snap(r, scene + "-Q-death")
                r.key("r")
                time.sleep(1)
                assert any(o["name"] == "Player" for o in objects(r.reader))
                snap(r, scene + "-restart")
                r.close("god-boss-probe")
                case["saved"] = store.summary(slot)
                case["passed"] = True
                print("PASS", scene, flush=True)
            finally:
                if store.active:
                    r.close("probe-cleanup")
                (OUT / "boss-results.json").write_text(
                    json.dumps(report, indent=2) + "\n"
                )
        report["passed"] = len(report["cases"]) == 3 and all(
            c.get("passed") for c in report["cases"]
        )
        (OUT / "boss-results.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
