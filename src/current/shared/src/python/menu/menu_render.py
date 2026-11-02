"""Small native panels complement the original animated Boshy menu."""

from host_platform import replace_file
from ui_i18n import (
    tr,
    display,
    font_path,
    font_family,
    configure_tk,
    LANGUAGE,
    Localized,
)
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import os
import json
from native_models import duration
from menu_model import DIFFICULTIES, seed_layout
from run_extras import EXTRAS, SHOT_MODES, SHOT_LABELS, shot_label, presentation
from run_settings import (
    mode_name,
    RUSH_MODES,
    LEVELS,
    BOSSES as ROUTE_BOSSES,
    ADVANCED_PAGE_SIZE,
    ADVANCED_PAGES,
)
from beta_catalogue import goals, BOSSES, confirmed


class Renderer:
    def __init__(self, base):
        self.base = Path(base)
        self.icons = {
            p.stem.casefold(): p for p in (self.base / 'Custom/trophies').glob('*.png')
        }
        self.cache = {}
        self.icons.update(
            {
                p.stem.casefold(): p
                for p in (self.base / 'menu-character-icons').glob('*.png')
            }
        )
        self.fonts = {
            n: ImageFont.truetype(font_path(), n)
            for n in (10, 11, 12, 13, 14, 15, 16, 17, 19, 20, 22, 25)
        }
        folder = self.base / 'menu-runtime'
        folder.mkdir(exist_ok=True)
        logo = Image.open(self.base / 'Custom/boshy_randomizer.png').convert('RGBA')
        logo.thumbnail((302, 121), Image.Resampling.LANCZOS)
        out = Image.new('RGBA', (302, 121))
        out.alpha_composite(logo, ((302 - logo.width) // 2, (121 - logo.height) // 2))
        out.save(folder / 'logo.png')

    def appearance(self, m):
        from menu_layout import SIZES

        self.text(252, 266, tr('Menü-Darstellung'), 20)
        self.text(
            253,
            306,
            tr(
                'Fenster: {0} × {1} · Layout automatisch',
                str(m.display_size[0]),
                str(m.display_size[1]),
            ),
            13,
            '#b3c3ce',
        )
        labels = (tr('Kleine Schrift'), tr('Standardschrift'), tr('Große Schrift'))
        for i, key in enumerate(SIZES):
            y = 350 + i * 58
            self.box((251, y, 851, y + 49), m.focus == i)
            self.text(
                270,
                y + 13,
                labels[i] + ('  ✓' if m.font_size == key else ''),
                16,
                '#92ee92' if m.font_size == key else 'white',
            )
        self.wrap(
            253,
            535,
            tr(
                'Die Schriftgröße gilt für alle Menüs und bleibt auf diesem Rechner gespeichert. Spielauflösung und Seed bleiben unverändert.'
            ),
            590,
            12,
        )
        self.box((251, 604, 851, 640), m.focus == 3)
        self.text(485, 614, tr('Zurück'), 14)

    def text(self, x, y, s, n=14, color='white'):
        value = display(s)
        limit = (860 if x >= 237 else 268) - x
        if self.d.textlength(value, font=self.fonts[n]) > limit:
            value = self.fit(value, limit, n)
        self.d.text(
            (x, y),
            str(value),
            font=self.fonts[n],
            fill={
                'white': '#edf5f6',
                '#92ee92': '#92e4cd',
                '#86e486': '#92e4cd',
                '#dddddd': '#b3c3ce',
            }.get(color, color),
        )

    def fit(self, s, width, n):
        s = display(s)
        if self.d.textlength(s, font=self.fonts[n]) <= width:
            return s
        while s and self.d.textlength(s + '…', font=self.fonts[n]) > width:
            s = s[:-1]
        return Localized(s + '…')

    def wrap(self, x, y, s, width, n=12, color='#dddddd'):
        s = display(s)
        line = ''
        separator = '' if LANGUAGE == 'ja' else ' '
        for word in (list(s) if LANGUAGE == 'ja' else s.split()):
            test = (line + separator + word).strip()
            if self.d.textlength(test, font=self.fonts[n]) > width and line:
                self.text(x, y, Localized(line), n, color)
                y += round(n * getattr(self, 'font_factor', 1)) + 4
                line = word
            else:
                line = test
        if line:
            self.text(x, y, Localized(line), n, color)
            y += round(n * getattr(self, 'font_factor', 1)) + 4
        return y

    def box(self, r, selected=False):
        self.d.rounded_rectangle(
            r,
            radius=5,
            fill='#244342' if selected else '#16232f',
            outline='#8cddc6' if selected else '#435767',
            width=2 if selected else 1,
        )

    def icons_row(self, names, x, y, cols=14, size=17, done=None):
        for i, name in enumerate(names):
            k = (name.casefold(), size)
            px = x + i % cols * (size + 4)
            py = y + i // cols * (size + 5)
            if k not in self.cache:
                p = self.icons.get(k[0])
                im = (
                    Image.open(p).convert('RGBA')
                    if p
                    else Image.new('RGBA', (size, size), '#555555')
                )
                im.thumbnail((size, size), Image.Resampling.NEAREST)
                self.cache[k] = im
            im = self.cache[k]
            self.im.paste(im, (px, py), im)
            if done is not None and name in done:
                self.d.rectangle((px, py, px + size, py + size), outline='#72df71')
        return y + max(1, (len(names) + cols - 1) // cols) * (size + 5)

    def draw(self, m):
        from menu_layout import FACTORS, viewport

        factor = FACTORS.get(m.font_size, 1)
        if factor != getattr(self, 'font_factor', None):
            self.font_factor = factor
            self.fonts = {
                n: ImageFont.truetype(font_path(), max(9, round(n * factor)))
                for n in (10, 11, 12, 13, 14, 15, 16, 17, 19, 20, 22, 25)
            }
        m.presentation = viewport(m.page, m.display_size)
        self.im = Image.new('RGB', (880, 660), '#ff00ff')
        self.d = ImageDraw.Draw(self.im)
        self.updates(214 if m.page != 'slots' else 251)
        temp = self.base / 'menu-runtime/updates-next.bmp'
        self.im.save(temp)
        replace_file(temp, self.base / 'menu-runtime/updates.bmp')
        self.d.rectangle((0, 0, 879, 659), fill='#ff00ff')
        self.d.rounded_rectangle(
            (4, 298, 296, 452), radius=8, fill='#16232f', outline='#435767'
        )
        self.text(17, 310, tr('Fenstergröße'), 17)
        self.wrap(
            17,
            340,
            tr('Links / Rechts: passende Größen für diesen Bildschirm.'),
            265,
            12,
        )
        self.wrap(17, 382, tr('Letzte Option: Vollbild, gestreckt.'), 265, 12)
        if hasattr(m, 'resolution_recommended'):
            w, h = m.resolution_recommended
            self.text(
                17, 420, tr('Empfohlen: {0} × {1}', str(w), str(h)), 12, '#92e4cd'
            )
        self.im.save(self.base / 'menu-runtime/resolution-next.bmp')
        replace_file(
            self.base / 'menu-runtime/resolution-next.bmp',
            self.base / 'menu-runtime/resolution.bmp',
        )
        self.d.rectangle((0, 0, 879, 659), fill='#ff00ff')
        if m.page == 'slots':
            self.overview(m)
        else:
            self.box((237, 254, 865, 650))
            if m.page == 'new':
                self.new(m)
            elif m.page == 'appearance':
                self.appearance(m)
            elif m.page == 'advanced':
                self.advanced(m)
            elif m.page == 'extras':
                self.extras(m)
            elif m.page == 'graphics':
                self.graphics(m)
            elif m.page == 'music':
                self.music(m)
            elif m.page == 'choice':
                self.choice_dialog(m)
            elif m.page == 'shots':
                self.shots_dialog(m)
            elif m.page == 'interval':
                self.interval_dialog(m)
            elif m.page == 'presets':
                self.presets(m)
            elif m.page == 'result':
                self.result(m)
            elif m.page == 'seed':
                self.seed_dialog(m)
            elif m.page == 'seed_preview':
                self.seed_preview(m)
            elif m.page == 'discard':
                self.discard_dialog(m)
            elif m.page == 'characters':
                self.characters(m)
            elif m.page == 'delete':
                self.text(258, 284, tr('Speicherplatz {0} löschen?', str(m.slot)), 22)
                self.wrap(
                    258,
                    348,
                    tr(
                        'Nur dieser Spielstand wird gelöscht. Eine Sicherung bleibt erhalten.'
                    ),
                    568,
                    16,
                )
                self.box((255, 530, 525, 578), m.focus == 0)
                self.text(312, 543, tr('Abbrechen'), 17)
                self.box((550, 530, 850, 578), m.focus == 1)
                self.text(606, 543, tr('Löschen'), 17)
            elif m.page == 'targets':
                self.targets(m)
            else:
                self.text(263, 306, tr('Lauf wird geladen …'), 22)
        self.context_help(m)
        if m.page == 'new':
            self.box((583, 263, 625, 291), m.focus == 10)
            self.text(591, 270, 'Aa', 13)
        if m.presentation:
            source, target = m.presentation
            panel = self.im.crop(source).resize(
                (target[2] - target[0], target[3] - target[1]), Image.Resampling.NEAREST
            )
            self.im = Image.new('RGB', (880, 660), '#ff00ff')
            self.im.paste(panel, target[:2])
            self.d = ImageDraw.Draw(self.im)
        tmp = self.base / 'menu-runtime/frame-next.bmp'
        self.im.save(tmp)
        replace_file(tmp, self.base / 'menu-runtime/frame.bmp')
        m.dirty = False

    def updates(self, width=251):
        self.d.rectangle((0, 266, 285, 660), fill='#111b25')
        self.text(17, 284, 'RANDOMIZER', 11, '#90dac7')
        self.text(17, 303, 'Latest updates', 22)
        self.d.line((17, 340, 268, 340), fill='#3c5362')
        all_entries = json.loads(
            (self.base / 'menu_updates.json').read_text(encoding='utf-8')
        )['entries']
        latest = all_entries[0]
        text = (
            str(tr('Latest updates'))
            + '\r\n'
            + latest['date']
            + '\r\n\r\n'
            + str(display(latest['title']))
            + '\r\n\r\n'
            + '\r\n\r\n'.join(str(display(line)) for line in latest['lines'])
        )
        temp = self.base / 'menu-runtime/updates-next.txt'
        try:
            native_text = text.encode('cp1252')
        except UnicodeEncodeError:
            # The original MMF text object is ANSI-only. An empty text resource
            # selects the existing Unicode bitmap panel in the native renderer.
            native_text = b''
        temp.write_bytes(native_text)
        replace_file(temp, self.base / 'menu-runtime/updates.txt')
        entries = all_entries[:1]
        y = 348
        for entry in entries:
            self.text(17, y, entry['date'], 10, '#94aebd')
            y += 15
            self.text(17, y, self.fit(entry['title'], width, 14), 14, '#c7f2e5')
            y += 22
            for line in entry['lines']:
                y = self.wrap(17, y, line, width, 10, '#b3c3ce') + 2
            y += 12
        self.d.line((17, 632, 268, 632), fill='#3c5362')
        self.text(17, 643, 'Randomizer changelog.', 10, '#91a7b7')

    def overview(self, m):
        s = m.saves[m.slot]
        self.box((322, 268, 870, 364))
        self.text(
            335,
            277,
            f"{m.slot}  ·  "
            + self.fit(
                s['location'] if s['exists'] else tr('Neuer Spielstand'), 291, 19
            ),
            19,
        )
        self.box((640, 274, 682, 299), m.focus == 7)
        # Draw the note directly; Segoe UI does not include this music glyph.
        color = '#edf5f6'
        self.d.ellipse((653, 286, 659, 291), fill=color)
        self.d.line((659, 288, 659, 279, 664, 282), fill=color, width=2)
        self.box((690, 274, 732, 299), m.focus == 6)
        self.text(700, 279, 'Aa', 13)
        for i in range(3):
            x = 742 + i * 40
            self.box((x, 274, x + 36, 299), m.focus == i + 3)
            self.text(
                x + 13, 279, str(i + 1), 13, '#92ee92' if m.slot == i + 1 else 'white'
            )
        if s['exists']:
            mode = (
                tr(mode_name(s.get('settings', {}).get('mode')))
                if s.get('managed')
                else tr('Originaler Spielstand')
            )
            self.text(
                335,
                305,
                self.fit(
                    mode + '  ·  ' + s['difficulty_name'] + '  ·  ' + s['character'],
                    521,
                    12,
                ),
                12,
                '#c3d2dc',
            )
            self.text(
                335,
                325,
                tr(
                    '{0}  ·  {1} Tode  ·  {2} Level  ·  {3} Bosse',
                    str(duration(s['seconds'])),
                    str(s['deaths']),
                    str(len(s['worlds'])),
                    str(len(s['bosses'])),
                ),
                12,
            )
            self.text(
                335,
                347,
                'Seed  ' + self.fit(s['seed'] or 'Original', 470, 10),
                10,
                '#a8bdc9',
            )
        else:
            self.text(
                335,
                308,
                tr('Modus, Schwierigkeit und Randomizer nach deinem Geschmack.'),
                12,
                '#c3d2dc',
            )
            self.text(
                335,
                332,
                tr('Empfohlen: 7 Level + 7 Bosse, danach Solgryn.'),
                12,
                '#91d9c4',
            )
        self.box((604, 407, 870, 653))
        self.text(617, 417, tr('GESAMMELTE ITEMS'), 10, '#94aebd')
        self.icons_row(s['items'], 617, 436, cols=12, size=16)
        self.text(617, 490, tr('GESAMMELTE CHARAKTERE'), 10, '#94aebd')
        self.icons_row(s['characters'], 617, 509, cols=12, size=16)
        if not s['exists']:
            self.text(617, 443, tr('Deine Funde erscheinen hier.'), 12, '#a8bdc9')
            self.text(617, 516, tr('Neue Charaktere im Überblick.'), 11, '#a8bdc9')
        self.box((614, 570, 860, 593), m.focus == 2)
        self.text(
            624,
            575,
            (
                tr('Entf · Spielstand löschen')
                if s['exists']
                else tr('Advanced · Route & Start')
            ),
            11,
            '#d4bac0' if s['exists'] else 'white',
        )
        self.box((614, 600, 860, 624), m.focus == 0)
        self.text(
            624,
            605,
            (
                (
                    tr('Enter · Laden wiederholen')
                    if s.get('recovery')
                    else tr('Enter · Fortsetzen')
                )
                if s['exists']
                else tr('Enter · Neuer Lauf')
            ),
            12,
        )
        self.box((614, 630, 860, 649), m.focus == 1)
        self.text(
            624,
            633,
            tr('T · Run-Ergebnis') if s.get('completed') else tr('T · Ziele & Details'),
            11,
        )
        if m.message:
            self.text(335, 350, self.fit(m.message, 518, 10), 10, '#ffce87')

    def new(self, m):
        if m.options['mode'] == 'normal':
            self.normal_new(m)
            return
        target = m.options['mode'] == 'target'
        self.text(252, 265, tr('Neuer Lauf'), 20)
        self.box((635, 263, 854, 291), m.focus == 9)
        self.text(652, 270, tr('Vorlagen · Standard / …'), 12)
        rows = [
            (tr('Modus'), tr(mode_name(m.options['mode']))),
            (tr('Schwierigkeit'), DIFFICULTIES[m.options['difficulty']]),
        ]
        rows += (
            [
                (tr('Ziel-Items'), str(m.options['target_count'])),
                (
                    tr('Ziel-Bosse'),
                    (
                        tr('AUS')
                        if not m.options['boss_count']
                        else str(m.options['boss_count'])
                    ),
                ),
            ]
            if target
            else [
                (
                    tr('Position-Randomizer'),
                    tr('AN') if m.options['levels'] else tr('AUS'),
                ),
                (tr('Item-Randomizer'), tr('AN') if m.options['items'] else tr('AUS')),
            ]
        )
        if m.options['mode'] in RUSH_MODES:
            key = (
                'route_boss_count'
                if m.options['mode'] == 'boss_rush'
                else 'level_count'
            )
            rows[2] = (
                tr('Boss-Anzahl') if key == 'route_boss_count' else tr('Level-Anzahl'),
                str(m.options[key]) + tr(' + Solgryn-Finale'),
            )
        rows.append(
            (
                tr('Charakter-Randomizer'),
                (
                    tr('AN / F3 gesperrt')
                    if m.options['characters']
                    else tr('AUS / ')
                    + (
                        'Dark Boshy'
                        if m.options.get('start_character', 'Auto') == 'Auto'
                        else m.options['start_character']
                    )
                ),
            )
        )
        rows.append((tr('Schussstil-Randomizer'), shot_label(m.options)))
        for i, (label, value) in enumerate(rows):
            y = 295 + i * 35
            self.box((245, y, 856, y + 32), m.focus == ([1, 2, 3, 4, 5, 8][i]))
            self.text(257, y + 9, self.fit(label, 230, 13), 13)
            self.text(496, y + 9, self.fit(value, 345, 13), 13, '#92ee92')
        msg = (
            'Zufällige Ziele pro Seed, originale Truheninhalte. Endlos bis alle Ziele erfüllt sind. Ziele im separaten Live-Tracker.'
            if target
            else 'Charakterwechsel bei neuen Spots; neue Charakterfunde kommen in den Pool.'
        )
        self.box((245, 508, 856, 539), m.focus == 7)
        self.text(
            258,
            516,
            (
                tr('Advanced · Hacks (alle Level / Bosse)')
                if target
                else tr('Advanced · Route, Start & Hacks')
            ),
            13,
            'white',
        )
        self.box((245, 546, 856, 580), m.focus == 0)
        self.text(257, 555, tr('Seed'), 13)
        self.text(
            390,
            555,
            self.fit(m.seed + tr(' · Enter: teilen / einfügen'), 454, 13),
            13,
            '#92ee92',
        )
        self.text(
            255,
            587,
            self.fit(
                m.message or tr('Pfeile: Auswahl / Enter: Öffnen / Esc: Zurück'),
                590,
                11,
            ),
            11,
            '#ffcf75' if m.message else 'white',
        )
        self.box((245, 603, 856, 642), m.focus == 6)
        self.text(455, 613, tr('Lauf starten'), 17)

    def normal_new(self, m):
        from menu_controls import controls

        self.text(252, 265, tr('Neuer Lauf'), 20)
        self.box((635, 263, 854, 291), m.focus == 9)
        self.text(652, 270, tr('Vorlagen · Standard / …'), 12)
        chosen = m.options.get('start_character', 'Auto')
        rows = {
            3: (
                tr('Charakter-Randomizer'),
                tr('AN / F3 gesperrt') if m.options['characters'] else tr('AUS'),
            ),
            1: (tr('Modus'), tr('Normal')),
            2: (tr('Schwierigkeit'), DIFFICULTIES[m.options['difficulty']]),
            5: (
                tr('Startcharakter'),
                (
                    (tr('Automatisch') if m.options['characters'] else 'Dark Boshy')
                    if chosen == 'Auto'
                    else chosen
                ),
            ),
            8: (tr('Schussstil-Randomizer'), shot_label(m.options)),
        }
        for i, rect in controls(m):
            if i not in rows:
                continue
            self.box(rect, m.focus == i)
            label, value = rows[i]
            self.text(257, rect[1] + 12, self.fit(label, 230, 13), 13)
            self.text(496, rect[1] + 12, self.fit(value, 345, 13), 13, '#92ee92')
        self.text(
            255,
            480,
            self.fit(
                tr(
                    'Originaler Spielverlauf und originale Truhen. Hacks sind optional.'
                ),
                590,
                11,
            ),
            11,
            '#b3c3ce',
        )
        self.box((245, 508, 856, 539), m.focus == 7)
        self.text(258, 516, tr('Optionale Hacks'), 13, 'white')
        self.box((245, 546, 856, 580), m.focus == 0)
        self.text(257, 555, tr('Seed'), 13)
        self.text(
            390,
            555,
            self.fit(m.seed + tr(' · Enter: teilen / einfügen'), 454, 13),
            13,
            '#92ee92',
        )
        self.text(
            255,
            587,
            self.fit(
                m.message or tr('Pfeile: Auswahl / Enter: Öffnen / Esc: Zurück'),
                590,
                11,
            ),
            11,
            '#ffcf75' if m.message else 'white',
        )
        self.box((245, 603, 856, 642), m.focus == 6)
        self.text(455, 613, tr('Lauf starten'), 17)

    def advanced(self, m):
        o = m.options
        self.text(
            252,
            264,
            tr('Advanced · {0} (+ Solgryn-Finale)', tr(mode_name(o['mode']))),
            17,
        )
        controls = [
            (
                tr('Level-Anzahl'),
                str(o['level_count']) + ' / ' + str(len(o['level_pool'])),
            ),
            (
                tr('Boss-Anzahl'),
                str(o['route_boss_count']) + ' / ' + str(len(o['boss_pool'])),
            ),
            (
                tr('Startcharakter'),
                (
                    tr('Automatisch')
                    if o['start_character'] == 'Auto'
                    else o['start_character']
                )
                + tr(' · Enter: Auswahl'),
            ),
        ]
        for i, (label, value) in enumerate(controls):
            if (o['mode'] == 'boss_rush' and i == 0) or (
                o['mode'] == 'level_rush' and i == 1
            ):
                continue
            y = 299 + i * 25
            self.box((245, y, 856, y + 23), m.focus == i)
            self.text(255, y + 4, self.fit(label, 221, 12), 12)
            self.text(486, y + 4, self.fit(value, 358, 12), 12, '#92ee92')
        self.text(
            252,
            378,
            tr('BOSSE') if o['mode'] == 'boss_rush' else tr('LEVEL IM SEED-POOL'),
            12,
        )
        if o['mode'] not in RUSH_MODES:
            self.text(556, 378, tr('BOSSE'), 12)
        self.text(
            666, 378, tr('Seite {0}/{1}', m.advanced_page + 1, ADVANCED_PAGES), 10
        )
        self.box((751, 374, 791, 395), m.focus == len(LEVELS) + len(ROUTE_BOSSES) + 5)
        self.text(764, 377, '<', 12)
        self.box((799, 374, 845, 395), m.focus == len(LEVELS) + len(ROUTE_BOSSES) + 6)
        self.text(815, 377, '>', 12)
        entries = [(k, n, 'level_pool') for k, n in LEVELS.items()] + [
            (k, v[0], 'boss_pool') for k, v in ROUTE_BOSSES.items()
        ]
        for i, (key, name, pool) in enumerate(entries):
            if (o['mode'] == 'boss_rush' and pool == 'level_pool') or (
                o['mode'] == 'level_rush' and pool == 'boss_pool'
            ):
                continue
            col = 0 if i < len(LEVELS) else 1
            row = i if col == 0 else i - len(LEVELS)
            if row // ADVANCED_PAGE_SIZE != m.advanced_page:
                continue
            row %= ADVANCED_PAGE_SIZE
            x = 249 + col * 304
            y = 399 + row * 15
            width = 596 if o['mode'] in RUSH_MODES else 292
            if o['mode'] in RUSH_MODES:
                x = 249
            if m.focus == i + 3:
                self.d.rectangle(
                    (x, y, x + width, y + 14), fill='#244342', outline='#8cddc6'
                )
            self.text(
                x + 3,
                y + 1,
                self.fit(
                    ('✓ ' if key in o[pool] else '– ') + str(display(name)),
                    width - 8,
                    11,
                ),
                11,
                '#92ee92' if key in o[pool] else '#929292',
            )
        self.text(
            252,
            595,
            self.fit(
                m.message
                or tr(
                    'Weitere Level und Bosse: Bild ↑/↓ oder die Pfeile oben. Enter/Klick: ändern.'
                ),
                595,
                10,
            ),
            10,
            '#ffcf75' if m.message else '#b3c3ce',
        )
        self.box((245, 608, 548, 642), m.focus == len(entries) + 3)
        self.text(260, 618, tr('Fertig · Auswahl übernehmen'), 12)
        self.box((558, 608, 856, 642), m.focus == len(entries) + 4)
        self.text(573, 618, tr('Hacks · Pop-ups, Mausgeist & mehr'), 12)

    def extras(self, m):
        self.text(252, 265, tr('Advanced · Hacks für diesen Lauf'), 20)
        for i, (key, label, hint, default) in enumerate(EXTRAS):
            y = 293 + i * 26
            active = m.options.get('extras', {}).get(key, False)
            self.box((245, y, 856, y + 25), m.focus == i)
            self.text(
                257,
                y + 4,
                self.fit(
                    str(display(label))
                    + ('  ›' if key in ('sprite_scenery', 'music') else ''),
                    524,
                    14,
                ),
                14,
            )
            self.text(
                794,
                y + 4,
                tr('AN') if active else tr('AUS'),
                13,
                '#92e4cd' if active else '#a8bdc9',
            )
            # The focused option's full explanation lives in the left help panel.
        self.box((245, 608, 856, 642), m.focus == len(EXTRAS))
        self.text(
            260,
            618,
            (
                tr('Fertig · Auswahl übernehmen')
                if m.extras_parent == 'new'
                else tr('Zurück · Alle Extras werden im geteilten Seed gespeichert.')
            ),
            12,
        )

    def music(self, m):
        self.text(252, 265, tr('Musik & Soundpacks'), 20)
        self.box((251, 302, 851, 341), m.focus == 0)
        active = m.options['extras']['music']
        label = (
            tr('Musik-Shuffle für diesen Lauf')
            if m.music_parent[0] != 'slots'
            else tr('Musik-Shuffle wird pro Lauf eingestellt.')
        )
        self.text(267, 314, self.fit(label, 482, 14), 14)
        if m.music_parent[0] != 'slots':
            self.text(
                792,
                314,
                tr('AN') if active else tr('AUS'),
                13,
                '#92e4cd' if active else '#a8bdc9',
            )
        self.text(
            253, 355, tr('Soundpack · dauerhaft für diese Installation'), 12, '#b3c3ce'
        )
        for i, pack in enumerate(m.music_packs):
            y = 380 + i * 50
            self.box((251, y, 851, y + 43), m.focus == i + 1)
            on = m.music_pack == pack['id']
            self.text(
                267,
                y + 13,
                ('✓ ' if on else '– ') + pack['title'],
                15,
                '#92e4cd' if on else 'white',
            )
        self.wrap(
            253,
            535,
            tr(
                'Intro, Menü, Tod und Credits bleiben auch ohne Shuffle aktiv. Gilt ab dem nächsten Spielstart; unabhängig vom Seed.'
            ),
            594,
            11,
        )
        if m.message:
            self.text(253, 584, self.fit(m.message, 594, 11), 11, '#ffcf75')
        for focus, rect, label in (
            (len(m.music_packs) + 1, (251, 604, 546, 640), 'Übernehmen'),
            (len(m.music_packs) + 2, (558, 604, 851, 640), 'Abbrechen'),
        ):
            self.box(rect, m.focus == focus)
            self.text(rect[0] + 18, 615, tr(label), 14)

    def graphics(self, m):
        from run_extras import GRAPHICS_ROWS
        from menu_controls import controls

        self.text(252, 265, tr('Sprite-Chaos · Auswahl'), 20)
        for i, rect in controls(m):
            self.box(rect, m.focus == i)
            if i == len(GRAPHICS_ROWS):
                self.text(269, 615, tr('Zurück'), 14)
                continue
            key, label, _ = GRAPHICS_ROWS[i]
            value = m.options['extras'][key]
            self.text(267, rect[1] + 11, self.fit(label, 495, 14), 14)
            caption = (
                str(value) + '%'
                if key == 'sprite_dim'
                else tr('AN') if value else tr('AUS')
            )
            self.text(790, rect[1] + 11, caption, 13, '#92e4cd' if value else '#a8bdc9')
        self.text(
            253,
            577,
            tr('Pfeile: bewegen · Enter/Klick: ändern · Esc: zurück'),
            11,
            '#b3c3ce',
        )

    def choice_dialog(self, m):
        from menu_controls import controls

        self.text(252, 265, tr(m.choice_title), 20)
        self.text(
            253,
            291,
            tr('Pfeile/Tab: Auswahl · Enter/Klick: übernehmen · Esc: abbrechen'),
            11,
            '#b3c3ce',
        )
        for i, rect in controls(m):
            self.box(rect, m.focus == i)
            if i == len(m.choice_values):
                self.text(rect[0] + 18, rect[1] + 10, tr('Abbrechen'), 14)
                continue
            value, label = m.choice_values[i]
            selected = value == m.options[m.choice_name]
            label = ('✓ ' if selected else '') + str(display(label))
            self.text(
                rect[0] + 12,
                rect[1] + 11,
                self.fit(Localized(label), rect[2] - rect[0] - 22, 14),
                14,
                '#92ee92' if selected else 'white',
            )

    def shots_dialog(self, m):
        from menu_controls import controls

        self.text(252, 265, tr('Schussstil · Projektil & Schusseffekt'), 20)
        mode = m.options.get('extras', {}).get('shot_mode', 'off')
        seconds = m.options.get('extras', {}).get('shot_interval_seconds', 300)
        labels = [
            'AUS',
            'Zufällige Wartezeit',
            'Nach jedem Spot',
            'Nach jedem Tod',
            'Nach Tod & Spot',
        ]
        for i, rect in controls(m):
            self.box(rect, m.focus == i)
            if i < 5:
                chosen = SHOT_MODES[i] == mode
                label = ('✓ ' if chosen else '') + str(tr(labels[i]))
                color = '#92ee92' if chosen else 'white'
            elif i == 5:
                label = tr(
                    'Zeitgrenze einstellen · {0}:{1}',
                    str(seconds // 60),
                    f'{seconds%60:02d}',
                )
                color = 'white'
            else:
                label = tr('Zurück')
                color = 'white'
            self.text(rect[0] + 16, rect[1] + 10, Localized(label), 14, color)
        self.text(
            253,
            574,
            (
                tr(
                    'Normal: Spot bedeutet Raumwechsel. Zeitgrenze gilt nur im Zeitmodus.'
                )
                if m.options['mode'] == 'normal'
                else tr(
                    'Spot = jeder Randomizer-Übergang. Zeitgrenze gilt nur im Zeitmodus.'
                )
            ),
            11,
            '#b3c3ce',
        )
        self.text(
            253,
            590,
            tr('Pfeile/Tab: Auswahl · Enter/Klick: aktivieren · Esc: zurück'),
            10,
            '#b3c3ce',
        )

    def seed_dialog(self, m):
        valid = False
        self.text(252, 265, tr('Seed · teilen und einfügen'), 20)
        try:
            seed, o = m.seed_value(m.seed_text)
            mode = tr(mode_name(o['mode']))
            details = (
                tr('Originaler Spielverlauf')
                if o['mode'] == 'normal'
                else (
                    tr(
                        '{0} Ziel-Items / {1} Ziel-Bosse',
                        str(o['target_count']),
                        str(o['boss_count']),
                    )
                    if o['mode'] == 'target'
                    else tr(
                        '{0} Level / {1} Bosse',
                        str(o['level_count']),
                        str(o['route_boss_count']),
                    )
                )
            )
            self.text(
                253,
                296,
                self.fit(
                    mode + ' · ' + DIFFICULTIES[o['difficulty']] + ' · ' + details,
                    596,
                    11,
                ),
                11,
                '#92ee92',
            )
            self.text(
                253,
                313,
                self.fit(
                    tr('Start: ')
                    + o['start_character']
                    + tr(' / Charakterwechsel: ')
                    + (tr('AN') if o['characters'] else tr('AUS'))
                    + tr(' / Items: ')
                    + (tr('AN') if o['items'] else tr('AUS')),
                    596,
                    10,
                ),
                10,
            )
            valid = True
        except ValueError:
            self.text(
                253,
                299,
                tr('Vollständigen geteilten Seed einfügen oder neu generieren.'),
                12,
            )
        field, buttons = seed_layout(m.seed_text)
        compact = len(m.seed_text) <= 180
        if compact:
            self.text(253, 334, tr('Teilbarer Seed-Code'), 12, '#b3c3ce')
            self.text(675, 334, tr('{0} Zeichen', str(len(m.seed_text))), 11, '#b3c3ce')
        self.box(field, m.focus == 0)
        if m.seed_selected:
            self.d.rounded_rectangle(
                (field[0] + 3, field[1] + 3, field[2] - 3, field[3] - 3),
                radius=4,
                fill='#31567b',
            )
        value = m.seed_text + ('|' if m.focus == 0 and not m.seed_selected else '')
        size = (
            22
            if compact and self.d.textlength(value, font=self.fonts[22]) <= 568
            else 14 if compact else 11
        )
        lines = []
        line = ''
        for char in value:
            if line and self.d.textlength(line + char, font=self.fonts[size]) > 568:
                lines.append(line)
                line = ''
            line += char
        lines.append(line)
        limit = max(1, (field[3] - field[1] - 16) // (size + 4))
        if len(lines) > limit:
            lines = ['…'] + lines[-(limit - 1) :] if limit > 1 else [lines[-1]]
        y = field[1] + (field[3] - field[1] - len(lines) * (size + 4)) // 2
        for line in lines:
            x = (
                field[0]
                + (field[2] - field[0] - self.d.textlength(line, font=self.fonts[size]))
                // 2
                if compact and len(lines) == 1
                else field[0] + 14
            )
            self.text(x, y, Localized(line), size)
            y += size + 4
        for i, (left, right, label) in enumerate(
            (
                (251, 443, tr('Neu generieren')),
                (455, 647, tr('Kopieren')),
                (659, 851, tr('Einfügen')),
            ),
            1,
        ):
            self.box((left, buttons[0], right, buttons[1]), m.focus == i)
            self.text(left + 13, buttons[0] + 10, label, 13)
        if compact:
            from seed_share import compatibility, version_text

            info = compatibility(m.seed_text, self.base) if valid else {}
            label = (
                tr(
                    'Export version: {0} · Current: {1}',
                    version_text(info.get('release')),
                    version_text(info.get('current')),
                )
                if valid
                else tr('Code unvollständig oder ungültig.')
            )
            self.wrap(253, 505, label, 595, 12, '#92ee92' if valid else '#ffcf75')
        self.wrap(
            253,
            544,
            m.message
            or tr(
                'Strg+A: Text markieren · Strg+V: Einfügen · Strg+C: Kopieren. Übernehmen lädt Seed und Einstellungen; Esc verwirft den Entwurf.'
            ),
            595,
            11,
            '#ffcf75' if m.message else '#dddddd',
        )
        self.box((251, 604, 546, 640), m.focus == 4)
        self.text(327, 615, tr('Preview'), 14)
        self.box((558, 604, 851, 640), m.focus == 5)
        self.text(646, 615, tr('Abbrechen'), 14)

    def characters(self, m):
        self.text(252, 265, tr('Startcharakter auswählen'), 20)
        self.text(253, 288, tr('Pfeile: Auswahl · Enter: Übernehmen · Esc: Zurück'), 11)
        for i, name in enumerate(m.character_names):
            x = 249 + i % 7 * 87
            y = 303 + i // 7 * 49
            self.box((x, y, x + 82, y + 45), m.focus == i)
            if name.casefold() in self.icons:
                self.icons_row([name], x + 30, y + 3, cols=1, size=22)
            elif name == 'Auto':
                self.text(x + 32, y + 2, '?', 19, '#92ee92')
            else:
                self.text(
                    x + 26,
                    y + 5,
                    ''.join(v[0] for v in name.split())[:3],
                    14,
                    '#92ee92',
                )
            self.text(
                x + 4, y + 30, self.fit('Auto' if name == 'Auto' else name, 75, 10), 10
            )
        name = (
            m.character_names[m.focus]
            if m.focus < len(m.character_names)
            else m.options['start_character']
        )
        self.text(
            253, 557, tr('Automatisch') if name == 'Auto' else name, 16, '#92ee92'
        )
        self.wrap(
            253,
            580,
            (
                tr(
                    'Auto: Dark Boshy, bei aktivem Charakter-Randomizer zufälliger Start.'
                )
                if name == 'Auto'
                else tr('Auswahl gilt für den Start. Enter übernimmt diesen Charakter.')
            ),
            595,
            11,
        )
        self.box((249, 608, 852, 640), m.focus == len(m.character_names))
        self.text(487, 618, tr('Zurück'), 13)

    def targets(self, m):
        s = m.saves[m.slot]
        self.text(252, 265, tr('Speicherplatz {0} · Ziele & Details', str(m.slot)), 20)
        if not s['exists']:
            self.wrap(
                254,
                326,
                tr(
                    'Hier erscheinen deine gesammelten Items, Charaktere und abgeschlossenen Bosse. Dieser Speicherplatz ist noch frei.'
                ),
                576,
                16,
            )
            self.text(254, 624, tr('Esc / Enter · Zurück'), 12)
            return
        options = s.get('settings', {})
        g = goals(self.base, s.get('seed', ''), options)
        items = g['items'] or s.get('items', [])
        bosses = g['bosses'] or s.get('bosses', [])
        self.text(
            254,
            307,
            (tr('ZIEL-ITEMS') if g['items'] else tr('GESAMMELTE ITEMS'))
            + f'  ·  {len(items)}',
            12,
            '#92e4cd',
        )
        self.icons_row(
            items,
            254,
            335,
            cols=9,
            size=26,
            done=set(s.get('items', [])) if g['items'] else None,
        )
        self.text(
            558,
            307,
            tr('ZIEL-BOSSE') if g['items'] else tr('BESIEGTE BOSSE'),
            12,
            '#92e4cd',
        )
        for i, key in enumerate(bosses):
            name = BOSSES[key][0] if key in BOSSES else key
            done = name in s.get('bosses', [])
            x = 558 + (i // 11) * 147
            y = 335 + (i % 11) * 23
            self.text(
                x,
                y,
                ('✓ ' if done else '· ') + self.fit(name, 127, 11),
                11,
                '#92e4cd' if done else '#b3c3ce',
            )
        self.text(254, 446, tr('GESAMMELTE CHARAKTERE'), 12, '#92e4cd')
        self.icons_row(s.get('characters', []), 254, 474, cols=9, size=26)
        self.text(254, 553, tr('LEVEL ABGESCHLOSSEN'), 11, '#94aebd')
        self.wrap(
            254,
            575,
            ', '.join(map(str, s.get('worlds', []))) or tr('Noch keine'),
            279,
            12,
        )
        self.d.line((254, 610, 850, 610), fill='#435767')
        self.text(254, 624, tr('Esc / Enter · Zurück'), 12)

    def interval_dialog(self, m):
        self.text(252, 265, tr('Schusswechsel · zufällige Wartezeit'), 20)
        self.wrap(
            253,
            305,
            tr(
                'Nach jedem Wechsel wird eine neue Wartezeit zwischen 1 Sekunde und deiner Obergrenze gezogen.'
            ),
            593,
            13,
        )
        for i, (x, label) in enumerate(((260, tr('Minuten')), (555, tr('Sekunden')))):
            self.box((x, 354, x + 275, 414), m.focus == i)
            self.text(x + 14, 362, label, 11, '#a8bdc9')
            self.text(x + 14, 382, m.interval_fields[i] or '0', 22, '#92e4cd')
        self.wrap(
            253,
            450,
            tr(
                'Standard: 5 Minuten. Menüs und geschlossene Spiele verbrauchen keine Wechselzeit. Die Obergrenze wird mit deinem Seed geteilt.'
            ),
            590,
            13,
        )
        self.wrap(
            253,
            535,
            m.message or tr('Digits: edit · Arrows/Tab: move · Enter: confirm'),
            590,
            12,
            '#ffcf75' if m.message else '#a8bdc9',
        )
        self.box((251, 604, 546, 640), m.focus == 2)
        self.text(327, 615, tr('Übernehmen'), 14)
        self.box((558, 604, 851, 640), m.focus == 3)
        self.text(646, 615, tr('Abbrechen'), 14)

    def presets(self, m):
        self.text(252, 265, tr('Vorlagen · danach frei anpassbar'), 20)
        self.text(
            253,
            294,
            tr('Spielmodus und Anzahl der Target-Ziele bleiben erhalten.'),
            11,
            '#a8bdc9',
        )
        for i, (name, hint) in enumerate(
            (
                (
                    tr('Standard'),
                    (
                        tr('Alle Hacks deaktiviert; originaler Spielverlauf.')
                        if m.options['mode'] == 'normal'
                        else tr('Pop-ups und Mausgeist aus; übrige Hacks deaktiviert.')
                    ),
                ),
                (
                    tr('Chaos'),
                    tr(
                        'Zusätzlich Charakterwechsel sowie Schusswechsel bei Tod und Spot.'
                    ),
                ),
                (
                    tr('Training'),
                    tr('God Mode, 1-HP-Bosse, Dauerfeuer und verkürzte Animationen.'),
                ),
                (tr('Abbrechen'), tr('Aktuelle Einstellungen behalten.')),
            )
        ):
            y = 315 + i * 73
            self.box((251, y, 851, y + 60), m.focus == i)
            self.text(265, y + 8, name, 17, '#92e4cd')
            self.text(265, y + 36, self.fit(hint, 568, 11), 11)

    def result(self, m):
        r = m.result
        h = r.get('highlights', {})
        options = m.result_manifest['options']
        # Keep the upper scene and left side visible for the ending and credits.
        logo = Image.open(self.base / 'Custom/boshy_randomizer.png').convert('RGBA')
        logo.thumbnail((156, 63), Image.Resampling.LANCZOS)
        self.im.paste(logo, (693 + (156 - logo.width) // 2, 265), logo)
        self.text(253, 270, self.fit(tr('Solgryn besiegt!'), 423, 25), 25, '#92e4cd')
        mode = tr(mode_name(options.get('mode')))
        self.text(
            253,
            307,
            self.fit(
                mode
                + ' · '
                + DIFFICULTIES[options['difficulty']]
                + f" · Slot {r.get('slot',m.slot)}",
                423,
                12,
            ),
            12,
            '#b3c3ce',
        )
        names = [v['name'] for v in h.get('finds', [])]
        for x, label, value in (
            (253, tr('Run time'), duration(r.get('seconds', 0))),
            (455, tr('Deaths'), str(r.get('deaths', 0))),
            (657, tr('Collected'), str(len(names))),
        ):
            self.box((x, 337, x + 192, 395))
            self.text(x + 12, 345, label, 11, '#94aebd')
            self.text(x + 12, 362, str(value), 22)
        for x, key, title in (
            (253, 'hardest', tr('Meiste Tode')),
            (559, 'longest_boss', tr('Längster Bossabschnitt')),
        ):
            self.text(x, 408, self.fit(title, 287, 11), 11, '#94aebd')
            v = h.get(key)
            text = (
                (
                    str(display(v['name']))
                    + ' · '
                    + (
                        str(v['deaths']) + tr(' Tode')
                        if key == 'hardest'
                        else duration(v['seconds'])
                    )
                )
                if v
                else tr('Noch keine vollständigen Messdaten')
            )
            self.text(x, 426, self.fit(text, 287, 13), 13)
        self.d.line((253, 451, 849, 451), fill='#435767')
        self.text(253, 461, tr('FUNDE IN REIHENFOLGE'), 11, '#94aebd')
        # All rewards fit in three rows; a long history never covers the seed/buttons.
        cols = 25
        size = min(20, max(8, 72 // max(1, (len(names) + cols - 1) // cols) - 5))
        if names:
            self.icons_row(names, 253, 478, cols=cols, size=size)
        else:
            self.text(253, 487, tr('No recorded pickups'), 12, '#b3c3ce')
        self.text(
            253,
            554,
            self.fit('Seed · ' + str(m.result_manifest['seed']), 432, 12),
            12,
            '#c7f2e5',
        )
        self.box((698, 548, 851, 574), m.focus == 2)
        self.text(
            711,
            554,
            self.fit(tr('Copy seed'), 128, 12),
            12,
            '#92e4cd' if m.focus == 2 else 'white',
        )
        note = m.message or (
            tr('Auswertung ab diesem Update; ältere Abschnitte fehlen.')
            if h.get('partial', True)
            else tr('Ending animation and credits continue in the background.')
        )
        self.text(
            253, 579, self.fit(note, 594, 11), 11, '#ffcf75' if m.message else '#a8bdc9'
        )
        self.box((251, 604, 546, 640), m.focus == 0)
        self.text(277, 615, tr('Diesen Seed erneut spielen'), 14)
        self.box((558, 604, 851, 640), m.focus == 1)
        self.text(623, 615, tr('Zum Hauptmenü'), 14)

    def context_help(self, m):
        from menu_help import help_for

        info = help_for(m)
        if not info:
            return
        self.box((8, 266, 229, 650))
        self.text(18, 281, tr('Help'), 14, '#92ee92')
        y = self.wrap(18, 313, tr(info[0]), 194, 13) + 18
        self.wrap(18, y, tr(info[1]), 194, 12)
        self.d.line((18, 551, 216, 551), fill='#435767')
        self.wrap(
            18,
            564,
            tr('Arrows: move. Enter or click: confirm. Escape: back.'),
            194,
            11,
            '#b3c3ce',
        )

    def discard_dialog(self, m):
        from menu_controls import controls

        self.text(252, 273, tr('Unsaved changes'), 20)
        self.wrap(
            253,
            325,
            tr('Apply your Advanced changes, discard them, or keep editing?'),
            590,
            15,
        )
        labels = ['Apply changes', 'Discard changes', 'Keep editing']
        for i, rect in controls(m):
            self.box(rect, m.focus == i)
            self.text(rect[0] + 18, rect[1] + 15, tr(labels[i]), 14)

    def seed_preview(self, m):
        from menu_controls import controls
        from seed_share import version_text

        info = m.preview_version
        self.text(252, 265, tr('Seed preview'), 20)
        self.text(580, 273, f'{m.preview_page+1} / {m.preview_pages}', 12)
        self.text(
            253,
            303,
            tr(
                'Export version: {0} · Current: {1}',
                version_text(info['release']),
                version_text(info['current']),
            ),
            11,
            '#b3c3ce',
        )
        warnings = {
            'unknown': 'Older seed: rule version unknown. Identical gameplay cannot be verified.',
            'different': 'Different game rules detected. Results may differ on this installation.',
            'matching': 'Game rule fingerprint matches this installation.',
        }
        self.wrap(
            253,
            325,
            tr(warnings[info['status']]),
            590,
            12,
            '#92ee92' if info['status'] == 'matching' else '#ffcf75',
        )
        self.text(
            253,
            365,
            tr(
                'Changes below; otherwise all settings are shown. Page Up/Down: browse.'
            ),
            10,
            '#b3c3ce',
        )
        for i, (label, a, b, changed) in enumerate(
            m.preview_rows[m.preview_page * 6 : (m.preview_page + 1) * 6]
        ):
            y = 385 + i * 34
            self.text(253, y, self.fit(label, 237, 11), 11)
            text = f'{a} → {b}' if changed else b
            self.text(
                496, y, self.fit(text, 348, 11), 11, '#ffcf75' if changed else '#92ee92'
            )
        for i, rect in controls(m):
            self.box(rect, m.focus == i)
            self.text(
                rect[0] + 14, rect[1] + 10, tr(['<', '>', 'Apply seed', 'Back'][i]), 13
            )
