import os
import random
import json
from .logger import log
from .config import positions_json

# ======================================================
# ROUTE BUILDER (JSON-basiert) mit No-Repeat-Cycle
#   - Nutzt positions.json als Quelle für rooms/bosses
#   - Respektiert disabled_rooms / disabled_bosses aus cfg
#   - Unterstützt:
#       * only_bosses
#       * only_rooms
#       * Mixed Mode (abwechselnd)
#   - Innerhalb eines Runs sowieso keine Duplikate
#   - NEU: No-Repeat-Cycle über mehrere Runs:
#       * Alle Rooms/Bosse werden zyklisch benutzt, bevor sie erneut drankommen
#       * Berücksichtigt die aktuell erlaubten (enabled) Pools
#   - Route endet immer mit boss_solgryn.ini
#
#   NEU: Seed-Unterstützung (cfg.route_seed)
#       * Wenn cfg.route_seed gesetzt ist:
#           - Route wird deterministisch mit random.Random(seed) gebaut
#           - No-Repeat-Globalpools (_ROOM_POOL/_BOSS_POOL) werden ignoriert
#       * Wenn kein Seed: Verhalten wie vorher (No-Repeat-Cycle)
# ======================================================

# Globale Pools (über den Prozess / mehrere Runs)
_ROOM_POOL: list[str] | None = None
_BOSS_POOL: list[str] | None = None
_ROOM_UNUSED: list[str] = []
_BOSS_UNUSED: list[str] = []


