import os
import random
import json
from .logger import log
from .config import positions_json

# ======================================================
# ROUTE BUILDER (JSON-basiert)
# ======================================================
def build_random_route(cfg, pos_data=None):
    """
    Build a random route using data from positions.json.
    - Supports passing in-memory data (pos_data) to avoid reloading file.
    - Respects disabled bosses/rooms.
    - Always ends with boss_solgryn.ini.
    """

    # --- Load or use passed positions data ---
    if pos_data and isinstance(pos_data, dict):
        data = pos_data
    else:
        if not os.path.exists(positions_json):
            log("⚠️ positions.json missing – cannot build route!")
            return []
        try:
            with open(positions_json, "r", encoding="utf-8") as f:
                raw = json.load(f)
            data = {
                "rooms": raw.get("rooms") or raw.get("Rooms") or {},
                "bosses": raw.get("bosses") or raw.get("Bosses") or {}
            }
        except Exception as e:
            log(f"⚠️ Failed to read positions.json: {e}")
            return []

    # --- Collect stage names ---
    all_rooms = [r.lower() for r in data.get("rooms", {}).keys()]
    all_bosses = [b.lower() for b in data.get("bosses", {}).keys()]

    if not all_rooms and not all_bosses:
        log("⚠️ positions.json appears empty or invalid.")
        return []

    # --- Filter disabled content ---
    enabled_rooms = [r for r in all_rooms if r not in [x.lower() for x in cfg.disabled_rooms]]
    enabled_bosses = [b for b in all_bosses if b not in [x.lower() for x in cfg.disabled_bosses] and b != "boss_solgryn.ini"]

    # --- Warn if pools are empty ---
    if not enabled_rooms and not cfg.only_bosses:
        log("⚠️ No enabled rooms available in positions.json.")
    if not enabled_bosses and not cfg.only_rooms:
        log("⚠️ No enabled bosses available in positions.json.")

    route = []

    # --- Only Bosses Mode ---
    if cfg.only_bosses:
        count = min(cfg.bosses_to_play, len(enabled_bosses))
        route = random.sample(enabled_bosses, count) if enabled_bosses else []

    # --- Only Levels Mode ---
    elif cfg.only_rooms:
        count = min(cfg.rooms_to_play, len(enabled_rooms))
        route = random.sample(enabled_rooms, count) if enabled_rooms else []

    # --- Mixed Mode ---
    else:
        bosses_count = min(cfg.bosses_to_play, len(enabled_bosses))
        rooms_count = min(cfg.rooms_to_play, len(enabled_rooms))
        total_steps = bosses_count + rooms_count

        for i in range(total_steps):
            # We alternate: start with Room
            if i % 2 == 0 and enabled_rooms:
                choice = random.choice(enabled_rooms)
                route.append(choice)
                enabled_rooms.remove(choice)
            elif enabled_bosses:
                choice = random.choice(enabled_bosses)
                route.append(choice)
                enabled_bosses.remove(choice)

    # --- Always end with boss_solgryn.ini ---
    if "boss_solgryn.ini" not in route:
        route.append("boss_solgryn.ini")

    # --- Log result ---
    if route:
        log("Route built from positions.json: " + " -> ".join(route))
    else:
        log("⚠️ Route could not be built (no valid entries found).")

    return route
