import os
import random
import json
from .logger import log
from .config import positions_json
_ROOM_POOL: list[str] | None = None
_BOSS_POOL: list[str] | None = None
_ROOM_UNUSED: list[str] = []
_BOSS_UNUSED: list[str] = []
def _load_positions(pos_data=None):
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
    if _ROOM_POOL is None:
        _ROOM_POOL = sorted(r.lower() for r in data["rooms"].keys())
        _ROOM_UNUSED = list(_ROOM_POOL)
        random.shuffle(_ROOM_UNUSED)
        log(f"📦 Room pool initialized with {len(_ROOM_POOL)} entries.")
    if _BOSS_POOL is None:
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
\
\
\
\
\
    if not enabled_set:
        return None
    for idx, name in enumerate(unused_list):
        if name in enabled_set:
            choice = unused_list.pop(idx)
            return choice
    if all_names:
        unused_list[:] = list(all_names)
        random.shuffle(unused_list)
        log(f"🔁 {label} cycle refreshed (size={len(unused_list)})")
        for idx, name in enumerate(unused_list):
            if name in enabled_set:
                choice = unused_list.pop(idx)
                return choice
    if enabled_set:
        choice = random.choice(list(enabled_set))
        log(f"⚠️ {label} cycle fallback hit → {choice}")
        return choice
    return None
def _take_seeded_from(rnd: random.Random,
                      enabled_set: set[str]) -> str | None:
\
\
\
\
    if not enabled_set:
        return None
    choices = sorted(enabled_set)
    choice = rnd.choice(choices)
    enabled_set.remove(choice)
    return choice
def build_random_route(cfg, pos_data=None):
\
\
\
\
\
\
\
\
    data = _load_positions(pos_data)
    rooms_dict = data.get("rooms", {}) or {}
    bosses_dict = data.get("bosses", {}) or {}
    all_rooms = [r.lower() for r in rooms_dict.keys()]
    all_bosses = [b.lower() for b in bosses_dict.keys()]
    if not all_rooms and not all_bosses:
        log("⚠️ positions.json appears empty or invalid.")
        return []
    disabled_rooms_l = [x.lower() for x in getattr(cfg, "disabled_rooms", [])]
    disabled_bosses_l = [x.lower() for x in getattr(cfg, "disabled_bosses", [])]
    enabled_rooms = [r for r in all_rooms if r not in disabled_rooms_l]
    enabled_bosses = [
        b for b in all_bosses
        if b not in disabled_bosses_l and b != "boss_solgryn.ini"
    ]
    if not enabled_rooms and not getattr(cfg, "only_bosses", False):
        log("⚠️ No enabled rooms available in positions.json.")
    if not enabled_bosses and not getattr(cfg, "only_rooms", False):
        log("⚠️ No enabled bosses available in positions.json.")
    route: list[str] = []
    enabled_room_set = set(enabled_rooms)
    enabled_boss_set = set(enabled_bosses)
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
    if use_seed:
        if getattr(cfg, "only_bosses", False):
            count = min(getattr(cfg, "bosses_to_play", 0), len(enabled_bosses))
            pool = list(enabled_bosses)
            rnd.shuffle(pool)
            route.extend(pool[:count])
        elif getattr(cfg, "only_rooms", False):
            count = min(getattr(cfg, "rooms_to_play", 0), len(enabled_rooms))
            pool = list(enabled_rooms)
            rnd.shuffle(pool)
            route.extend(pool[:count])
        else:
            bosses_count = min(getattr(cfg, "bosses_to_play", 0), len(enabled_bosses))
            rooms_count = min(getattr(cfg, "rooms_to_play", 0), len(enabled_rooms))
            total_steps = bosses_count + rooms_count
            rooms_left = rooms_count
            bosses_left = bosses_count
            for i in range(total_steps):
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
                        if rooms_left > 0 and enabled_room_set:
                            choice = _take_seeded_from(rnd, enabled_room_set)
                            if choice:
                                route.append(choice)
                                rooms_left -= 1
    else:
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
        else:
            bosses_count = min(getattr(cfg, "bosses_to_play", 0), len(enabled_bosses))
            rooms_count = min(getattr(cfg, "rooms_to_play", 0), len(enabled_rooms))
            total_steps = bosses_count + rooms_count
            rooms_left = rooms_count
            bosses_left = bosses_count
            for i in range(total_steps):
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
    if "boss_solgryn.ini" not in route:
        route.append("boss_solgryn.ini")
    if route:
        log("Route built from positions.json: " + " -> ".join(route))
    else:
        log("⚠️ Route could not be built (no valid entries found).")
    return route
