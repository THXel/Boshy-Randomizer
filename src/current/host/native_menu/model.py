"""Menu navigation and editable run settings, independent of drawing/transport."""

import json
from dataclasses import dataclass
from menu_host.draft import Draft, LEVELS, BOSSES, RUN_MODES
from menu_host.labels import text, stage, LANGUAGES
from native_menu import layout, history
from native_menu.preferences import load_language, save_preferences, load_preferences
from native_menu import display
from gameplay.shot_plan import MODES as SHOT_MODES

DIFFICULTIES = ("Ez Mode", "Totally Average", "Hardon Mode", "You're Gonna Rage")
RULES = (
    "god_mode",
    "autofire",
    "no_mouse_ghost",
    "one_hp",
    "skip_intro",
    "fast_chests",
    "quiet_pickups",
    "mirror",
    "no_screen_shaking",
    "spider",
)
GRAPHICS = (
    "music",
    "sprite_scenery",
    "sprite_backgrounds",
    "sprite_decor",
    "sprite_tiles",
    "sprite_actors",
    "sprite_dim",
)
from gameplay.characters import CHOICES as CHARACTER_CHOICES

ADJUSTABLE = {
    "mode",
    "difficulty",
    "level_count",
    "route_boss_count",
    "target_count",
    "boss_count",
    "sprite_dim",
    "shot_interval_seconds",
    "aspect",
    "resolution",
    "font_size",
}

DIM_LEVELS = (0, 20, 40, 60)

from native_menu.labels import CAPTIONS


@dataclass
class Row:
    key: str
    label: str
    value: str = ""
    enabled: bool = True