def _load_positions(pos_data=None):
    """positions.json lesen oder pos_data verwenden, ruft auch _init_pools()."""
    global _ROOM_POOL, _BOSS_POOL, _ROOM_UNUSED, _BOSS_UNUSED

    if pos_data and isinstance(pos_data, dict):
        raw = pos_data
    else:
        if not os.path.exists(positions_json):
            log("⚠️ positions.json missing – cannot build route!")
            return {"rooms": {}, "bosses": {}}
        try:
            with open(positions_json, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception as e:
            log(f"⚠️ Failed to read positions.json: {e}")
            return {"rooms": {}, "bosses": {}}

    data = {
        "rooms": raw.get("rooms") or raw.get("Rooms") or {},
        "bosses": raw.get("bosses") or raw.get("Bosses") or {},
    }

    # Pools nur einmal initialisieren (oder wenn noch leer)
    if _ROOM_POOL is None:
        _ROOM_POOL = sorted(r.lower() for r in data["rooms"].keys())
        _ROOM_UNUSED = list(_ROOM_POOL)
        random.shuffle(_ROOM_UNUSED)
        log(f"📦 Room pool initialized with {len(_ROOM_POOL)} entries.")

    if _BOSS_POOL is None:
        # Solgryn kommt sowieso immer ans Ende, also nicht in den Boss-Pool nehmen
        _BOSS_POOL = sorted(
            b.lower()
            for b in data["bosses"].keys()
            if b.lower() != "boss_solgryn.ini"
        )
        _BOSS_UNUSED = list(_BOSS_POOL)
        random.shuffle(_BOSS_UNUSED)
        log(f"📦 Boss pool initialized with {len(_BOSS_POOL)} entries.")

    return data


def _take_from_cycle(all_names: list[str],
                     unused_list: list[str],
                     enabled_set: set[str],
                     label: str) -> str | None:
    """
    No-Repeat-Auswahl:
      - nimmt möglichst Einträge aus unused_list, die in enabled_set liegen
      - wenn keine passenden mehr da → Cycle refresh (unused_list = all_names, shuffle)
      - wenn dann immer noch nichts geht → Fallback random.choice(enabled_set)
    """
    if not enabled_set:
        return None

    # Versuche, aus dem aktuellen Zyklus einen gültigen Eintrag zu holen
    for idx, name in enumerate(unused_list):
        if name in enabled_set:
            choice = unused_list.pop(idx)
            return choice

    # Kein passender Eintrag im aktuellen Zyklus → neuen Zyklus starten
    if all_names:
        unused_list[:] = list(all_names)
        random.shuffle(unused_list)
        log(f"🔁 {label} cycle refreshed (size={len(unused_list)})")

        for idx, name in enumerate(unused_list):
            if name in enabled_set:
                choice = unused_list.pop(idx)
                return choice

    # Wenn immer noch nichts → Fallback
    if enabled_set:
        choice = random.choice(list(enabled_set))
        log(f"⚠️ {label} cycle fallback hit → {choice}")
        return choice

    return None


def _take_seeded_from(rnd: random.Random,
                      enabled_set: set[str]) -> str | None:
    """
    Seeded-Auswahl:
      - benutzt eine lokale random.Random-Instanz (rnd)
      - wählt deterministisch ein Element aus enabled_set und entfernt es daraus
    """
    if not enabled_set:
        return None
    choices = sorted(enabled_set)  # sortiert für deterministische Reihenfolge
    choice = rnd.choice(choices)
    enabled_set.remove(choice)
    return choice


# ======================================================
# PUBLIC API
# ======================================================
def build_random_route(cfg, pos_data=None):
    """
    Build a random route using data from positions.json.
    - Supports passing in-memory data (pos_data) to avoid reloading file.
    - Respects disabled bosses/rooms.
    - Always ends with boss_solgryn.ini.
    - Nutzt No-Repeat-Cycle-Pools für Rooms/Bosse über mehrere Runs.
    - NEU: Wenn cfg.route_seed gesetzt ist, wird eine deterministische
      Route mit random.Random(seed) gebaut (ohne globale Pools).
    """

    data = _load_positions(pos_data)
    rooms_dict = data.get("rooms", {}) or {}
    bosses_dict = data.get("bosses", {}) or {}

    # --- Collect stage names (alles klein) ---
    all_rooms = [r.lower() for r in rooms_dict.keys()]
    all_bosses = [b.lower() for b in bosses_dict.keys()]

    if not all_rooms and not all_bosses:
        log("⚠️ positions.json appears empty or invalid.")
        return []

    # --- Filter disabled content ---
    disabled_rooms_l = [x.lower() for x in getattr(cfg, "disabled_rooms", [])]
    disabled_bosses_l = [x.lower() for x in getattr(cfg, "disabled_bosses", [])]

    enabled_rooms = [r for r in all_rooms if r not in disabled_rooms_l]
    enabled_bosses = [
        b for b in all_bosses
        if b not in disabled_bosses_l and b != "boss_solgryn.ini"
    ]

    # --- Warn if pools are empty ---
    if not enabled_rooms and not getattr(cfg, "only_bosses", False):
        log("⚠️ No enabled rooms available in positions.json.")
    if not enabled_bosses and not getattr(cfg, "only_rooms", False):
        log("⚠️ No enabled bosses available in positions.json.")

    route: list[str] = []

    # Um mit Sets/Restmengen zu arbeiten
    enabled_room_set = set(enabled_rooms)
    enabled_boss_set = set(enabled_bosses)

    # --- Seed-Handling ---
    seed = getattr(cfg, "route_seed", None)
    use_seed = seed is not None
    if use_seed:
        try:
            seed_int = int(seed)
        except Exception:
            seed_int = None
            use_seed = False
        if seed_int is not None:
            rnd = random.Random(seed_int)
            log(f"🎲 Using route seed: {seed_int}")
        else:
            rnd = random

    # ======================================================
    # SEEDED MODE – deterministisch mit random.Random(seed)
    # ======================================================
    if use_seed:
        # --- Only Bosses Mode ---
        if getattr(cfg, "only_bosses", False):
            count = min(getattr(cfg, "bosses_to_play", 0), len(enabled_bosses))
            pool = list(enabled_bosses)
            rnd.shuffle(pool)
            route.extend(pool[:count])

        # --- Only Levels Mode ---
        elif getattr(cfg, "only_rooms", False):
            count = min(getattr(cfg, "rooms_to_play", 0), len(enabled_rooms))
            pool = list(enabled_rooms)
            rnd.shuffle(pool)
            route.extend(pool[:count])

        # --- Mixed Mode ---
        else:
            bosses_count = min(getattr(cfg, "bosses_to_play", 0), len(enabled_bosses))
            rooms_count = min(getattr(cfg, "rooms_to_play", 0), len(enabled_rooms))
            total_steps = bosses_count + rooms_count

            rooms_left = rooms_count
            bosses_left = bosses_count

            for i in range(total_steps):
                # Wie im normalen Modus: bevorzugt Room an geraden Stellen
                if (i % 2 == 0 and rooms_left > 0 and enabled_room_set):
                    choice = _take_seeded_from(rnd, enabled_room_set)
                    if choice:
                        route.append(choice)
                        rooms_left -= 1
                else:
                    if bosses_left > 0 and enabled_boss_set:
                        choice = _take_seeded_from(rnd, enabled_boss_set)
                        if choice:
                            route.append(choice)
                            bosses_left -= 1
                    else:
                        # Fallback: wenn keine Bosse mehr, aber noch Rooms
                        if rooms_left > 0 and enabled_room_set:
                            choice = _take_seeded_from(rnd, enabled_room_set)
                            if choice:
                                route.append(choice)
                                rooms_left -= 1

    # ======================================================
    # NORMAL MODE – wie bisher, mit No-Repeat-Cycle
    # ======================================================
    else:
        # --- Only Bosses Mode ---
        if getattr(cfg, "only_bosses", False):
            count = min(getattr(cfg, "bosses_to_play", 0), len(enabled_bosses))
            for _ in range(count):
                choice = _take_from_cycle(
                    _BOSS_POOL or enabled_bosses,
                    _BOSS_UNUSED,
                    enabled_boss_set,
                    "Boss"
                )
                if not choice:
                    break
                route.append(choice)
                if choice in enabled_boss_set:
                    enabled_boss_set.remove(choice)

        # --- Only Levels Mode ---
        elif getattr(cfg, "only_rooms", False):
            count = min(getattr(cfg, "rooms_to_play", 0), len(enabled_rooms))
            for _ in range(count):
                choice = _take_from_cycle(
                    _ROOM_POOL or enabled_rooms,
                    _ROOM_UNUSED,
                    enabled_room_set,
                    "Room"
                )
                if not choice:
                    break
                route.append(choice)
                if choice in enabled_room_set:
                    enabled_room_set.remove(choice)

        # --- Mixed Mode ---
        else:
            bosses_count = min(getattr(cfg, "bosses_to_play", 0), len(enabled_bosses))
            rooms_count = min(getattr(cfg, "rooms_to_play", 0), len(enabled_rooms))
            total_steps = bosses_count + rooms_count

            rooms_left = rooms_count
            bosses_left = bosses_count

            for i in range(total_steps):
                # Start mit Room, dann Boss, usw., aber nur wenn noch etwas übrig ist
                if (i % 2 == 0 and rooms_left > 0 and enabled_room_set):
                    choice = _take_from_cycle(
                        _ROOM_POOL or enabled_rooms,
                        _ROOM_UNUSED,
                        enabled_room_set,
                        "Room"
                    )
                    if choice:
                        route.append(choice)
                        rooms_left -= 1
                        if choice in enabled_room_set:
                            enabled_room_set.remove(choice)
                    else:
                        # kein Room möglich → versuche Boss
                        if bosses_left > 0 and enabled_boss_set:
                            choice_b = _take_from_cycle(
                                _BOSS_POOL or enabled_bosses,
                                _BOSS_UNUSED,
                                enabled_boss_set,
                                "Boss"
                            )
                            if choice_b:
                                route.append(choice_b)
                                bosses_left -= 1
                                if choice_b in enabled_boss_set:
                                    enabled_boss_set.remove(choice_b)
                else:
                    if bosses_left > 0 and enabled_boss_set:
                        choice = _take_from_cycle(
                            _BOSS_POOL or enabled_bosses,
                            _BOSS_UNUSED,
                            enabled_boss_set,
                            "Boss"
                        )
                        if choice:
                            route.append(choice)
                            bosses_left -= 1
                            if choice in enabled_boss_set:
                                enabled_boss_set.remove(choice)
                        else:
                            # kein Boss möglich → versuche Room
                            if rooms_left > 0 and enabled_room_set:
                                choice_r = _take_from_cycle(
                                    _ROOM_POOL or enabled_rooms,
                                    _ROOM_UNUSED,
                                    enabled_room_set,
                                    "Room"
                                )
                                if choice_r:
                                    route.append(choice_r)
                                    rooms_left -= 1
                                    if choice_r in enabled_room_set:
                                        enabled_room_set.remove(choice_r)

    # --- Always end with boss_solgryn.ini ---
    if "boss_solgryn.ini" not in route:
        route.append("boss_solgryn.ini")

    # --- Log result ---
    if route:
        log("Route built from positions.json: " + " -> ".join(route))
    else:
        log("⚠️ Route could not be built (no valid entries found).")

    return route
