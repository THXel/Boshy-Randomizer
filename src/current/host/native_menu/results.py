"""Transparent completion summary over the original ending and credits."""

import configparser
import copy
import io
import json
import math
import struct
import time
from pathlib import Path
from PIL import Image, ImageDraw
from gameplay.native_events import Events
from gameplay.spider_events import window, calc
from menu_host.store import atomic, save
from native_menu.events import condition, file_path, value, load_image, alt
from native_menu.transport import write, read
from transition.events import (
    action,
    commands,
    expression,
    integer,
    parameter,
    ini_value,
    set_ini,
)
from transition.router import GROUP, STAGES, ini_expression
from export_route_probe import REPO

PANEL, VIEW, INPUT = 4300, 4301, 4302
ROOM = "Prize Room"
ENDING_FRAMES = (47, 48, 49)
ENDING_NAMES = ("Frame 49", "Credits", ROOM)
CLOSE_BOUNDS = (596, 194, 620, 218)
CAPTIONS = {
    "title": (
        "Run abgeschlossen",
        "Run complete",
        "Partida completada",
        "Забег завершён",
        "クリア",
    ),
    "time": ("Zeit", "Time", "Tiempo", "Время", "タイム"),
    "deaths": ("Tode", "Deaths", "Muertes", "Смерти", "死亡回数"),
    "goals": ("Ziele", "Goals", "Objetivos", "Цели", "目標"),
    "bosses": ("Bosse", "Bosses", "Jefes", "Боссы", "ボス"),
    "items": ("Items", "Items", "Objetos", "Предметы", "アイテム"),
    "copy": (
        "F6 · Seed kopieren",
        "F6 · Copy seed",
        "F6 · Copiar semilla",
        "F6 · Копировать сид",
        "F6・シードをコピー",
    ),
    "close": (
        "F2 · Zurück zum Titel",
        "F2 · Return to title",
        "F2 · Volver al título",
        "F2 · На главный экран",
        "F2・タイトルへ",
    ),
    "copied": (
        "Seed kopiert",
        "Seed copied",
        "Semilla copiada",
        "Сид скопирован",
        "シードをコピーしました",
    ),
    "copy_failed": (
        "Kopieren fehlgeschlagen – F6 erneut versuchen",
        "Copy failed — try F6 again",
        "Error al copiar: vuelve a pulsar F6",
        "Не удалось скопировать — повторите F6",
        "コピー失敗・F6で再試行",
    ),
}
LANGUAGES = ("de", "en", "es", "ru", "ja")


def eligible(frame, config):
    return frame in ENDING_NAMES and config.getint(GROUP, "Completed", fallback=0) == 1


def snapshot(plan, config, elapsed, slot, identity):
    from gameplay.reward_plan import LOCATIONS

    elapsed = float(elapsed)
    if not math.isfinite(elapsed):
        raise ValueError("Invalid completion time")
    item_names = {r["source"] for r in LOCATIONS if r["source_kind"] == "item"} | {
        "Gastly"
    }
    from gameplay.target_plan import progress
    from beta_catalogue import BOSSES

    selected = plan.get("targets", {"items": [], "bosses": []})
    earned = progress(selected, config)
    goals = [
        dict(name=name, done=name in earned["items"]) for name in selected["items"]
    ]
    goals += [
        dict(name=BOSSES[key][0], done=key in earned["bosses"])
        for key in selected["bosses"]
    ]
    bosses = sum(
        config.getint("Achievements", key, fallback=0) >= 2
        or plan["options"]["mode"] != "normal"
        and config.getint(GROUP, "Done" + str(STAGES[entry[2]]["id"]), fallback=0) == 1
        for key, entry in BOSSES.items()
    )
    return dict(
        schema=2,
        test_run=config.getint("RandomizerDebug", "Enabled", fallback=0) == 1,
        goals=goals,
        bosses=bosses + int(config.getint(GROUP, "Completed", fallback=0) == 1),
        run_id=identity,
        slot=slot,
        seed=plan["seed"],
        shared_seed=plan["shared_seed"],
        mode=plan["options"]["mode"],
        elapsed=max(0, elapsed),
        deaths=config.getint("Stats", "Deaths", fallback=0),
        items=sum(
            config.getint("Collectables", k, fallback=0) == 1 for k in item_names
        ),
    )