class Model:
    def __init__(self, store):
        self.store = store
        self.draft = Draft()
        remembered_spider = load_preferences(store.root).get("spider", True)
        if type(remembered_spider) is bool:
            self.draft.update(spider=remembered_spider)
        self.slot = 1
        self.page = "home"
        self.focus = 0
        self.offset = 0
        self.mouse = None
        self.action = None
        self.message = ""
        self.page_focus = {}
        self.busy = False
        self.busy_label = "busy"
        self.font_size = load_preferences(store.root).get("font_size", "normal")
        if self.font_size not in ("normal", "large"):
            self.font_size = "normal"
        self.language = load_language(store.root)
        self.display = display.load(store.root)
        from native_menu.presets import Presets

        self.presets = Presets(store.root)
        self.preset_id = None
        self.load_slot()

    def t(self, key):
        if key == "sprite_dim":
            key = "dim"
        return (
            CAPTIONS[key][LANGUAGES.index(self.language)]
            if key in CAPTIONS
            else text(key, self.language)
        )

    def saved(self):
        return bool(self.store.current(self.slot))

    def fresh_draft(self):
        self.draft = Draft()
        spider = load_preferences(self.store.root).get("spider", True)
        if type(spider) is bool:
            self.draft.update(spider=spider)

    def load_slot(self):
        if self.saved():
            p = json.loads((self.store.folder(self.slot) / "plan.json").read_text())
            self.draft.import_seed(p["shared_seed"])
            self.draft.music_pack = p["music_pack"]
            self.draft.blood_pack = p["blood_pack"]
        elif getattr(self, "loaded_saved_slot", False):
            self.fresh_draft()
        self.loaded_saved_slot = self.saved()

    def go(self, page):
        self.page_focus[self.page] = self.focus
        self.page = page
        self.focus = min(self.page_focus.get(page, 0), max(0, len(self.rows()) - 1))
        self.offset = self.focus // layout.PAGE_SIZE * layout.PAGE_SIZE
        self.mouse = None
        self.message = ""

    def back(self):
        self.go(
            layout.PARENTS.get(
                self.page, "home" if self.page == "settings" else "settings"
            )
        )

    def rows(self):
        locked = self.saved()
        d = self.draft.options
        ex = d["extras"]
        if self.page == "home":
            out = []
            for slot in (1, 2, 3):
                summary = self.store.summary(slot)
                value = (
                    self.t("empty")
                    if not summary["exists"]
                    else summary["seed"]
                    + " · "
                    + str(summary["deaths"])
                    + " "
                    + self.t("deaths")
                )
                out.append(
                    Row(
                        "slot:" + str(slot),
                        self.t("slot") + " " + str(slot),
                        ("● " if slot == self.slot else "") + value,
                    )
                )
            return out + [
                Row("new", self.t("new"), enabled=not locked),
                Row("resume", self.t("resume"), enabled=locked),
                Row("delete", self.t("delete"), enabled=locked),
                Row("settings", self.t("settings")),
                Row("exit", self.t("exit")),
            ]
        if self.page == "settings":
            return [Row("seed", self.t("seed"), self.draft.seed)] + [
                Row(k, self.t(k))
                for k in (
                    "route",
                    "loadout",
                    "gameplay",
                    "cosmetics",
                    "preview",
                    "tools",
                )
            ]
        if self.page == "tools":
            return [Row(k, self.t(k)) for k in ("presets", "updates", "diagnostics")] + [
                Row("font_size", self.t("font_size"), self.t("font_" + self.font_size))
            ]
        if self.page == "loadout":
            return [
                Row(
                    "start_character",
                    self.t("start_character"),
                    (
                        self.t("auto_character")
                        if d["start_character"] == "Auto"
                        else d["start_character"]
                    ),
                    not locked and d["mode"] != "target",
                ),
                Row(
                    "characters",
                    self.t("characters"),
                    "✓" if d["characters"] else "—",
                    not locked,
                ),
                Row(
                    "items",
                    self.t("items"),
                    "✓" if d["items"] else "—",
                    not locked and d["mode"] not in ("normal", "target"),
                ),
                Row(
                    "death_character",
                    self.t("death_character"),
                    "✓" if ex["death_character"] else "—",
                    not locked,
                ),
            ]
        if self.page == "updates":
            return [
                Row("update:" + str(i), caption, date)
                for i, (date, caption) in enumerate(history.entries(self.language))
            ] + [Row("back", self.t("back"))]
        if self.page == "display":
            w, h = self.display.size
            return [
                Row(
                    "aspect",
                    self.t("aspect"),
                    self.t(
                        "aspect_original"
                        if self.display.aspect == "4:3"
                        else "aspect_stretched"
                    ),
                ),
                Row("resolution", self.t("resolution"), f"{w} × {h}"),
                Row(
                    "fullscreen",
                    self.t("fullscreen"),
                    "✓" if self.display.fullscreen else "—",
                ),
                Row("back", self.t("back")),
            ]
        if self.page == "character_picker":
            return [
                Row(
                    "character:" + name,
                    self.t("auto_character") if name == "Auto" else name,
                    "✓" if name == d["start_character"] else "",
                    not locked and d["mode"] != "target",
                )
                for name in CHARACTER_CHOICES
            ]
        if self.page == "presets":
            try:
                personal = self.presets.read()
            except (OSError, ValueError, KeyError, TypeError):
                personal = []
                self.message = self.t("presets_unreadable")
            return [
                Row("save_preset", self.t("save_preset")),
                *[
                    Row("preset:" + k, self.t("preset_" + k), enabled=not locked)
                    for k in ("standard", "chaos", "training")
                ],
                *[Row("user_preset:" + p["id"], p["name"]) for p in personal],
            ]
        if self.page in ("preset_details", "preset_delete"):
            return (
                [
                    Row("confirm_delete_preset", self.t("confirm_delete_preset")),
                    Row("back", self.t("cancel")),
                ]
                if self.page == "preset_delete"
                else [
                    Row("use_preset", self.t("use_preset"), enabled=not locked),
                    Row("delete_preset", self.t("delete_preset")),
                    Row("back", self.t("back")),
                ]
            )
        if self.page == "preview":
            from run_settings import route

            if d["mode"] == "target":
                return [
                    Row("targets", self.t("targets")),
                    Row("preview:dynamic", self.t("target_hint")),
                ]
            if d["mode"] == "normal":
                return [Row("preview:original", self.t("normal_hint"))]
            names = {
                **LEVELS,
                **{value[2]: value[0] for value in BOSSES.values()},
                "boss_solgryn.ini": "Solgryn",
            }
            return [
                Row(
                    "preview:" + spot,
                    str(index + 1)
                    + " · "
                    + stage(names.get(spot, spot), self.language),
                )
                for index, spot in enumerate(route(self.draft.seed, d))
            ]
        if self.page == "targets":
            from gameplay.target_plan import goals

            selected = goals(self.draft.seed, d)
            summary = self.store.summary(self.slot)
            progress = summary.get("target_progress") or dict(items=[], bosses=[])
            return [
                Row(
                    "goal:" + kind + ":" + name,
                    stage(BOSSES[name][0], self.language) if kind == "bosses" else name,
                    "✓" if name in progress[kind] else "○",
                    True,
                )
                for kind in ("items", "bosses")
                for name in selected[kind]
            ] or [Row("none", self.t("target_only"), enabled=False)]
        if self.page == "route":
            if d["mode"] == "target":
                return [
                    Row("mode", self.t("mode"), self.t("target"), not locked),
                    Row(
                        "target_count",
                        self.t("target_count"),
                        str(d["target_count"]),
                        not locked,
                    ),
                    Row(
                        "boss_count",
                        self.t("boss_count"),
                        str(d["boss_count"]),
                        not locked,
                    ),
                    Row(
                        "difficulty",
                        self.t("difficulty"),
                        DIFFICULTIES[d["difficulty"]],
                        not locked,
                    ),
                    Row("targets", self.t("targets") + " …"),
                ]
            return [
                Row("mode", self.t("mode"), self.t(d["mode"]), not locked),
                Row(
                    "level_count",
                    self.t("level_count"),
                    str(d["level_count"]) if d["mode"] != "normal" else "—",
                    not locked and d["mode"] not in ("boss_rush", "normal"),
                ),
                Row(
                    "route_boss_count",
                    self.t("route_boss_count"),
                    str(d["route_boss_count"]) if d["mode"] != "normal" else "—",
                    not locked and d["mode"] not in ("level_rush", "normal"),
                ),
                Row(
                    "difficulty",
                    self.t("difficulty"),
                    DIFFICULTIES[d["difficulty"]],
                    not locked,
                ),
                Row("levels", self.t("levels") + " …"),
                Row("bosses", self.t("bosses") + " …"),
            ]
        if self.page in ("levels", "bosses"):
            pool = "level_pool" if self.page == "levels" else "boss_pool"
            items = (
                LEVELS
                if self.page == "levels"
                else {k: v[0] for k, v in BOSSES.items()}
            )
            return [
                Row(
                    pool + ":" + k,
                    stage(v, self.language),
                    "✓" if k in d[pool] else "—",
                    not locked
                    and d["mode"] not in ("normal", "target")
                    and d["mode"]
                    != ("boss_rush" if self.page == "levels" else "level_rush"),
                )
                for k, v in items.items()
            ]
        if self.page == "gameplay":
            return [
                Row(k, self.t(k), "✓" if ex.get(k, False) else "—", not locked)
                for k in RULES
            ]
        if self.page == "shots":
            return [
                Row(
                    "shot:" + mode,
                    self.t("shot_" + mode),
                    "✓" if ex["shot_mode"] == mode else "—",
                    not locked,
                )
                for mode in SHOT_MODES
            ] + [
                Row(
                    "shot_interval_seconds",
                    self.t("shot_interval_seconds"),
                    str(ex["shot_interval_seconds"]),
                    not locked,
                ),
                Row("back", self.t("back")),
            ]
        if self.page == "cosmetics":
            return [
                Row(
                    k,
                    self.t(k),
                    (
                        (
                            str(ex[k]) + " %"
                            if k == "sprite_dim"
                            else "✓" if ex[k] else "—"
                        )
                    ),
                    not locked,
                )
                for k in GRAPHICS
            ] + [Row("shots", self.t("shots"), self.t("shot_" + ex["shot_mode"]))]
        if self.page == "seed":
            return [
                Row("copy", self.t("copy_seed")),
                Row("import", self.t("import_seed"), enabled=not locked),
                Row("renew", self.t("renew_seed"), enabled=not locked),
            ]
        raise ValueError(self.page)

    def visible(self):
        rows = self.rows()
        self.focus = min(self.focus, len(rows) - 1)
        self.offset = self.focus // layout.PAGE_SIZE * layout.PAGE_SIZE
        return rows[self.offset : self.offset + layout.PAGE_SIZE]

    def select(self, key, direction=1):
        row = next((r for r in self.rows() if r.key == key), None)
        if row is None or not row.enabled or self.busy:
            return
        self.message = ""
        if key == "run_summary" or key.startswith(("goal:", "preview:", "update:")):
            return  # Readable, focusable progress entries are not editable.
        if key == "save_preset":
            self.action = "save_preset"
        elif key.startswith("user_preset:"):
            self.preset_id = key.split(":", 1)[1]
            self.go("preset_details")
        elif key == "use_preset":
            self.presets.apply(self.preset_id, self.draft)
            self.go("settings")
            self.message = self.t("preset_applied")
        elif key == "delete_preset":
            self.go("preset_delete")
        elif key == "confirm_delete_preset":
            self.presets.delete(self.preset_id)
            self.preset_id = None
            self.go("presets")
        elif key.startswith("character:"):
            self.draft.update(start_character=key.split(":", 1)[1])
            self.go("loadout")
        elif key.startswith("shot:"):
            self.draft.update(shot_mode=key.split(":", 1)[1])
        elif key == "shot_interval_seconds":
            value = self.draft.options["extras"][key]
            self.draft.update(**{key: min(86400, max(1, value + direction))})
        elif key.startswith("preset:"):
            self.draft.apply_preset(key.split(":", 1)[1])
            self.go("settings")
        elif key.startswith("slot:"):
            self.slot = int(key.split(":")[1])
            self.load_slot()
        elif key in (
            "settings",
            "loadout",
            "tools",
            "route",
            "levels",
            "bosses",
            "gameplay",
            "cosmetics",
            "shots",
            "seed",
            "targets",
            "preview",
            "presets",
            "display",
            "updates",
        ):
            self.go(key)
        elif key == "back":
            self.back()
        elif key in ("items", "characters"):
            self.draft.update(**{key: not self.draft.options[key]})
        elif key == "mode":
            current = RUN_MODES.index(self.draft.options["mode"])
            self.draft.set_mode(RUN_MODES[(current + direction) % len(RUN_MODES)])
        elif key == "start_character":
            self.go("character_picker")
            self.focus = CHARACTER_CHOICES.index(self.draft.options["start_character"])
        elif key in ("aspect", "resolution", "fullscreen"):
            self.display = self.display.changed(
                "height" if key == "resolution" else key, direction
            )
            display.save(self.store.root, self.display)
            self.action = "display"
        elif key == "font_size":
            self.font_size = "large" if self.font_size == "normal" else "normal"
            save_preferences(self.store.root, font_size=self.font_size)
        elif key == "diagnostics":
            self.action = "diagnostics"
        elif key in ("new", "resume", "delete", "exit", "copy", "import"):
            self.action = key
        elif key == "renew":
            self.draft.consume_seed()
        elif ":" in key:
            pool, item = key.split(":")
            selected = list(self.draft.options[pool])
            selected.remove(item) if item in selected else selected.append(item)
            count = "level_count" if pool == "level_pool" else "route_boss_count"
            number = min(self.draft.options[count], len(selected))
            other = "route_boss_count" if count == "level_count" else "level_count"
            if number + self.draft.options[other] == 0:
                self.message = self.t("route_required")
                return
            self.draft.update(**{pool: selected, count: number})
        elif key in ("target_count", "boss_count"):
            minimum, limit = (1, 19) if key == "target_count" else (0, len(BOSSES))
            self.draft.update(
                **{
                    key: minimum
                    + (self.draft.options[key] - minimum + direction)
                    % (limit - minimum + 1)
                }
            )
        elif key in ("level_count", "route_boss_count", "difficulty"):
            limit = (
                3
                if key == "difficulty"
                else len(
                    self.draft.options[
                        "level_pool" if key == "level_count" else "boss_pool"
                    ]
                )
            )
            minimum = 0
            if key != "difficulty":
                other = "route_boss_count" if key == "level_count" else "level_count"
                minimum = 1 if self.draft.options[other] == 0 else 0
            value = minimum + (self.draft.options[key] - minimum + direction) % (
                limit - minimum + 1
            )
            self.draft.update(**{key: value})
        elif key == "sprite_dim":
            self.draft.update(
                sprite_dim=DIM_LEVELS[
                    (DIM_LEVELS.index(self.draft.options["extras"][key]) + direction)
                    % len(DIM_LEVELS)
                ]
            )
        else:
            self.draft.update(**{key: not self.draft.options["extras"].get(key, False)})
            if key == "spider":
                save_preferences(
                    self.store.root, spider=self.draft.options["extras"]["spider"]
                )

    def key(self, key, x=0, y=0):
        if self.busy:
            return
        rows = self.rows()
        if key == 1001:
            self.mouse = (x, y)
            visible = self.visible()
            hit = layout.hit(self.page, len(visible), x, y)
            if hit is not None:
                self.focus = self.offset + hit
            return
        if (
            self.page == "shots"
            and key in (33, 34)
            and rows[self.focus].key == "shot_interval_seconds"
        ):
            self.select("shot_interval_seconds", -60 if key == 33 else 60)
            return
        if key in (37, 38, 39, 40, 9):
            self.focus = layout.move(self.page, self.focus, len(rows), key)
        elif key in (33, 34):
            page_count = (len(rows) + layout.PAGE_SIZE - 1) // layout.PAGE_SIZE
            current = self.focus // layout.PAGE_SIZE
            self.focus = (
                (current + (-1 if key == 33 else 1)) % page_count
            ) * layout.PAGE_SIZE
        elif key in (13, 32):
            self.select(rows[self.focus].key)
        elif key in (107, 109, 187, 189):
            selected = rows[self.focus].key
            if selected in ADJUSTABLE:
                self.select(selected, -1 if key in (109, 189) else 1)
        elif key in (27, 8):
            self.back()
        elif key == 46 and self.page == "home" and self.saved():
            self.action = "delete"
        elif key == 116 and not self.saved():
            self.draft.consume_seed()
        elif key == 117:
            self.action = "copy"
        elif key == 118 and not self.saved():
            self.action = "import"
        elif key == 1000:
            i = layout.hit(self.page, len(self.visible()), x, y)
            if i is not None:
                self.focus = self.offset + i
                selected = rows[self.focus].key
                direction = (
                    -1
                    if selected in ADJUSTABLE
                    and layout.contains(layout.adjust_rect(self.page, i, -1), x, y)
                    else 1
                )
                self.select(selected, direction)
            elif self.page != "home" and layout.contains(layout.BACK, x, y):
                self.key(27)
            elif self.page != "home" and layout.contains(layout.PREVIOUS, x, y):
                self.key(33)
            elif self.page != "home" and layout.contains(layout.NEXT, x, y):
                self.key(34)
        self.visible()
