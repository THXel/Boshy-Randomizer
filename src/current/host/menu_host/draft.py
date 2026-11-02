"""Reuse the canonical routes/seed format; expose only migrated gameplay settings."""

import secrets
from copy import deepcopy
from export_route_probe import REPO
from run_settings import (
    defaults,
    normalize,
    encode,
    decode,
    LEVELS as LEVELS,
    BOSSES as BOSSES,
)
from run_extras import defaults as extras_defaults, EXTRAS
import sys

sys.path.insert(0, str(REPO / "src/python/menu"))
from menu_seed import renew_on_edit
from export_native_run import PACKS

from gameplay.characters import selected as selected_character

RUN_MODES = ("randomizer", "boss_rush", "level_rush", "normal", "target")

SUPPORTED = {
    "spider",
    "no_screen_shaking",
    "mirror",
    "death_character",
    "god_mode",
    "one_hp",
    "skip_intro",
    "fast_chests",
    "quiet_pickups",
    "autofire",
    "no_mouse_ghost",
    "music",
    "sprite_scenery",
    "sprite_backgrounds",
    "sprite_decor",
    "sprite_tiles",
    "sprite_actors",
    "sprite_dim",
}


BETA_BOSSES = frozenset(("bomberman", "questionmark", "ridley"))


def initial():
    extras = extras_defaults()
    for key, *_ in EXTRAS:
        extras[key] = False
    extras["quiet_pickups"] = True
    extras["no_mouse_ghost"] = True
    base = defaults()
    base["start_character"] = "Dark Boshy"
    base["boss_pool"] = [key for key in base["boss_pool"] if key not in BETA_BOSSES]
    return normalize(
        dict(
            difficulty=1,
            levels=True,
            items=False,
            characters=False,
            mode="randomizer",
            target_count=5,
            boss_count=0,
            **base,
            extras=extras,
        )
    )


def validate(options):
    d = normalize(options)
    if (
        d["mode"] not in RUN_MODES
        or d["route_version"] != 9
        or (not d["levels"] and d["mode"] != "normal")
    ):
        raise ValueError("Dieser Seed verwendet noch nicht migrierte Spielregeln.")
    selected_character(d)
    ex = d["extras"]
    if any(ex[k] for k, *_ in EXTRAS if k not in SUPPORTED):
        raise ValueError("Dieser Seed verwendet noch nicht migrierte Extras.")
    return d


class Draft:
    def __init__(self):
        self.options = initial()
        self._route_choices = {}
        self.remember_choices()
        self.seed = ""
        self.seed_origin = None
        self.action = None
        self.dirty = True
        self.music_pack = "original"
        self.blood_pack = "original"
        self.consume_seed()

    def consume_seed(self):
        previous = self.seed
        while self.seed == previous:
            self.seed = secrets.token_hex(4).upper()
        self.seed_origin = None
        self.dirty = True

    @renew_on_edit
    def update(self, **changes):
        d = deepcopy(self.options)
        from run_extras import upgrade

        upgrade(d)
        for key, value in changes.items():
            if key in SUPPORTED or key in ("shot_mode", "shot_interval_seconds"):
                d["extras"][key] = value
            elif key in (
                "levels",
                "items",
                "characters",
                "mode",
                "difficulty",
                "start_character",
                "level_pool",
                "boss_pool",
                "level_count",
                "route_boss_count",
                "target_count",
                "boss_count",
            ):
                d[key] = value
            else:
                raise ValueError("Unsupported draft field: " + key)
        self.options = validate(d)
        self.remember_choices()

    def remember_choices(self):
        if self.options["mode"] in ("normal", "target"):
            return
        for pool, count, excluded in (
            ("level_pool", "level_count", "boss_rush"),
            ("boss_pool", "route_boss_count", "level_rush"),
        ):
            if self.options["mode"] != excluded:
                self._route_choices[pool] = (
                    list(self.options[pool]),
                    self.options[count],
                )

    def set_mode(self, mode):
        if mode not in RUN_MODES:
            raise ValueError("Unsupported native run mode")
        changes = {"mode": mode, "levels": mode != "normal"}
        fallback = initial()
        for pool, count, excluded in (
            ("level_pool", "level_count", "boss_rush"),
            ("boss_pool", "route_boss_count", "level_rush"),
        ):
            selected, number = self._route_choices.get(
                pool, (fallback[pool], fallback[count])
            )
            if (
                mode != "randomizer"
                and mode != excluded
                and (not selected or number == 0)
            ):
                selected, number = fallback[pool], fallback[count]
            changes[pool] = [] if mode == excluded else list(selected)
            changes[count] = 0 if mode == excluded else number
        self.update(**changes)

    def select_pack(self, kind, value):
        if kind not in ("blood_pack", "music_pack") or value not in PACKS:
            raise ValueError("Pack")
        if getattr(self, kind) != value:
            setattr(self, kind, value)
            self.consume_seed()

    @renew_on_edit
    def apply_preset(self, name):
        if name not in ("standard", "chaos", "training"):
            raise ValueError("Unsupported preset")
        previous = self.options
        candidate = initial()
        candidate.update(
            {k: previous[k] for k in ("mode", "target_count", "boss_count")}
        )
        candidate.update(
            difficulty=1,
            levels=previous["mode"] != "normal",
            items=previous["mode"] not in ("normal", "target"),
        )
        candidate["extras"]["spider"] = previous["extras"]["spider"]
        if name == "chaos":
            candidate["characters"] = True
            candidate["extras"].update(shot_mode="death_and_spot", death_character=True)
        if name == "training":
            candidate["extras"].update(
                god_mode=True,
                one_hp=True,
                autofire=True,
                skip_intro=True,
                fast_chests=True,
            )
        self.options = validate(candidate)
        self._route_choices = {}
        self.remember_choices()

    def shared(self):
        return encode(self.seed, validate(self.options))

    def import_seed(self, code):
        if (
            not isinstance(code, str)
            or not code.strip().startswith("BR12-")
            or len(code) > 4096
        ):
            raise ValueError("A current shared seed is required")
        seed, options = decode(code.strip())
        options = validate(options)
        self.seed = seed
        self.options = options
        self._route_choices = {}
        self.remember_choices()
        self.seed_origin = object()
        self.dirty = True