def render(folder, data, model, message=""):
    from native_menu.render import Renderer

    # Reuse the existing typefaces, without constructing an animated menu.
    fonts = Renderer.fonts(type("Fonts", (), {"font_cache": {}})(), model.language)
    t = lambda k: CAPTIONS[k][LANGUAGES.index(model.language)]
    im = Image.new("RGBA", (640, 480))
    draw = ImageDraw.Draw(im)
    # Match the old result layout: upper scene and left side stay clear.
    draw.rounded_rectangle(
        (178, 186, 628, 466),
        radius=8,
        fill=(12, 20, 29, 112),
        outline=(140, 221, 198, 180),
    )
    draw.rectangle(CLOSE_BOUNDS, fill=(12, 20, 29, 150), outline="#9aecd5")
    draw.line((602, 200, 614, 212), fill="white", width=2)
    draw.line((614, 200, 602, 212), fill="white", width=2)
    logo = Image.open(REPO / "assets/Custom/boshy_randomizer.png").convert("RGBA")
    logo.thumbnail((112, 48))
    im.alpha_composite(logo, (506 + (112 - logo.width) // 2, 224))

    def text(x, y, message, size=14, color="#edf5f6"):
        draw.text((x, y), message, font=fonts[size], fill=color)

    from native_menu.debug_actions import TEST_LABELS
    title = TEST_LABELS[LANGUAGES.index(model.language)] if data.get("test_run") else t("title")
    text(190, 198, title, 16, "#9aecd5")
    text(190, 228, model.t(data["mode"]), 12)
    seconds = int(data["elapsed"])
    hours, rest = divmod(seconds, 3600)
    minutes, seconds = divmod(rest, 60)
    clock = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    for x, label, result in (
        (190, t("time"), clock),
        (338, t("deaths"), str(data["deaths"])),
        (486, t("items"), str(data["items"])),
    ):
        text(x, 275, label, 12, "#b8cbd4")
        text(x, 301, result, 18)
    goals = data.get("goals", [])
    if data["mode"] == "target":
        text(
            190,
            329,
            t("goals") + f" · {sum(g['done'] for g in goals)}/{len(goals)}",
            12,
            "#9aecd5",
        )
        names = ", ".join(g["name"] for g in goals)
        while names and draw.textlength(names, font=fonts[10]) > 410:
            names = names[:-2].rstrip("…") + "…"
        text(190, 349, names, 10)
    else:
        text(190, 337, t("bosses") + " · " + str(data.get("bosses", 0)), 12, "#9aecd5")
    text(190, 371, model.t("seed") + " · " + data["seed"], 12)
    text(190, 395, t("copy"), 12)
    text(190, 419, t("close"), 12)
    if message:
        text(190, 442, t(message), 10, "#9aecd5")
    buffer = io.BytesIO()
    im.save(buffer, format="PNG")
    atomic(Path(folder) / "run-result.png", buffer.getvalue())


class Completion:
    def __init__(self, c):
        self.c = c
        self.identity = None
        self.data = None
        self.copy_sequence = 0
        self.dismissed = False
        self.visible = False
        self.generation = 0
        self.last = 0
        self.last_error = None
        write(c.folder / "results-input.ini", dict(Copy=0, Dismiss=0, EndingReady=0))
        write(c.folder / "results-view.ini", dict(Ready=0, Generation=0))

    def publish(self, message=""):
        if self.dismissed:
            return
        self.visible = True
        render(self.c.folder, self.data, self.c.model, message)
        self.generation += 1
        write(
            self.c.folder / "results-view.ini",
            dict(Ready=1, Generation=self.generation),
        )

    def tick(self):
        c = self.c
        if c.closed or c.phase != "playing" or c.active_slot is None:
            return
        if time.monotonic() - self.last < 0.15:
            return
        self.last = time.monotonic()
        try:
            frame = c.window.reader.frame()
            if frame not in ENDING_NAMES:
                return
            cfg = save(c.folder / "SaveFile1.ini")
            if not eligible(frame, cfg):
                return
            meta = c.store.current(c.active_slot)
            identity = meta["run"][13:]
            if self.identity != identity:
                plan = json.loads(
                    (c.store.folder(c.active_slot) / "plan.json").read_text()
                )
                self.data = snapshot(
                    plan,
                    cfg,
                    c.tracker.finish_run(c, identity),
                    c.active_slot,
                    identity,
                )
                self.identity = identity
                self.copy_sequence = read(c.folder / "results-input.ini").get("copy", 0)
                atomic(
                    c.store.folder(c.active_slot) / "result.json",
                    json.dumps(self.data, ensure_ascii=False, indent=2).encode(),
                )
            state = read(c.folder / "results-input.ini")
            if state.get("dismiss", 0):
                self.dismissed = True
                self.visible = False
                write(
                    c.folder / "results-view.ini",
                    dict(Ready=0, Generation=self.generation),
                )
                return
            if self.dismissed:
                return
            if not self.visible and state.get("endingready", 0) == 1:
                self.publish()
            sequence = state.get("copy", 0)
            if sequence > self.copy_sequence:
                self.copy_sequence = sequence
                try:
                    if c.clipboard is None:
                        from menu_clipboard import Clipboard

                        c.clipboard = Clipboard()
                    c.clipboard.put(self.data["shared_seed"])
                    self.publish("copied")
                except Exception as error:
                    self.last_error = repr(error)
                    self.publish("copy_failed")
        except (
            OSError,
            ValueError,
            KeyError,
            configparser.Error,
            RuntimeError,
        ) as error:
            self.last_error = repr(error)
            return

    def reset(self):
        self.identity = None
        self.data = None
        self.dismissed = False
        self.visible = False
        write(
            self.c.folder / "results-input.ini", dict(Copy=0, Dismiss=0, EndingReady=0)
        )
        write(
            self.c.folder / "results-view.ini",
            dict(Ready=0, Generation=self.generation),
        )


def convert_frame(number, frame, objects):
    if number not in ENDING_FRAMES:
        return frame, objects
    result = copy.deepcopy(frame)
    objs = dict(objects) if isinstance(objects, dict) else dict(enumerate(objects))
    layer = max(i["layer"] for i in frame["instances"])
    for oi, old, name in (
        (PANEL, 41, "Run Result Panel"),
        (VIEW, 47, "Run Result View"),
        (INPUT, 47, "Run Result Input"),
    ):
        assert oi not in objs
        obj = copy.deepcopy(objs[old])
        obj.update(handle=oi, name=name)
        if oi == PANEL:
            obj.update(values=[-1] * 4, qualifiers=[])
            props = bytearray(obj["properties"])
            struct.pack_into(
                "<I", props, 16, struct.unpack_from("<I", props, 16)[0] | 0x6000
            )
            obj["properties"] = bytes(props)
        else:
            data = bytearray(obj["private"]["data"])
            name = (
                "results-view.ini" if oi == VIEW else "results-input.ini"
            ).encode() + b"\0"
            data[22:282] = name + bytes(260 - len(name))
            obj["private"]["data"] = bytes(data)
        objs[oi] = obj
        result["instances"].append(
            dict(
                handle=59000 + oi - 4300,
                objectInfo=oi,
                x=0,
                y=0,
                layer=layer,
                parentType=0,
                parentObjectInfo=0,
                tail="00 " * 8,
            )
        )
    return result, objs


def original_score_row(row):
    """Identify only the original post-game score dialog and its HTTP callbacks."""
    return any(
        c[3] == 2766 or b"Leaderboards" in c[-1] or b"submit" in c[-1].lower()
        for c in commands(row)
    )


def transform(frame, sections):
    if frame not in ENDING_FRAMES:
        return sections, []
    # This executable permits modified runs. Its local summary replaces the
    # original score submission flow, including callbacks and modal warnings.
    removed = 0
    result = [list(rows) for rows in sections]
    if frame == 49:
        removed = sum(original_score_row(row) for rows in sections for row in rows)
        assert removed == 9, "Original post-game leaderboard flow changed"
        result = [
            [row for row in rows if not original_score_row(row)] for rows in sections
        ]
    e = Events(result, low=0xD000, high=0xD600)
    # This cinematic has no original global-key section. Credits and Prize Room
    # already implement F2; add it only to the early ending, without a route jump.
    if frame == 47:
        restart = condition(
            -6, -1, 0, [parameter(14, struct.pack("<HH", 113, 0))], e.ident()
        )
        result.append([e.row([restart], [action(-3, 5, 0, [])])])
    rows = [
        e.row(
            [e.start()],
            [
                action(2, 26, PANEL, []),
                value(PANEL, 0, integer(-1)),
                action(
                    33,
                    123,
                    INPUT,
                    [file_path("results-input.ini"), expression(integer(0))],
                ),
                action(33, 125, INPUT, [file_path("results-input.ini")]),
            ],
        )
    ]
    always = condition(-1, -1, 0, [], e.ident())
    rows.append(
        e.row(
            [always],
            [
                action(
                    33,
                    123,
                    VIEW,
                    [file_path("results-view.ini"), expression(integer(1))],
                )
            ],
        )
    )
    rows.append(
        e.row(
            [
                e.eq(VIEW, "Menu", "Ready", 1),
                e.cmp(alt(PANEL, 0), ini_value("Menu", "Generation", 0, oi=VIEW), 1),
            ],
            [
                load_image(PANEL, "run-result.png"),
                value(PANEL, 0, ini_value("Menu", "Generation", 0, oi=VIEW)),
                action(2, 27, PANEL, []),
            ],
        )
    )
    # Original ending uses randomness.A as its 50 Hz timeline. At 750 ticks
    # (15 seconds) the rainbow is already visible; preserve the old reveal delay.
    ready = [e.cmp(alt(2462, 0), integer(750), 4)] if frame == 47 else [e.start()]
    rows.append(
        e.row(
            ready + [e.eq(INPUT, "Menu", "EndingReady", 0)],
            [set_ini("Menu", "EndingReady", 1, oi=INPUT), action(33, 124, INPUT, [])],
        )
    )
    rows.append(e.row([e.eq(VIEW, "Menu", "Ready", 0)], [action(2, 26, PANEL, [])]))
    rows.append(
        e.row(
            [e.eq(VIEW, "Menu", "Ready", 1)],
            [
                action(2, 2, PANEL, [expression(window(0))]),
                action(2, 3, PANEL, [expression(window(1))]),
            ],
        )
    )
    mouse_x = calc(struct.pack("<hhH", -6, 0, 6), 4, window(0))
    mouse_y = calc(struct.pack("<hhH", -6, 1, 6), 4, window(1))
    click = condition(-6, -5, 0, [parameter(32, struct.pack("<IH", 0, 0))], e.ident())
    left, top, right, bottom = CLOSE_BOUNDS
    rows.append(
        e.row(
            [
                click,
                e.eq(VIEW, "Menu", "Ready", 1),
                e.cmp(mouse_x, integer(left), 4),
                e.cmp(mouse_x, integer(right), 2),
                e.cmp(mouse_y, integer(top), 4),
                e.cmp(mouse_y, integer(bottom), 2),
            ],
            [
                set_ini("Menu", "Dismiss", 1, oi=INPUT),
                action(33, 124, INPUT, []),
                action(2, 26, PANEL, []),
            ],
        )
    )
    press = condition(-6, -1, 0, [parameter(14, struct.pack("<HH", 117, 0))], e.ident())
    rows.append(
        e.row(
            [press, e.eq(VIEW, "Menu", "Ready", 1)],
            [
                ini_expression(
                    "Menu",
                    "Copy",
                    e.add(ini_value("Menu", "Copy", 0, oi=INPUT), integer(1)),
                    INPUT,
                ),
                action(33, 124, INPUT, []),
            ],
        )
    )
    result.append(rows)
    return result, [
        dict(
            frame=frame,
            ending_overlay=True,
            reveal_ticks=750,
            original_score_rows_removed=removed,
            copy_key="F6",
            dismiss_button=CLOSE_BOUNDS,
            early_restart=frame == 47,
        )
    ]
