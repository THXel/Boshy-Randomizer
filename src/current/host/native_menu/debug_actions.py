"""Explicit, reversible test edits made only to inactive, validated run copies.

A slot pointer is the commit: failures never change the original. No process
memory writes, route rewiring, fabricated chest receipts or victory awards.
"""

import io
import json
import shutil
import time
import uuid
from menu_host.store import atomic, save, RC4
from transition.router import STAGES, GROUP
from gameplay.reward_plan import LOCATIONS

MARKER = "RandomizerDebug"
TEST_LABELS = (
    "Testlauf",
    "Test run",
    "Partida de prueba",
    "Тестовый забег",
    "テストプレイ",
)
ITEMS = sorted(
    {r["source"] for r in LOCATIONS if r["source_kind"] == "item"} | {"Gastly"}
)
CHARACTERS = sorted({r["source"] for r in LOCATIONS if r["source_kind"] == "character"})


def destinations(plan):
    mode = plan["options"]["mode"]
    spots = list(STAGES) if mode in ("normal", "target") else plan["route"]
    # Target finale remains gated by actual goals, even inside test copies.
    return [s for s in spots if not (mode == "target" and s == "boss_solgryn.ini")]


def write_ini(path, config):
    stream = io.StringIO()
    config.write(stream)
    atomic(path, RC4(b"BLOB", stream.getvalue().encode("latin1")))


def prepare(store, slot, operation, value):
    store.writable()
    old = store.current(slot)
    source, plan, _ = store.resume(slot)
    allowed = (
        destinations(plan)
        if operation == "teleport"
        else (
            ITEMS
            if operation == "item"
            else CHARACTERS if operation == "character" else ()
        )
    )
    if value not in allowed:
        raise ValueError("Unknown or unavailable test action")
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("Linked test-copy source")
    folder = store.runs / ("rebuilt-menu-" + uuid.uuid4().hex)
    try:
        shutil.copytree(source, folder)
        config = save(folder / "SaveFile1.ini")
        if config.getint(GROUP, "Completed", fallback=0):
            raise ValueError("Use an unfinished run for test actions")
        if operation == "teleport":
            stage = STAGES[value]
            config["Positions"].update(
                frame=str(stage["frame"]), xpos=str(stage["x"]), ypos=str(stage["y"])
            )
            if plan["options"]["mode"] != "normal":
                config[GROUP]["CurrentStage"] = str(stage["id"])
            for key in ("Handled", "Armed", "KrackoVictory", "KidSeen"):
                config[GROUP][key] = "0"
        elif operation == "item":
            if not config.has_section("Collectables"):
                config.add_section("Collectables")
            config["Collectables"][value] = "1"
        else:
            profile = save(folder / "onlineLicense.ini")
            if not profile.has_section("Unlockables"):
                profile.add_section("Unlockables")
            profile["Unlockables"][value] = "1"
            write_ini(folder / "onlineLicense.ini", profile)
        config[MARKER] = {"Enabled": "1"}
        write_ini(folder / "SaveFile1.ini", config)
        meta = dict(
            old,
            run=folder.name,
            test_run=True,
            debug_original=old.get("debug_original", old),
        )
        store.validate_folder(folder, meta)
        history = (
            json.loads((folder / "debug-actions.json").read_text())
            if (folder / "debug-actions.json").exists()
            else []
        )
        history.append(dict(time=time.time(), operation=operation, value=value))
        atomic(
            folder / "debug-actions.json",
            json.dumps(history[-100:], ensure_ascii=False).encode(),
        )
        # New identity must never reuse the original run's completion or clock receipt.
        for name in ("result.json", "tracker-clock.json"):
            (folder / name).unlink(missing_ok=True)
        atomic(store.pointer(slot), json.dumps(meta, indent=2).encode())
        return meta
    except Exception:
        if folder.exists():
            shutil.rmtree(folder)
        raise


def restore(store, slot):
    store.writable()
    meta = store.current(slot)
    original = meta.get("debug_original") if meta else None
    if not isinstance(original, dict):
        raise ValueError("No original run to restore")
    # Validate via the same path and identity boundary as normal slot loading.
    name = original.get("run", "")
    if (
        len(name) != 45
        or not name.startswith("rebuilt-menu-")
        or any(c not in "0123456789abcdef" for c in name[13:])
    ):
        raise ValueError("Invalid original run reference")
    folder = store.runs / name
    if folder.is_symlink():
        raise ValueError("Linked original run")
    store.validate_folder(folder, original)
    atomic(store.pointer(slot), json.dumps(original, indent=2).encode())
    return original
