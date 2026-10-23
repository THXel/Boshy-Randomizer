"""Small wrapping strip for active modifiers, separate from collected rewards."""

from ui_i18n import (
    tr,
    display,
    font_path,
    font_family,
    configure_tk,
    LANGUAGE,
    Localized,
)
import tkinter as tk
import math
import json
import time
from pathlib import Path
from PIL import Image, ImageTk


class ExtraStrip(tk.Canvas):
    def __init__(self, parent, base):
        super().__init__(parent, height=28, bg='#14161a', highlightthickness=0)
        self.base = Path(base)
        self.rows = []
        self.signature = None
        self.cells = {}
        self.tip = None
        self.photos = {}
        self.countdown = False
        self.bind('<Configure>', lambda e: self.draw())
        self.bind('<Motion>', self.motion)
        self.bind('<Leave>', lambda e: self.hide_tip())

    def update_rows(self, rows, countdown=False):
        self.rows = rows
        self.countdown = countdown
        signature = json.dumps(rows, sort_keys=True) + str(countdown)
        if signature != self.signature:
            self.signature = signature
            self.draw()

    def draw(self):
        self.delete('all')
        self.cells = {}
        width = max(100, self.winfo_width())
        x = 0
        y = 0
        for i, row in enumerate(self.rows):
            remaining = row.get('remaining')
            text = row['icon']
            if self.countdown and remaining is not None:
                text += f' {int(math.ceil(remaining))//60}:{int(math.ceil(remaining))%60:02d}'
            w = 78 if len(text) > 2 else 28
            if x + w > width:
                x = 0
                y += 29
            tag = 'extra' + str(i)
            self.create_rectangle(
                x + 1,
                y + 2,
                x + w - 3,
                y + 26,
                fill='#21333e',
                outline='#456170',
                tags=tag,
            )
            style = row.get('style')
            photo = None
            if style:
                if style not in self.photos:
                    path = self.base / 'menu-character-icons' / (style + '.png')
                    if path.exists():
                        im = Image.open(path).convert('RGBA')
                        im.thumbnail((19, 19))
                        self.photos[style] = ImageTk.PhotoImage(im, master=self)
                photo = self.photos.get(style)
            if photo:
                self.create_image(x + 13, y + 14, image=photo, tags=tag)
                if w > 28:
                    self.create_text(
                        x + 30,
                        y + 14,
                        text=text.split(' ', 1)[-1],
                        anchor='w',
                        fill='#bdecd9',
                        font=(font_family(), 9),
                        tags=tag,
                    )
            else:
                self.create_text(
                    x + w / 2 - 1,
                    y + 14,
                    text=text,
                    fill='#bdecd9',
                    font=(font_family(), 10, 'bold'),
                    tags=tag,
                )
            self.cells[tag] = row
            x += w
        self.configure(height=y + 29 if self.rows else 1)

    def motion(self, event):
        tag = next((t for t in self.gettags('current') if t in self.cells), None)
        self.hide_tip()
        if tag is None:
            return
        row = self.cells[tag]
        text = str(display(row['label'])) + '\n' + str(display(row['hint']))
        if 'remaining' in row:
            text += '\n' + tr(
                'Nächster Wechsel in {0} Sekunden Spielzeit',
                math.ceil(row['remaining']),
            )
        self.tip = tk.Toplevel(self)
        self.tip.overrideredirect(True)
        self.tip.attributes('-topmost', True)
        tk.Label(
            self.tip,
            text=text,
            bg='#303843',
            fg='white',
            justify='left',
            padx=7,
            pady=4,
            font=(font_family(), 10),
        ).pack()
        self.tip.geometry(f'+{event.x_root+10}+{event.y_root+18}')

    def hide_tip(self):
        if self.tip:
            self.tip.destroy()
            self.tip = None
