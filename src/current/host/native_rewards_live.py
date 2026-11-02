"""Real mixed pickups and receipt persistence with isolated position fixtures.

No runtime writes. Chest collisions, rewards, Q/R and reopen are handled by the
native engine. The first pair proves that owning Luigi cannot hide his chest.
"""

import io, json, time, uuid, sys
from menu_host.store import Store, save, RC4
from menu_host.draft import Draft
from menu_host.runtime import Runtime
from native_menu.observe import objects
from native_pickups_live import ITEMS, dialogs, close_dialog, player
from export_route_probe import ROOT
from gameplay.reward_plan import LOCATIONS
import god_mode_live as capture

OUT = ROOT / "outputs/Fusion-NativeRewards-20261024"
KEYS = {
    "cd": "I00A4",
    "luigi": "L0122",
    "mixer": "I00C7",
    "timer": "I0311",
    "scouter": "I0452",
    "item": "I0098",
}


def write_save(path, c):
    buf = io.StringIO()
    c.write(buf)
    path.write_bytes(RC4(b"BLOB", buf.getvalue().encode("latin1")))


def chest_ids(r):
    return {o["name"] for o in objects(r.reader)}


def run_case(s, r, folder, name, fast, quiet, report):
    loc = ITEMS[name]
    key = KEYS[name]
    p = json.loads((folder / "plan.json").read_text())
    reward = p["rewards"][key]
    expected_group = "Unlockables" if reward["kind"] == "character" else "Collectables"
    case = dict(name=name, key=key, reward=reward, fast=fast, quiet=quiet, dialogs=[])
    report["cases"].append(case)
    c = save(folder / "SaveFile1.ini")
    c["Positions"]["xpos"] = str(loc[2])
    c["Positions"]["ypos"] = str(loc[3] - 8)
    write_save(folder / "SaveFile1.ini", c)
    case["frame"] = r.start(1)
    start = time.monotonic()
    print("START", name, reward, flush=True)
    captured = False
    while time.monotonic() - start < 12:
        for row in dialogs(r):
            case["dialogs"].append(row[4])
            assert not quiet and row[4] == "RANDOMIZER", row
            capture.snap(r, name + "-dialog")
            close_dialog(row)
        obs = player(r)
        elapsed = time.monotonic() - start
        if not captured and obs["timer"] >= 1 and (fast or obs["timer"] >= 250):
            capture.snap(r, name + "-reward")
            captured = True
        if loc[1] not in chest_ids(r) and not obs["pickup_active"]:
            case["released_seconds"] = round(elapsed, 3)
            break
        time.sleep(0.04)
    assert "released_seconds" in case, (name, player(r))
    assert bool(case["dialogs"]) == bool(loc[-1] and not quiet)
    if name == "cd":
        assert "Active 65" in chest_ids(r), (
            "Luigi chest disappeared merely because Luigi was unlocked"
        )
        case["other_chest_retained"] = True
    r.key("q")
    time.sleep(0.25)
    r.key("r")
    time.sleep(0.25)
    assert loc[1] not in chest_ids(r)
    r.close("reward-restart")
    s.resume(1)
    c = save(folder / "SaveFile1.ini")
    profile = save(
        folder
        / ("onlineLicense.ini" if expected_group == "Unlockables" else "SaveFile1.ini")
    )
    assert profile.getint(expected_group, reward["name"], fallback=0) == 1, (
        name,
        reward,
    )
    assert c.getint("RandoChecks", key, fallback=0) == 1
    ownloc = next(l for l in LOCATIONS if l["key"] == key)
    if ownloc["source"] != reward["name"]:
        original = save(
            folder
            / (
                "onlineLicense.ini"
                if ownloc["source_kind"] == "character"
                else "SaveFile1.ini"
            )
        )
        # Luigi was legitimately awarded by the first chest in the paired case.
        if name != "luigi":
            assert (
                original.getint(ownloc["inventory"], ownloc["source"], fallback=0) == 0
            )
    before = {
        section: dict(c[section])
        for section in ("Collectables", "RandoChecks")
        if c.has_section(section)
    }
    license_before = (
        dict(save(folder / "onlineLicense.ini")["Unlockables"])
        if (folder / "onlineLicense.ini").exists()
        and save(folder / "onlineLicense.ini").has_section("Unlockables")
        else {}
    )
    r.start(1)
    time.sleep(0.2)
    assert loc[1] not in chest_ids(r)
    r.close("reward-resume")
    s.resume(1)
    c = save(folder / "SaveFile1.ini")
    assert before == {
        section: dict(c[section])
        for section in ("Collectables", "RandoChecks")
        if c.has_section(section)
    }
    license_after = (
        dict(save(folder / "onlineLicense.ini")["Unlockables"])
        if (folder / "onlineLicense.ini").exists()
        and save(folder / "onlineLicense.ini").has_section("Unlockables")
        else {}
    )
    assert license_before == license_after
    case.update(
        saved_reward=True, receipt=True, no_duplicate_after_restart=True, passed=True
    )
    print("PASS", name, flush=True)


def main():
    capture.OUT = OUT
    result = OUT / "live-results.json"
    report = dict(scope=__doc__, memory_writes=0, cases=[])
    batches = [
        (["cd", "luigi"], "0000001D", True, False),
        (["mixer"], "ABCDEF12", False, True),
        (["timer"], "10203040", True, True),
        (["scouter"], "ABCDEF12", True, True),
        (["item"], "0000001D", True, True),
    ]
    try:
        for names, seed, fast, quiet in batches:
            if len(sys.argv) > 1 and names[0] not in sys.argv[1:]:
                continue
            s = Store(OUT / ("profile-" + names[0] + "-" + uuid.uuid4().hex[:6]))
            with s.lock():
                d = Draft()
                d.update(
                    level_pool=[ITEMS[names[0]][0]],
                    level_count=1,
                    boss_pool=[],
                    route_boss_count=0,
                    items=True,
                    god_mode=True,
                    no_mouse_ghost=True,
                    fast_chests=fast,
                    quiet_pickups=quiet,
                    start_character="Kirby",
                )
                d.seed = seed
                s.create(1, d)
                folder = s.folder(1)
                r = Runtime(s)
                try:
                    for name in names:
                        run_case(s, r, folder, name, fast, quiet, report)
                finally:
                    for row in dialogs(r) if r.pid else []:
                        close_dialog(row)
                    if s.active:
                        r.close("reward-cleanup")
        report["passed"] = len(report["cases"]) == 6 and all(
            c.get("passed") for c in report["cases"]
        )
    except BaseException as e:
        report["error"] = repr(e)
        raise
    finally:
        result.write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
