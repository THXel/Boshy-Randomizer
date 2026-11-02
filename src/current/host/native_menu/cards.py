"""Compact menu cards, using the game's existing portraits and shared hit targets."""

from PIL import Image, ImageDraw
from native_menu import layout


def draw(renderer, model):
    from native_menu.model import ADJUSTABLE

    image = Image.new("RGBA", layout.SIZE)
    d = ImageDraw.Draw(image)
    large = getattr(model, "font_size", "normal") == "large"
    fonts = renderer.fonts(model.language, "large" if large else "normal")

    def text(x, y, value, width, size=11, color="#edf5f6"):
        value = str(value)
        if d.textlength(value, font=fonts[size]) > width:
            while value and d.textlength(value + "…", font=fonts[size]) > width:
                value = value[:-1]
            value += "…"
        d.text((x, y), value, font=fonts[size], fill=color)

    from native_menu import icons

    def badge(row, x, y, width=75):
        on = row.value == "✓"
        color = "#9aecd5" if on else "#cad6df"
        if not row.enabled:
            color = "#7e8c97"
        d.rounded_rectangle(
            (x, y, x + width, y + 23),
            4,
            fill="#22594b" if on and row.enabled else "#253440",
            outline=color,
            width=1,
        )
        d.rectangle(
            (x + 6, y + 6, x + 17, y + 17),
            fill=color if on else None,
            outline=color,
            width=2,
        )
        if on:
            d.line(
                [(x + 8, y + 11), (x + 11, y + 14), (x + 16, y + 8)],
                fill="#12372d",
                width=2,
            )
        if not on:
            d.line((x + 9, y + 11, x + 14, y + 11), fill=color, width=2)
        text(
            x + 23,
            y + 4,
            model.t("state_on" if on else "state_off"),
            width - 27,
            10,
            color,
        )

    d.rounded_rectangle(layout.PANEL, 6, fill="#121f2b", outline="#435767")
    from native_menu.help import summary

    title, counts = summary(model, compact=True)
    text(24, 207, "‹ " + model.t("back"), 92)
    text(134, 202, title + " · " + model.t(model.page), 365, 12, "#9aecd5")
    text(134, 220, counts, 365, 10, "#becfd7")
    rows = model.visible()
    allrows = model.rows()
    pages = (len(allrows) + layout.PAGE_SIZE - 1) // layout.PAGE_SIZE
    if pages > 1:
        text(511, 207, "‹", 22, 14)
        text(543, 207, f"{model.offset//layout.PAGE_SIZE+1}/{pages}", 41, 10)
        text(598, 207, "›", 20, 14)
    for i, row in enumerate(rows):
        x, y, right, bottom = layout.row_rect(model.page, i)
        selected = model.focus == model.offset + i
        d.rounded_rectangle(
            (x, y, right - 1, bottom - 1),
            4,
            fill="#244342" if selected else "#1a2a37",
            outline="#8cddc6" if selected else "#435767",
            width=2 if selected else 1,
        )
        color = "#edf5f6" if row.enabled else "#71818b"
        if model.page == "character_picker":
            icons.draw_row(image, model, row, (x + 53, y + 2, x + 93, y + 45))
            text(x + 7, y + 50, row.label, right - x - 14, 11, color)
            if row.value:
                d.rounded_rectangle(
                    (right - 29, y + 5, right - 7, y + 27), 3, fill="#9aecd5"
                )
                d.line(
                    [(right - 25, y + 15), (right - 20, y + 21), (right - 11, y + 10)],
                    fill="#12372d",
                    width=3,
                )
        elif model.page in layout.LIST_PAGES:
            reserved = (
                min(120, round(d.textlength(row.value, font=fonts[10])) + 12)
                if row.value
                else 0
            )
            icons.draw_row(image, model, row, (x + 4, y + 2, x + 24, y + 22))
            text(x + 31, y + 4, row.label, right - x - 41 - reserved, 11, color)
            if row.value:
                text(right - reserved, y + 5, row.value, reserved - 6, 10, color)
        else:
            icons.draw_row(image, model, row, (x + 7, y + 4, x + 33, y + 30))
            boolean = row.value in ("✓", "—")
            if boolean:
                # Meaning is encoded by shape, word and contrast, not color alone.
                from native_menu.help import wrapped

                lines = wrapped(
                    d, row.label, fonts[11], right - x - 130, model.language
                )
                for n, line in enumerate(lines[:2]):
                    text(x + 43, y + 2 + n * (16 if large else 14), line, right - x - 130, 11, color)
                badge(row, right - 81, y + 5)
            else:
                text(x + 43, y + 2, row.label, right - x - 65, 11, color)
                if row.value:
                    text(
                        x + 43,
                        y + 18,
                        row.value,
                        right - x - 108 if row.key in ADJUSTABLE else right - x - 54,
                        10,
                        "#9aecd5" if row.enabled else color,
                    )
                elif row.enabled:
                    text(right - 18, y + 18, "›", 12, 11, "#9aecd5")
            if not row.enabled:
                d.rectangle(
                    (x + 23, y + 21, x + 32, y + 29), fill="#1a2a37", outline="#a5b1bb"
                )
                d.arc((x + 24, y + 16, x + 31, y + 25), 180, 360, fill="#a5b1bb")
            if row.key in ADJUSTABLE:
                for direction, symbol in ((-1, "−"), (1, "+")):
                    a, b, c, e = layout.adjust_rect(model.page, i, direction)
                    d.rectangle((a, b, c - 1, e - 1), outline="#435767")
                    text(a + 7, b + 1, symbol, 16, 11, color)
    if model.page == "seed":
        d.rounded_rectangle((24, 323, 616, 380), 4, fill="#1a2a37", outline="#435767")
        text(36, 329, model.t("current_seed"), 550, 11, "#becfd7")
        text(36, 349, model.draft.seed, 550, 18, "#9aecd5")
    if model.page not in layout.LIST_PAGES:
        row = allrows[model.focus]
        from native_menu.help import explanation, wrapped

        detail = explanation(model, row)
        d.rounded_rectangle((20, 383 if large else 389, 620, 453 if large else 450), 4, fill="#101b25")
        lines = wrapped(d, detail, fonts[11], 580, model.language)
        for index, line in enumerate(lines[:4]):
            text(
                28,
                (385 if large else 391) + index * (16 if large else 14),
                line,
                580,
                11,
                "#ddc38c" if model.message or not row.enabled else "#becfd7",
            )
    d.rectangle((12, 461, 639, 479), fill="#101b25")
    text(20, 464, model.t("compact_controls"), 610, 10, "#becfd7")
    return image
