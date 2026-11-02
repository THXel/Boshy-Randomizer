"""Original Boshy artwork, animated cast and separate save/action panels."""

import io
import math
import secrets
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from menu_host.store import atomic
from menu_host.labels import stage
from export_route_probe import REPO
from native_menu import art, layout

from platform_support.fonts import font_path

FONT = font_path()
CJK = font_path("ja")


class Renderer:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.presentation_seed = secrets.token_hex(16)
        self.cast_seed = None
        self.art_generation = 0
        self.art = art.assets()
        self.font_cache = {}
        self.portraits = {}
        self.logo = Image.open(REPO / "assets/Custom/boshy_randomizer.png").convert(
            "RGBA"
        )
        self.logo.thumbnail((380, 156), Image.Resampling.LANCZOS)
        # The original intro still uses its small native logo before our page opens.
        logo = self.logo.copy()
        logo.thumbnail((220, 88), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (220, 88))
        canvas.alpha_composite(logo, ((220 - logo.width) // 2, (88 - logo.height) // 2))
        self.write("native-logo.png", canvas)

    def write(self, name, im):
        buf = io.BytesIO()
        im.save(buf, format="PNG", compress_level=1)
        atomic(self.folder / name, buf.getvalue())

    def fonts(self, language, size="normal"):
        key = (language, size)
        if key not in self.font_cache:
            path = CJK if language == "ja" and Path(CJK).exists() else FONT
            self.font_cache[key] = {
                n: ImageFont.truetype(path, n + (2 if size == "large" and n < 18 else 0)) for n in (10, 11, 12, 13, 14, 16, 18, 56)
            }
        return self.font_cache[key]

    def prepare_art(self):
        """Choose presentation art once per application start, independent of settings."""
        if self.cast_seed != self.presentation_seed:
            self.theme, self.cast = art.choose(self.presentation_seed)
            self.cast_seed = self.presentation_seed
            self.art_generation += 1
            for side, name in zip(("left", "right", "centre"), self.cast):
                frames = self.art[0][name]
                for i in range(8):
                    frame = frames[i * len(frames) // 8].resize(
                        (192, 192), Image.Resampling.NEAREST
                    )
                    shifted = Image.new("RGBA", (192, 192))
                    shifted.alpha_composite(
                        frame, (0, round(3 * math.sin(i * math.pi / 4)))
                    )
                    self.write(f"native-cast-{side}-{i:02d}.png", shifted)

    def render(self, m, step=0, *, background=True):
        self.prepare_art()
        _, landscape, tile = self.art[1][self.theme]
        # Keep the landscape fixed; native Active objects own all idle animation.
        dx, dy = 16, 8
        im = (
            landscape.crop((dx, dy, dx + 640, dy + 480))
            if background
            else Image.new("RGBA", (640, 480))
        )
        d = ImageDraw.Draw(im)
        fonts = self.fonts(m.language)

        def text(x, y, s, n=12, color="#edf5f6", width=400):
            s = str(s)
            if d.textlength(s, font=fonts[n]) > width:
                while s and d.textlength(s + "…", font=fonts[n]) > width:
                    s = s[:-1]
                s += "…"
            d.text((x, y), s, font=fonts[n], fill=color)

        def wrap(x, y, s, width=160, n=11, max_lines=6):
            lines = []
            for paragraph in str(s).split("\n"):
                words = list(paragraph) if m.language == "ja" else paragraph.split()
                separator = "" if m.language == "ja" else " "
                line = ""
                for word in words:
                    candidate = line + (separator if line else "") + word
                    if line and d.textlength(candidate, font=fonts[n]) > width:
                        lines.append(line)
                        line = word
                    else:
                        line = candidate
                lines.append(line)
            for i, line in enumerate(lines[:max_lines]):
                if i == max_lines - 1 and len(lines) > max_lines:
                    line += "…"
                text(x, y + i * (n + 4), line, n, "#becfd7", width)

        def box(rect, selected=False):
            d.rounded_rectangle(
                rect,
                5,
                fill="#244342" if selected else "#16232f",
                outline="#8cddc6" if selected else "#435767",
                width=2 if selected else 1,
            )

        def platform(x, y, width):
            t = tile.copy()
            t.thumbnail((40, 32), Image.Resampling.NEAREST)
            strip = Image.new("RGBA", (width, 22))
            for xx in range(0, width, t.width):
                for yy in range(0, 22, t.height):
                    strip.alpha_composite(t, (xx, yy))
            im.alpha_composite(strip, (x, y))
            d.line((x, y, x + width, y), fill="#9ec883", width=2)

        # Large familiar logo and genuine animation frames, not static icon tiles.
        im.alpha_composite(self.logo, ((640 - self.logo.width) // 2, 18))
        platform(18, 174, 100)
        platform(522, 174, 100)
        text(10, 3, "Made by Solgryn", 10, width=170)
        text(480, 3, m.language.upper(), 10, width=150)
        d.rectangle((0, 461, 639, 479), fill="#101b25")
        text(12, 464, m.t("seed") + ": " + m.draft.seed, 10, "#9aecd5", 205)
        text(228, 464, m.t("controls_short"), 10, "#becfd7", 400)

        box((12, 208, 198, 455))
        if m.busy:
            text(26, 220, m.t("your_run"), 16, width=156)
            wrap(26, 258, m.t(m.busy_label), max_lines=8)
            box((210, 208, 628, 455))
            text(230, 230, m.t(m.busy_label), 16, width=376)
            for i in range(8):
                x = 354 + i * 18
                d.ellipse((x, 393, x + 7, 400), fill="#9aecd5" if i == 0 else "#365b63")
        elif m.page == "home":
            summary = m.store.summary(m.slot)
            text(26, 220, m.t("your_run"), 16, width=156)
            text(26, 251, m.t(m.draft.options["mode"]), 13, "#9aecd5", 156)
            normal = m.draft.options["mode"] == "normal"
            text(
                26,
                278,
                (
                    m.t("original_progression")
                    if normal
                    else (
                        m.t("target_count")
                        + ": "
                        + str(m.draft.options["target_count"])
                        if m.draft.options["mode"] == "target"
                        else m.t("level_count")
                        + ": "
                        + str(m.draft.options["level_count"])
                    )
                ),
                11,
                width=156,
            )
            text(
                26,
                298,
                (
                    m.t("original_rewards")
                    if normal
                    else (
                        m.t("boss_count") + ": " + str(m.draft.options["boss_count"])
                        if m.draft.options["mode"] == "target"
                        else m.t("route_boss_count")
                        + ": "
                        + str(m.draft.options["route_boss_count"])
                    )
                ),
                11,
                width=156,
            )
            name = m.draft.options["start_character"]
            text(
                26,
                320,
                m.t("auto_character") if name == "Auto" else name,
                12,
                "#9aecd5",
                156,
            )
            wrap(26, 349, m.t("menu_hint"), max_lines=6)
            box((210, 208, 628, 298))
            title = (
                stage(summary["spot"], m.language)
                if summary["exists"]
                else m.t("new_save")
            )
            # Saved spot keys are mapped through the route catalogue when available.
            if summary["exists"]:
                from menu_host.draft import LEVELS, BOSSES

                names = {
                    **LEVELS,
                    **{v[2]: v[0] for v in BOSSES.values()},
                    "boss_solgryn.ini": "Solgryn",
                }
                title = stage(names.get(summary["spot"], summary["spot"]), m.language)
            text(224, 220, str(m.slot) + " · " + title, 14, width=280)
            text(
                224,
                253,
                m.t("difficulty")
                + ": "
                + str(
                    ("Ez Mode", "Totally Average", "Hardon Mode", "You're Gonna Rage")[
                        m.draft.options["difficulty"]
                    ]
                ),
                11,
                width=390,
            )
            status = (
                (
                    str(summary["deaths"])
                    + " "
                    + m.t("deaths")
                    + " · "
                    + m.t("completed")
                    + ": "
                    + str(summary["completed"])
                )
                if summary["exists"]
                else m.t("finale")
            )
            text(224, 276, status, 10, "#9aecd5", 390)
            for i, row in enumerate(m.rows()):
                rect = layout.row_rect("home", i)
                box(rect, m.slot == i + 1 if i < 3 else m.focus == i)
                if i < 3 and m.focus == i and m.slot != i + 1:
                    d.rounded_rectangle(rect, 5, outline="#edf5f6", width=1)
                if i < 3:
                    text(
                        rect[0] + 11,
                        rect[1] + 5,
                        str(i + 1),
                        12,
                        "#9aecd5" if i + 1 == m.slot else "#edf5f6",
                        24,
                    )
                else:
                    text(
                        rect[0] + 10,
                        rect[1] + 4,
                        row.label,
                        11,
                        "#edf5f6" if row.enabled else "#71818b",
                        rect[2] - rect[0] - 18,
                    )
            # The central save number echoes the original slot-selection scene.
            text(274, 367, str(m.slot), 56, "#9aecd5", 100)
            platform(232, 434, 122)
        else:
            rows = m.visible()
            key = m.rows()[m.focus].key.split(":")[0]
            text(26, 220, m.t(m.page), 14, width=156)
            from menu_host.labels import ROWS
            from native_menu.model import CAPTIONS

            hint_key = (m.draft.options["mode"] if key == "mode" else key) + "_hint"
            if m.draft.options["mode"] in ("normal", "target") and key in (
                "level_count",
                "route_boss_count",
                "items",
                "level_pool",
                "boss_pool",
            ):
                hint_key = m.draft.options["mode"] + "_hint"
            if m.page == "targets":
                hint_key = "target_hint"
            hint = (
                m.t(hint_key)
                if hint_key in ROWS or hint_key in CAPTIONS
                else (m.t("seed_hint") if m.page == "seed" else m.t("change_short"))
            )
            wrap(26, 255, hint, max_lines=9)
            if m.saved():
                wrap(26, 401, m.t("locked"), max_lines=3)
            else:
                text(26, 421, m.t("change_short"), 10, "#9aecd5", 156)
            box((210, 208, 628, 455))
            text(222, 214, "‹ " + m.t("back"), 11, width=250)
            text(
                533,
                214,
                str(m.offset // 8 + 1) + " / " + str((len(m.rows()) + 7) // 8) + "  ›",
                11,
                width=88,
            )
            for i, row in enumerate(rows):
                rect = layout.row_rect(m.page, i)
                box(rect, m.focus == m.offset + i)
                color = "#edf5f6" if row.enabled else "#71818b"
                if m.page == "character_picker":
                    name = row.key.split(":", 1)[1]
                    if name not in self.portraits:
                        path = REPO / "assets/menu-character-icons" / (name + ".png")
                        self.portraits[name] = (
                            Image.open(path).convert("RGBA") if path.is_file() else None
                        )
                    portrait = self.portraits[name]
                    if portrait is not None:
                        portrait = portrait.copy()
                        portrait.thumbnail((58, 58), Image.Resampling.NEAREST)
                        im.alpha_composite(
                            portrait,
                            (rect[0] + (98 - portrait.width) // 2, rect[1] + 8),
                        )
                    else:
                        text(rect[0] + 40, rect[1] + 20, "?", 18, color, 25)
                    text(rect[0] + 5, rect[1] + 73, row.label, 10, color, 89)
                    if row.value:
                        text(rect[0] + 80, rect[1] + 4, row.value, 11, "#9aecd5", 16)
                    continue
                if row.key.startswith("goal:") and row.value == "✓":
                    color = "#9aecd5"
                value_width = (
                    min(
                        158, max(24, round(d.textlength(row.value, font=fonts[11])) + 8)
                    )
                    if row.value
                    else 0
                )
                label_width = rect[2] - rect[0] - 20 - value_width
                text(rect[0] + 9, rect[1] + 4, row.label, 11, color, label_width)
                if row.value:
                    text(
                        rect[2] - value_width,
                        rect[1] + 4,
                        row.value,
                        11,
                        color,
                        value_width - 4,
                    )
        if m.message:
            d.rounded_rectangle(
                (12, 341, 198, 455), 5, fill="#303b36", outline="#ddc38c"
            )
            wrap(24, 350, m.message, width=162, n=10, max_lines=7)
        self.write("native-panel.png", im)
        return im
