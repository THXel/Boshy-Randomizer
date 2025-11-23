import os
import random
import json

from .logger import log
from .config import positions_json, ini_folder

_ROOM_POOL: list[str] | None = None
_BOSS_POOL: list[str] | None = None
_ROOM_UNUSED: list[str] = []
_BOSS_UNUSED: list[str] = []

_HISTORY_FILE = os.path.join(ini_folder, "route_history.json")
_HISTORY_LIMIT_ROOMS = 8
_HISTORY_LIMIT_BOSSES = 8


def _norm(name: str) -> str:
    return str(name).lower().strip()


def _empty_hist_block():
    return {"rooms": [], "bosses": []}


def _load_route_history_all() -> dict:
    if not os.path.exists(_history_file := _HISTORY_FILE):
        return {"normal": _empty_hist_block(), "target": _empty_hist_block()}
    try:
        with open(_history_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        log(f"⚠️ Failed to load route history: {e}")
        return {"normal": _empty_hist_block(), "target": _empty_hist_block()}

    if "rooms" in data or "bosses" in data:
        rooms = [_norm(r) for r in data.get("rooms", [])]
        bosses = [_norm(b) for b in data.get("bosses", [])]
        return {
            "normal": {"rooms": rooms, "bosses": bosses},
            "target": _empty_hist_block(),
        }

    result = {"normal": _empty_hist_block(), "target": _empty_hist_block()}
    for mode in ("normal", "target"):
        block = data.get(mode, {}) or {}
        rooms = [_norm(r) for r in block.get("rooms", [])]
        bosses = [_norm(b) for b in block.get("bosses", [])]
        result[mode] = {"rooms": rooms, "bosses": bosses}
    return result


def _save_route_history_all(data: dict) -> None:
    try:
        os.makedirs(ini_folder, exist_ok=True)
        with open(_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        log(f"⚠️ Failed to save route history: {e}")


def apply_history_filter(
    enabled_rooms: list[str],
    enabled_bosses: list[str],
    rooms_requested: int,
    bosses_requested: int,
    mode: str = "normal",
) -> tuple[list[str], list[str]]:
    hist_all = _load_route_history_all()
    block = hist_all.get(mode, _empty_hist_block())
    recent_rooms = set(block.get("rooms", []))
    recent_bosses = set(block.get("bosses", []))

    enabled_rooms_lc = [_norm(r) for r in enabled_rooms]
    enabled_bosses_lc = [_norm(b) for b in enabled_bosses]

    room_map = {lc: orig for lc, orig in zip(enabled_rooms_lc, enabled_rooms)}
    boss_map = {lc: orig for lc, orig in zip(enabled_bosses_lc, enabled_bosses)}

    filtered_rooms_lc = [r for r in enabled_rooms_lc if r not in recent_rooms]
    filtered_bosses_lc = [b for b in enabled_bosses_lc if b not in recent_bosses]

    rooms_final = enabled_rooms
    bosses_final = enabled_bosses

    if filtered_rooms_lc and len(filtered_rooms_lc) >= int(rooms_requested or 0):
        rooms_final = [room_map[r] for r in filtered_rooms_lc]
        log(
            f"♻️ [{mode}] Avoiding last {_HISTORY_LIMIT_ROOMS} rooms "
            f"(filtered to {len(rooms_final)} rooms)."
        )

    if filtered_bosses_lc and len(filtered_bosses_lc) >= int(bosses_requested or 0):
        bosses_final = [boss_map[b] for b in filtered_bosses_lc]
        log(
            f"♻️ [{mode}] Avoiding last {_HISTORY_LIMIT_BOSSES} bosses "
            f"(filtered to {len(bosses_final)} bosses)."
        )

    return rooms_final, bosses_final


def update_route_history(
    route: list[str],
    all_rooms: list[str],
    all_bosses: list[str],
    mode: str = "normal",
) -> None:
    try:
        hist_all = _load_route_history_all()
        block = hist_all.get(mode, _empty_hist_block())

        rooms_old = list(block.get("rooms", []))
        bosses_old = list(block.get("bosses", []))

        all_rooms_set = {_norm(r) for r in all_rooms}
        all_bosses_set = {_norm(b) for b in all_bosses}

        new_rooms = [_norm(r) for r in route if _norm(r) in all_rooms_set]
        new_bosses = [_norm(b) for b in route if _norm(b) in all_bosses_set]

        rooms_merged = (rooms_old + new_rooms)[-_HISTORY_LIMIT_ROOMS:]
        bosses_merged = (bosses_old + new_bosses)[-_HISTORY_LIMIT_BOSSES:]

        hist_all[mode] = {"rooms": rooms_merged, "bosses": bosses_merged}
        _save_route_history_all(hist_all)
        log(
            f"🧷 Updated [{mode}] route history "
            f"(rooms={len(rooms_merged)}, bosses={len(bosses_merged)})."
        )
    except Exception as e:
        log(f"⚠️ Failed to update route history: {e}")


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
        _ROOM_POOL = sorted(_norm(r) for r in data["rooms"].keys())
        _ROOM_UNUSED = list(_ROOM_POOL)
        random.shuffle(_ROOM_UNUSED)
        log(f"📦 Room pool initialized with {len(_ROOM_POOL)} entries.")

    if _BOSS_POOL is None:
        _BOSS_POOL = sorted(
            _norm(b)
            for b in data["bosses"].keys()
            if _norm(b) != "boss_solgryn.ini"
        )
        _BOSS_UNUSED = list(_BOSS_POOL)
        random.shuffle(_BOSS_UNUSED)
        log(f"📦 Boss pool initialized with {len(_BOSS_POOL)} entries.")

    return data


def _take_from_cycle(
    all_names: list[str],
    unused_list: list[str],
    enabled_set: set[str],
    label: str,
) -> str | None:
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


def _take_seeded_from(rnd: random.Random, enabled_set: set[str]) -> str | None:
    if not enabled_set:
        return None
    choices = sorted(enabled_set)
    choice = rnd.choice(choices)
    enabled_set.remove(choice)
    return choice


def build_random_route(cfg, pos_data=None, mode: str = "normal"):
    data = _load_positions(pos_data)
    rooms_dict = data.get("rooms", {}) or {}
    bosses_dict = data.get("bosses", {}) or {}

    all_rooms = [str(r).lower() for r in rooms_dict.keys()]
    all_bosses = [str(b).lower() for b in bosses_dict.keys()]

    if not all_rooms and not all_bosses:
        log("⚠️ positions.json appears empty or invalid.")
        return []

    disabled_rooms_l = [_norm(x) for x in getattr(cfg, "disabled_rooms", [])]
    disabled_bosses_l = [_norm(x) for x in getattr(cfg, "disabled_bosses", [])]

    enabled_rooms = [r for r in all_rooms if r not in disabled_rooms_l]
    enabled_bosses = [
        b for b in all_bosses if b not in disabled_bosses_l and b != "boss_solgryn.ini"
    ]

    if not enabled_rooms and not getattr(cfg, "only_bosses", False):
        log("⚠️ No enabled rooms available in positions.json.")
    if not enabled_bosses and not getattr(cfg, "only_rooms", False):
        log("⚠️ No enabled bosses available in positions.json.")

    rooms_to_play = int(getattr(cfg, "rooms_to_play", 0) or 0)
    bosses_to_play = int(getattr(cfg, "bosses_to_play", 0) or 0)

    enabled_rooms, enabled_bosses = apply_history_filter(
        enabled_rooms,
        enabled_bosses,
        rooms_requested=rooms_to_play,
        bosses_requested=bosses_to_play,
        mode=mode,
    )

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
    else:
        rnd = random

    if use_seed:
        if getattr(cfg, "only_bosses", False):
            count = min(bosses_to_play, len(enabled_bosses))
            pool = list(enabled_bosses)
            rnd.shuffle(pool)
            route.extend(pool[:count])
        elif getattr(cfg, "only_rooms", False):
            count = min(rooms_to_play, len(enabled_rooms))
            pool = list(enabled_rooms)
            rnd.shuffle(pool)
            route.extend(pool[:count])
        else:
            bosses_count = min(bosses_to_play, len(enabled_bosses))
            rooms_count = min(rooms_to_play, len(enabled_rooms))

            total_steps = bosses_count + rooms_count
            rooms_left = rooms_count
            bosses_left = bosses_count

            for i in range(total_steps):
                if i % 2 == 0 and rooms_left > 0 and enabled_room_set:
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
            count = min(bosses_to_play, len(enabled_bosses))
            for _ in range(count):
                choice = _take_from_cycle(
                    _BOSS_POOL or enabled_bosses,
                    _BOSS_UNUSED,
                    enabled_boss_set,
                    "Boss",
                )
                if not choice:
                    break
                route.append(choice)
                enabled_boss_set.discard(choice)
        elif getattr(cfg, "only_rooms", False):
            count = min(rooms_to_play, len(enabled_rooms))
            for _ in range(count):
                choice = _take_from_cycle(
                    _ROOM_POOL or enabled_rooms,
                    _ROOM_UNUSED,
                    enabled_room_set,
                    "Room",
                )
                if not choice:
                    break
                route.append(choice)
                enabled_room_set.discard(choice)
        else:
            bosses_count = min(bosses_to_play, len(enabled_bosses))
            rooms_count = min(rooms_to_play, len(enabled_rooms))

            total_steps = bosses_count + rooms_count
            rooms_left = rooms_count
            bosses_left = bosses_count

            for i in range(total_steps):
                if i % 2 == 0 and rooms_left > 0 and enabled_room_set:
                    choice = _take_from_cycle(
                        _ROOM_POOL or enabled_rooms,
                        _ROOM_UNUSED,
                        enabled_room_set,
                        "Room",
                    )
                    if choice:
                        route.append(choice)
                        rooms_left -= 1
                        enabled_room_set.discard(choice)
                    else:
                        if bosses_left > 0 and enabled_boss_set:
                            choice_b = _take_from_cycle(
                                _BOSS_POOL or enabled_bosses,
                                _BOSS_UNUSED,
                                enabled_boss_set,
                                "Boss",
                            )
                            if choice_b:
                                route.append(choice_b)
                                bosses_left -= 1
                                enabled_boss_set.discard(choice_b)
                else:
                    if bosses_left > 0 and enabled_boss_set:
                        choice = _take_from_cycle(
                            _BOSS_POOL or enabled_bosses,
                            _BOSS_UNUSED,
                            enabled_boss_set,
                            "Boss",
                        )
                        if choice:
                            route.append(choice)
                            bosses_left -= 1
                            enabled_boss_set.discard(choice)
                        else:
                            if rooms_left > 0 and enabled_room_set:
                                choice_r = _take_from_cycle(
                                    _ROOM_POOL or enabled_rooms,
                                    _ROOM_UNUSED,
                                    enabled_room_set,
                                    "Room",
                                )
                                if choice_r:
                                    route.append(choice_r)
                                    rooms_left -= 1
                                    enabled_room_set.discard(choice_r)

    if "boss_solgryn.ini" not in route:
        route.append("boss_solgryn.ini")

    if route:
        log("Route built from positions.json: " + " -> ".join(route))
        update_route_history(route, all_rooms, all_bosses, mode=mode)
    else:
        log("⚠️ Route could not be built (no valid entries found).")

    return route
