"""Original Boshy title and slot layout with supplementary Randomizer panels.

The game owns the animated title and slot selector. This adapter supplies the
settings panels and the three-slot create, resume and delete workflow.
"""

import configparser
import time
from PIL import Image, ImageDraw
from native_menu.controller import Controller
from native_menu.model import Model, Row
from native_menu.render import Renderer
from native_menu.transport import Mailbox, read
from native_menu.classic_art import prepare
from native_menu.social import URL
from native_menu import tracker_link
from menu_host.runtime import verify_engine
from menu_host.store import atomic
from export_native_run import REPO
from distribution.identity import VERSION
from native_menu.history import TITLE_CARD

from native_menu.builds import DYNAMIC_BASE as BASE, DYNAMIC_SHA as BASE_SHA


class ClassicModel(Model):
    def rows(self):
        rows = super().rows()
        if self.page == "settings":
            rows = [
                Row("new", self.t("new"), enabled=not self.saved()),
            ] + rows
        return rows

    def key(self, key, x=0, y=0):
        if self.busy:
            return
        if self.page == "home":
            if key == 1001:
                self.mouse = (x, y)
                return
            if key in (37, 38, 39, 40):
                return  # Original animated slot selector owns arrows.
            if key == 13:
                if self.saved():
                    self.action = "resume"
                else:
                    self.go("settings")
                return
            if key == 1000:
                if 438 <= x < 630:
                    if 394 <= y < 421:
                        self.key(13)
                    elif 426 <= y < 452:
                        self.go("settings")
                    elif 456 <= y < 480 and self.saved():
                        self.action = "delete"
                return
        return super().key(key, x, y)


class ClassicRenderer(Renderer):
    def __init__(self, folder):
        super().__init__(folder)
        logo = Image.open(REPO / "assets/Custom/boshy_randomizer.png").convert("RGBA")
        logo.thumbnail((302, 121), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (302, 121))
        canvas.alpha_composite(
            logo, ((302 - logo.width) // 2, (121 - logo.height) // 2)
        )
        self.write("classic-logo.png", canvas)
        self.art_generation = 1
        tracker_link.prepare(self.folder, self.fonts("en"))

    def render(self, m, step=0):
        self.prepare_art()
        f = self.fonts(m.language)
        im = Image.new("RGBA", (640, 480))
        draw = ImageDraw.Draw(im)
        tracker_link.draw(
            draw,
            f,
            busy=m.busy,
            hover=m.mouse is not None and tracker_link.contains(*m.mouse),
        )
        draw.multiline_text(
            (477, 1), m.t("menu_keys"), font=f[10], fill="#edf5f6", spacing=1
        )
        news = Image.new("RGBA", (640, 480))
        news_draw = ImageDraw.Draw(news)
        news_draw.rectangle((0, 194, 226, 480), fill=(12, 20, 29, 170))
        y = 202
        for i, line in enumerate(TITLE_CARD[m.language]):
            for j, part in enumerate(line.split("\n")):
                size = 14 if i == 0 else 12
                while size > 10 and news_draw.textlength(part, font=f[size]) > 210:
                    size -= 1
                news_draw.text(
                    (8, y + j * 17),
                    part,
                    font=f[size],
                    fill="#9aecd5" if i == 0 or (i >= 2 and j == 0) else "#edf5f6",
                )
            y += 24 if i < 2 else 48
        news_draw.text((8, 461), VERSION, font=f[10], fill="#a8bdc9")
        self.write("classic-news.png", news)
        # Both the initial Game/Options screen and save selection share this
        # footer. Draw it before exporting the initial-screen update card.
        draw.rectangle((91, 432, 122, 463), fill=(0, 0, 0, 0))
        draw.text((130, 440), URL.removeprefix("https://"), font=f[12], fill="#edf5f6")
        self.write("classic-updates.png", im)
        if m.page != "home":
            from native_menu.cards import draw as draw_cards

            im.alpha_composite(draw_cards(self, m))
        else:
            summary = m.store.summary(m.slot)
            from native_menu.save_preview import draw as draw_save_preview

            draw_save_preview(im, m, f, summary)
            draw.rounded_rectangle(
                (436, 314, 632, 479),
                radius=5,
                fill="#16232f",
                outline="#435767",
            )
            draw.text(
                (445, 319), m.t("slot") + f" {m.slot}", font=f[14], fill="#edf5f6"
            )
            hint = m.t("resume") if summary["exists"] else m.t("new")
            # Native digits and their arrow remain uncovered at x=210..430,y=319..389.
            for rect, label, enabled in (
                ((442, 395, 626, 421), "Enter · " + hint, True),
                ((442, 427, 626, 452), m.t("settings"), True),
                ((442, 457, 626, 479), m.t("delete"), summary["exists"]),
            ):
                draw.rounded_rectangle(
                    rect,
                    radius=3,
                    fill="#244342" if enabled else "#16232f",
                    outline="#8cddc6" if enabled else "#435767",
                )
                draw.text(
                    (rect[0] + 5, rect[1] + 4),
                    label,
                    font=f[11],
                    fill="#edf5f6" if enabled else "#71818d",
                )
            if m.message:
                draw.text((242, 297), m.message[:50], font=f[11], fill="#ffcc80")
            if m.busy:
                draw.rectangle((436, 314, 632, 479), fill="#16232f")
                draw.text((446, 357), m.t(m.busy_label), font=f[12], fill="#edf5f6")
        if m.busy and getattr(m, "loading_progress", None) is not None:
            from native_menu.loading import draw as draw_loading

            draw_loading(im, m, f)
        self.write("native-panel.png", im)
        return im


class ClassicController(Controller):
    def __init__(self, store, *, base=BASE, expected=BASE_SHA):
        verify_engine(base, expected)
        super().__init__(store, base=base)
        self.model = ClassicModel(store)
        self.renderer = ClassicRenderer(self.folder)
        self.last_sync = 0
        self.preview_signature = None
        prepare(self.folder)
        self.refresh_slots()
        self.mail = Mailbox(self.folder, self.renderer, self.model)

    def refresh_slots(self):
        signature = tuple((slot, str(self.store.current(slot))) for slot in (1, 2, 3))
        if signature == self.preview_signature:
            return
        for slot in (1, 2, 3):
            dest = self.folder / f"SaveFile{slot}.ini"
            if self.store.current(slot):
                atomic(dest, (self.store.folder(slot) / "SaveFile1.ini").read_bytes())
            else:
                dest.unlink(missing_ok=True)
        self.preview_signature = signature

    def open(self):
        self.preview_signature = None
        self.refresh_slots()
        super().open()

    def tick(self):
        if not self.store.active and not self.future and self.window.owned():
            self.refresh_slots()
            if self.model.page == "home" and time.monotonic() - self.last_sync > 0.08:
                self.last_sync = time.monotonic()
                try:
                    slot = read(self.folder / "native-input.ini").get("slot")
                except (OSError, ValueError, KeyError, configparser.Error):
                    slot = None
                if slot in (1, 2, 3) and slot != self.model.slot:
                    self.model.slot = slot
                    self.model.load_slot()
                    self.mail.publish()
        super().tick()
