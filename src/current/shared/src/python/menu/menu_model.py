"""Main-menu state and save summaries, independent of the native renderer."""

from ui_i18n import (
    tr,
    display,
    font_path,
    font_family,
    configure_tk,
    LANGUAGE,
    Localized,
)
import json
import secrets
from menu_seed import renew_on_edit
from copy import deepcopy
from run_extras import EXTRAS, defaults as extra_defaults, upgrade, SHOT_MODES
from run_settings import (
    defaults,
    normalize,
    decode,
    encode,
    character,
    LEVELS,
    BOSSES as ROUTE_BOSSES,
)
from run_settings import ADVANCED_PAGE_SIZE, ADVANCED_PAGES, LEGACY_LEVELS, NEW_LEVELS
from beta_catalogue import catalogue, EXTRA_BOSSES, MINIBOSSES, stage_achievements
from native_models import slot_summary, ini

DIFFICULTIES = {
    0: 'Ez Mode',
    1: 'Totally Average',
    2: 'Hardon Mode',
    3: "You're Gonna Rage",
}
BOSSES = {
    'hellokitty': 'Hello Kitty',
    'kingdedede': 'King Dedede',
    'biollante': 'Biollante',
    'sonic': 'Sonic',
    'skeletonking': 'Skeleton King',
    'megaman': 'Mega Man',
    'shangtsung': 'Shang Tsung',
    'ganon': 'Ganon',
    'missingno': 'Missingno',
    'mario': 'Mario',
    'ryu': 'Ryu',
    'solgryn': 'Solgryn',
    'randomness': 'Random World',
}


def summary(store, slot):
    d = slot_summary(store, slot)
    if not d['exists']:
        return d
    data = ini(store, store.base / 'IWBTB' / f'SaveFile{slot}.ini')
    a = data.get('achievements', {})
    d['worlds'] = [i for i in range(1, 12) if int(a.get(f'world{i}clear', 0)) >= 1]
    d['bosses'] = [v for k, v in BOSSES.items() if int(a.get(k, 0)) >= 2]
    d['difficulty_name'] = DIFFICULTIES.get(d['difficulty'], tr('Unbekannt'))
    m = store.current(slot)
    d['settings'] = m.get('options', {}) if d['managed'] else {}
    if d['managed']:
        d['characters'] = sorted(set(d.get('characters_in_run', [])))
    d['recovery'] = None
    if d['managed']:
        path = store.root / m['run_id'] / 'progress.json'
        if path.exists():
            progress = json.loads(path.read_text(encoding='utf-8'))
            if (
                progress.get('run_id') == m['run_id']
                and progress.get('binding') == m['session_binding']
            ):
                d['recovery'] = progress.get('pending')
                point = m.get('pool', {}).get(progress.get('spot'), {})
                if point.get('frame') == d['frame'] and point.get('label'):
                    d['location'] = point['label']
                from beta_catalogue import BETA

                earned = stage_achievements(m['options'], progress, a)
                d['bosses'] = [
                    v[0]
                    for k, v in catalogue(m['options']).items()
                    if int(earned.get(k, 0)) >= 2
                ]
                if int(a.get('solgryn', 0)) >= 2:
                    d['bosses'].append('Solgryn')
    return d


def seed_layout(value):
    compact = len(value) <= 180
    return (
        ((251, 353, 851, 433), (451, 489))
        if compact
        else ((251, 329, 851, 486), (499, 533))
    )


class Menu:
    def __init__(self, store, slot=1):
        from menu_layout import load

        self.font_size = load(store.base)
        self.display_size = (1760, 1320)
        self.presentation = None
        self.requested_slot = None
        self.advanced_page = 0
        self.clipboard = None
        self.seed_text = ''
        self.seed_selected = False
        self.character_names = []
        self.store = store
        self.slot = slot
        self.page = 'slots'
        self.focus = 0
        self.seed = secrets.token_hex(4).upper()
        self.options = dict(
            difficulty=1,
            levels=True,
            items=True,
            characters=False,
            mode='randomizer',
            target_count=5,
            boss_count=0,
        )
        self.options.update(defaults())
        self.options['extras'] = self.extra_defaults()
        self.message = ''
        self.dirty = True
        self.action = None
        self.reload()

    def consume_seed(self):
        # A prepared run owns its seed. Keep the chosen settings for the next draft.
        previous = self.seed
        self.seed = secrets.token_hex(4).upper()
        while self.seed == previous:
            self.seed = secrets.token_hex(4).upper()
        self.seed_origin = None
        self.seed_text = ''
        self.seed_selected = False

    def reload(self):
        self.saves = {i: summary(self.store, i) for i in (1, 2, 3)}
        self.dirty = True
        if self.page == 'slots':
            self.focus = 0

    def select(self, slot):
        if self.slot != slot:
            self.focus = 0
        self.slot = slot
        self.dirty = True

    @renew_on_edit
    def key(self, key):
        self.dirty = True
        from menu_controls import navigate

        if key in (9, 4096) and navigate(self, key):
            return
        if (
            key in (37, 38, 39, 40)
            and not (self.page == 'slots' and key in (37, 39))
            and navigate(self, key)
        ):
            return
        if self.page == 'seed_preview' and key in (33, 34):
            self.preview_page = max(
                0,
                min(
                    self.preview_pages - 1, self.preview_page + (-1 if key == 33 else 1)
                ),
            )
            return
        if self.page == 'advanced' and key in (33, 34):
            self.flip_advanced(-1 if key == 33 else 1)
            return
        if self.page == 'slots':
            if key == 37:
                self.select((self.slot - 2) % 3 + 1)
            elif key == 39:
                self.select(self.slot % 3 + 1)
            elif key in (38, 40, 9):
                order = [0, 1] if self.saves[self.slot]['exists'] else [2, 0, 1]
                self.focus = order[
                    (order.index(self.focus) + (-1 if key == 38 else 1)) % len(order)
                ]
            elif key == 13:
                if self.focus == 7:
                    self.open_music()
                elif self.focus == 6:
                    self.open_appearance()
                elif self.focus >= 3:
                    self.requested_slot = self.focus - 2
                elif self.focus == 2:
                    if self.saves[self.slot]['exists']:
                        self.key(46)
                    else:
                        self.open_advanced()
                elif self.focus == 1:
                    if not self.open_saved_result():
                        self.page = 'targets'
                elif self.saves[self.slot]['exists']:
                    if not (
                        self.saves[self.slot].get('completed')
                        and self.open_saved_result()
                    ):
                        self.action = ('resume', self.slot, None)
                else:
                    self.page = 'new'
                    self.focus = 1
            elif key == 46 and self.saves[self.slot]['exists']:
                self.page = 'delete'
                self.focus = 0
            elif key == 27:
                self.action = ('quit', 0, None)
        elif self.page == 'new':
            if key == 27:
                self.page = 'slots'
                self.focus = 0
            elif key in (38, 40, 9):
                order = [9, 1, 2, 3, 4, 5, 8, 7, 0, 6]
                self.focus = order[
                    (order.index(self.focus) + (-1 if key == 38 else 1)) % len(order)
                ]
            elif self.focus == 0 and key == 13:
                self.open_seed()
            elif key == 13 and 1 <= self.focus <= 5:
                if self.focus == 1:
                    self.open_choice(
                        'Modus',
                        [
                            ('randomizer', 'Randomizer'),
                            ('target', 'Target Select'),
                            ('normal', 'Normal'),
                            ('boss_rush', 'Boss Rush'),
                            ('level_rush', 'Level Rush'),
                        ],
                        'mode',
                    )
                elif self.focus == 2:
                    self.open_choice(
                        'Schwierigkeit', list(DIFFICULTIES.items()), 'difficulty'
                    )
                elif self.focus == 5:
                    if self.options['mode'] == 'normal':
                        self.open_characters()
                    else:
                        self.options['characters'] = not self.options['characters']
                elif self.options['mode'] == 'normal' and self.focus == 3:
                    self.options['characters'] = not self.options['characters']
                elif self.options['mode'] == 'target':
                    name, limit = (
                        ('target_count', 19)
                        if self.focus == 3
                        else ('boss_count', len(catalogue(self.options)))
                    )
                    self.open_choice(
                        'Ziel-Items' if self.focus == 3 else 'Ziel-Bosse',
                        [
                            (n, str(n))
                            for n in range(1 if self.focus == 3 else 0, limit + 1)
                        ],
                        name,
                    )
                elif (
                    self.options['mode'] in ('boss_rush', 'level_rush')
                    and self.focus == 3
                ):
                    name, pool = (
                        ('route_boss_count', 'boss_pool')
                        if self.options['mode'] == 'boss_rush'
                        else ('level_count', 'level_pool')
                    )
                    self.open_choice(
                        'Boss-Anzahl' if name == 'route_boss_count' else 'Level-Anzahl',
                        [(n, str(n)) for n in range(1, len(self.options[pool]) + 1)],
                        name,
                    )
                elif self.options['mode'] != 'normal':
                    name = 'levels' if self.focus == 3 else 'items'
                    self.options[name] = not self.options[name]
            elif self.focus == 6 and key == 13:
                try:
                    seed, options = decode(self.seed, self.options)
                    self.action = ('new', self.slot, dict(seed=seed, options=options))
                    self.message = ''
                except ValueError as e:
                    self.message = str(display(str(e)))
                    self.focus = 0
            elif self.focus == 10 and key == 13:
                self.open_appearance()
            elif self.focus == 9 and key == 13:
                self.page = 'presets'
                self.focus = 0
                self.message = ''
            elif self.focus == 8 and key == 13:
                self.open_shots()
            elif self.focus == 7 and key == 13:
                if self.options['mode'] == 'normal':
                    self.open_extras()
                else:
                    self.open_advanced()

        elif self.page == 'appearance':
            if key == 27 or (key == 13 and self.focus == 3):
                self.page, self.focus = self.appearance_parent
                self.message = ''
            elif key == 13 and self.focus in (0, 1, 2):
                from menu_layout import SIZES, save

                self.font_size = SIZES[self.focus]
                save(self.store.base, self.font_size)
        elif self.page == 'seed_preview':
            self.preview_key(key)
        elif self.page == 'discard':
            self.discard_key(key)
        elif self.page == 'choice':
            self.choice_key(key)
        elif self.page == 'shots':
            self.shots_key(key)
        elif self.page == 'interval':
            self.interval_key(key)
        elif self.page == 'presets':
            self.preset_key(key)
        elif self.page == 'result':
            self.result_key(key)
        elif self.page == 'seed':
            self.seed_key(key)
        elif self.page == 'characters':
            self.character_key(key)
        elif self.page == 'advanced':
            self.advanced_key(key)
        elif self.page == 'extras':
            self.extras_key(key)
        elif self.page == 'graphics':
            self.graphics_key(key)
        elif self.page == 'music':
            self.music_key(key)
        elif self.page == 'targets':
            if key in (27, 13, 9):
                self.page = 'slots'
        elif self.page == 'delete':
            if key == 27:
                self.page = 'slots'
            elif key in (37, 39, 9):
                self.focus = 1 - self.focus
            elif key == 13:
                if self.focus == 1:
                    self.action = ('delete', self.slot, None)
                else:
                    self.page = 'slots'

    def char(self, value):
        if self.page == 'interval' and self.focus < 2 and 48 <= value <= 57:
            old = self.interval_fields[self.focus]
            self.interval_fields[self.focus] = (
                (old + chr(value))[-4:] if not self.interval_selected else chr(value)
            )
            self.interval_selected = False
            self.dirty = True
            self.message = ''
            return
        if self.page == 'seed' and self.focus == 0 and 32 <= value <= 126:
            if self.seed_selected:
                self.seed_text = ''
                self.seed_selected = False
            if len(self.seed_text) < 4096:
                self.seed_text += chr(value)
            self.message = ''
            self.dirty = True

    def hover(self, x, y):
        from menu_controls import hit

        focus = hit(self, x, y)
        if focus is not None and focus != self.focus:
            self.focus = focus
            self.dirty = True

    def click(self, x, y):
        from menu_controls import hit

        focus = hit(self, x, y)
        if focus is None:
            return
        self.focus = focus
        self.dirty = True
        if self.page == 'seed' and focus == 0:
            return
        if self.page == 'interval' and focus < 2:
            self.interval_selected = True
            return
        self.key(13)

    def open_appearance(self):
        from menu_layout import SIZES

        self.appearance_parent = (self.page, self.focus)
        self.page = 'appearance'
        self.focus = SIZES.index(self.font_size)
        self.message = ''
        self.dirty = True

    def open_choice(self, title, values, name):
        self.choice_parent = (self.page, self.focus)
        self.choice_title = title
        self.choice_values = values
        self.choice_name = name
        self.page = 'choice'
        self.focus = next(
            (i for i, (value, _) in enumerate(values) if value == self.options[name]), 0
        )

    def choice_key(self, key):
        if key == 27 or (key == 13 and self.focus == len(self.choice_values)):
            self.page, self.focus = self.choice_parent
            return
        if key == 13:
            value = self.choice_values[self.focus][0]
            if self.choice_name == 'mode':
                self.change_mode(value)
            else:
                self.options[self.choice_name] = value
            self.page, self.focus = self.choice_parent

    def change_mode(self, value):
        old = self.options['mode']
        if value == old:
            return
        drafts = getattr(self, 'mode_drafts', {})
        drafts[old] = deepcopy(self.options)
        if value in drafts:
            self.options = deepcopy(drafts[value])
        else:
            self.options['mode'] = value
            if value in ('boss_rush', 'level_rush') or old in (
                'boss_rush',
                'level_rush',
            ):
                self.options.update(defaults())
                self.options['levels'] = True
            if value == 'normal':
                # Normal starts clean; hacks are explicit opt-ins in this mode.
                self.options['extras'] = extra_defaults()
                for name, _, _, _ in EXTRAS:
                    self.options['extras'][name] = False
                self.options.update(
                    levels=False, items=False, characters=False, start_character='Auto'
                )
            self.options = normalize(self.options)
        self.mode_drafts = drafts

    def open_shots(self):
        self.page = 'shots'
        self.focus = SHOT_MODES.index(
            self.options.get('extras', {}).get('shot_mode', 'off')
        )
        self.message = ''

    def shots_key(self, key):
        if key == 27 or (key == 13 and self.focus == 6):
            self.page = 'new'
            self.focus = 8
            return
        if key == 13:
            if self.focus == 5:
                self.open_interval()
            else:
                upgrade(self.options)['shot_mode'] = SHOT_MODES[self.focus]

    def open_advanced(self):
        self.advanced_before = deepcopy(self.options)
        if self.options['mode'] == 'target':
            self.open_extras()
            return
        if self.options['mode'] == 'normal':
            self.page = 'new'
            self.focus = 5
            return
        self.page = 'advanced'
        self.focus = 1 if self.options['mode'] == 'boss_rush' else 0
        self.advanced_page = 0

    def open_extras(self):
        if self.page != 'advanced':
            self.advanced_before = deepcopy(self.options)
        self.extras_parent = 'advanced' if self.page == 'advanced' else 'new'
        # Explicitly opening the page does not silently alter an imported old seed.
        self.page = 'extras'
        self.focus = 0
        self.message = ''

    def extra_defaults(self):
        value = extra_defaults()
        try:
            saved = json.loads(
                (self.store.base / 'INI/menu-preferences.json').read_text(
                    encoding='utf-8'
                )
            )
            if isinstance(saved, dict) and type(saved.get('spider')) is bool:
                value['spider'] = saved['spider']
        except (OSError, ValueError):
            pass
        return value

    def extras_key(self, key):
        if key == 27 or (key == 13 and self.focus == len(EXTRAS)):
            if self.extras_parent == 'new':
                self.finish_advanced(key == 13)
                return
            self.page = self.extras_parent
            self.focus = (
                (len(LEVELS) + len(ROUTE_BOSSES) + 4) if self.page == 'advanced' else 7
            )
            return
        if key in (38, 40, 9):
            self.focus = (self.focus + (-1 if key == 38 else 1)) % (len(EXTRAS) + 1)
        elif key == 13 and self.focus < len(EXTRAS):
            upgrade(self.options)
            name = EXTRAS[self.focus][0]
            if name == 'sprite_scenery':
                self.page = 'graphics'
                self.focus = 0
                return
            if name == 'music':
                self.open_music()
                return
            self.options['extras'][name] = not self.options['extras'][name]

    def open_music(self):
        from soundpacks import available, selected

        self.music_parent = (self.page, self.focus)
        self.music_before = self.options['extras']['music']
        self.music_pack = selected(self.store.base)
        self.music_packs = available(self.store.base)
        self.page = 'music'
        self.focus = 0
        self.message = ''

    def music_key(self, key):
        from soundpacks import select

        count = len(self.music_packs)
        if key == 27 or key == 13 and self.focus == count + 2:
            self.options['extras']['music'] = self.music_before
            self.page, self.focus = self.music_parent
            self.message = ''
            return
        if key != 13:
            return
        if self.focus == 0:
            if self.music_parent[0] != 'slots':
                self.options['extras']['music'] = not self.options['extras']['music']
        elif 1 <= self.focus <= count:
            self.music_pack = self.music_packs[self.focus - 1]['id']
        elif self.focus == count + 1:
            try:
                select(self.store.base, self.music_pack)
            except (OSError, ValueError, KeyError, RuntimeError) as error:
                self.message = tr('Soundpack konnte nicht geladen werden.')
                return
            self.page, self.focus = self.music_parent
            self.message = ''

    def graphics_key(self, key):
        from run_extras import GRAPHICS_ROWS

        if key == 27 or key == 13 and self.focus == len(GRAPHICS_ROWS):
            self.page = 'extras'
            self.focus = len(EXTRAS) - 1
            return
        if key != 13 or not 0 <= self.focus < len(GRAPHICS_ROWS):
            return
        value = upgrade(self.options)
        name = GRAPHICS_ROWS[self.focus][0]
        if name == 'sprite_dim':
            value[name] = (0, 20, 40, 60)[((0, 20, 40, 60).index(value[name]) + 1) % 4]
        else:
            value[name] = not value[name]

    def finish_advanced(self, apply):
        before = getattr(self, 'advanced_before', deepcopy(self.options))
        if not apply and before != self.options:
            self.discard_parent = (self.page, self.focus)
            self.page = 'discard'
            self.focus = 2
            return
        if apply:
            try:
                normalize(self.options)
            except ValueError as e:
                self.message = str(display(str(e)))
                return
            value = self.options.get('extras', {}).get('spider')
            if type(value) is bool and value != before.get('extras', {}).get('spider'):
                from native_session import write_json

                path = self.store.base / 'INI/menu-preferences.json'
                try:
                    prefs = json.loads(path.read_text(encoding='utf-8'))
                except (OSError, ValueError):
                    prefs = {}
                if not isinstance(prefs, dict):
                    prefs = {}
                prefs['spider'] = value
                write_json(path, prefs)
        self.advanced_before = None
        self.page = 'new'
        self.focus = 7
        self.message = ''

    def discard_key(self, key):
        if key == 27 or (key == 13 and self.focus == 2):
            self.page, self.focus = self.discard_parent
            return
        if key == 13:
            if self.focus == 1:
                self.options = deepcopy(self.advanced_before)
            self.page, self.focus = self.discard_parent
            self.finish_advanced(True)

    def open_preview(self):
        from menu_help import preview_rows
        from seed_share import compatibility

        seed, options = self.seed_value(self.seed_text)
        self.preview_code = self.seed_text.strip()
        self.preview_options = options
        self.preview_seed = seed
        self.preview_version = compatibility(self.preview_code, self.store.base)
        self.preview_rows = preview_rows(self.seed, self.options, seed, options)
        self.preview_page = 0
        self.preview_pages = max(1, (len(self.preview_rows) + 5) // 6)
        self.page = 'seed_preview'
        self.focus = 3
        self.message = ''

    def preview_key(self, key):
        if key == 27 or (key == 13 and self.focus == 3):
            self.page = 'seed'
            self.focus = 4
            return
        if key != 13:
            return
        if self.focus in (0, 1):
            self.preview_page = max(
                0,
                min(
                    self.preview_pages - 1,
                    self.preview_page + (-1 if self.focus == 0 else 1),
                ),
            )
            return
        if self.focus == 2:
            self.import_seed(self.preview_code)
            self.page = 'new'
            self.focus = 0

    def clipboard_access(self):
        if self.clipboard is None:
            from menu_clipboard import Clipboard

            self.clipboard = Clipboard()
        return self.clipboard

    def pump(self):
        if self.clipboard:
            self.clipboard.pump()

    def close(self):
        if self.clipboard:
            self.clipboard.close()
            self.clipboard = None

    def open_seed(self):
        from seed_share import encode as share

        try:
            origin = getattr(self, 'seed_origin', None)
            self.seed_text = (
                origin[0]
                if origin
                and origin[1] == self.seed
                and origin[2] == normalize(self.options)
                else share(self.seed, self.options, self.store.base)
            )
        except ValueError as e:
            self.message = str(display(str(e)))
            return
        self.page = 'seed'
        self.focus = 0
        self.seed_selected = False
        self.message = ''
        self.dirty = True

    def seed_value(self, value):
        if not isinstance(value, str) or not value.strip().startswith('BR12-'):
            raise ValueError(
                tr(
                    'Bitte einen gültigen BR12-Seed einfügen. Alte Seed-Formate werden nicht mehr unterstützt.'
                )
            )
        seed, options = decode(value)
        character(self.store.base, seed, options)
        return seed, options

    def paste_seed(self):
        try:
            value = self.clipboard_access().get()
            seed, options = self.seed_value(value)
            self.seed_text = value.strip()
            self.seed_selected = False
            self.message = tr(
                'Gültiger Seed. Übernehmen lädt auch seine Einstellungen.'
            )
        except Exception as e:
            self.message = tr('Nicht eingefügt: ') + str(display(str(e)))
        self.dirty = True

    def import_seed(self, value):
        seed, options = self.seed_value(value)
        self.seed_origin = (value.strip(), seed, deepcopy(options))
        self.seed = seed
        self.options = options
        self.message = tr('Seed und Einstellungen übernommen.')
        self.dirty = True

    def seed_key(self, key):
        if key == 27:
            self.page = 'new'
            self.focus = 0
            self.message = ''
            return
        if key == 4098:
            self.paste_seed()
            return
        if key == 4099:
            self.copy_seed()
            return
        if key in (38, 40, 9):
            self.focus = (self.focus + (-1 if key == 38 else 1)) % 6
            return
        if self.focus == 0:
            if key == 4097:
                self.seed_selected = True
                return
            if key in (8, 46):
                self.seed_text = (
                    '' if self.seed_selected or key == 46 else self.seed_text[:-1]
                )
                self.seed_selected = False
                self.message = ''
                return
        elif key in (37, 39):
            self.focus = (self.focus + (-1 if key == 37 else 1)) % 6
            return
        if key != 13:
            return
        if self.focus in (0, 4):
            try:
                self.open_preview()
            except ValueError as e:
                self.message = str(display(str(e)))
        elif self.focus == 1:
            # Keep the draft's imported settings when generating a new random seed.
            try:
                _, options = self.seed_value(self.seed_text)
            except ValueError:
                options = deepcopy(self.options)
            from seed_share import encode as share

            self.seed_text = share(
                secrets.token_hex(4).upper(), options, self.store.base
            )
            self.seed_selected = False
            self.message = tr('Neuer Seed erstellt. Mit Übernehmen bestätigen.')
        elif self.focus == 2:
            self.copy_seed()
        elif self.focus == 3:
            self.paste_seed()
        elif self.focus == 5:
            self.seed_key(27)

    def copy_seed(self):
        try:
            seed, options = self.seed_value(self.seed_text)
            self.clipboard_access().put(self.seed_text.strip())
            self.message = tr('Seed mit allen Einstellungen kopiert.')
        except Exception as e:
            self.message = tr('Nicht kopiert: ') + str(display(str(e)))

    def open_characters(self):
        from character_cycle import roster

        self.character_parent = (
            (self.page, self.focus) if self.page == 'advanced' else ('new', 5)
        )
        self.character_names = ['Auto'] + [c['name'] for c in roster(self.store.base)]
        self.focus = self.character_names.index(self.options['start_character'])
        self.page = 'characters'
        self.message = ''

    def character_key(self, key):
        if key == 27 or (key == 13 and self.focus == len(self.character_names)):
            self.page, self.focus = getattr(self, 'character_parent', ('advanced', 2))
            return
        if key in (37, 39, 9):
            self.focus = (self.focus + (-1 if key == 37 else 1)) % len(
                self.character_names
            )
        elif key in (38, 40):
            self.focus = (self.focus + (-7 if key == 38 else 7)) % len(
                self.character_names
            )
        elif key == 13:
            self.options['start_character'] = self.character_names[self.focus]
            self.page, self.focus = getattr(self, 'character_parent', ('advanced', 2))

    def flip_advanced(self, delta):
        old = self.focus
        count = 3 + len(LEVELS) + len(ROUTE_BOSSES)
        self.advanced_page = (self.advanced_page + delta) % ADVANCED_PAGES
        if old in (count + 2, count + 3):
            return
        offset = (
            3 + len(LEVELS)
            if self.options['mode'] == 'boss_rush'
            or (self.options['mode'] != 'level_rush' and 3 + len(LEVELS) <= old < count)
            else 3
        )
        size = len(ROUTE_BOSSES) if offset > 3 else len(LEVELS)
        row = max(0, old - offset) % ADVANCED_PAGE_SIZE
        self.focus = offset + min(
            self.advanced_page * ADVANCED_PAGE_SIZE + row, size - 1
        )

    def advanced_key(self, key):
        count = 3 + len(LEVELS) + len(ROUTE_BOSSES)
        if key == 27:
            self.finish_advanced(False)
            return
        if key == 13 and self.focus in (count + 2, count + 3):
            self.flip_advanced(-1 if self.focus == count + 2 else 1)
            return
        if key == 13 and self.focus < 2:
            name, pool = (
                ('level_count', 'level_pool')
                if self.focus == 0
                else ('route_boss_count', 'boss_pool')
            )
            self.open_choice(
                'Level-Anzahl' if self.focus == 0 else 'Boss-Anzahl',
                [
                    (n, str(n))
                    for n in range(
                        1 if self.options['mode'] in ('boss_rush', 'level_rush') else 0,
                        len(self.options[pool]) + 1,
                    )
                ],
                name,
            )
            return
        if key in (40, 9, 38):
            self.focus = (self.focus + (-1 if key == 38 else 1)) % (count + 2)
            if 3 <= self.focus < count:
                row = self.focus - 3
                row = row if row < len(LEVELS) else row - len(LEVELS)
                self.advanced_page = row // ADVANCED_PAGE_SIZE
            return
        if key != 13:
            return
        if self.focus == count:
            self.finish_advanced(True)
            return
        if self.focus == count + 1:
            self.open_extras()
            return
        if self.focus == 2:
            self.open_characters()
        else:
            i = self.focus - 3
            pool = 'level_pool' if i < len(LEVELS) else 'boss_pool'
            values = list(LEVELS) if pool == 'level_pool' else list(ROUTE_BOSSES)
            name = values[i if pool == 'level_pool' else i - len(LEVELS)]
            if name == 'kappa':
                self.options['route_version'] = max(8, self.options['route_version'])
            elif name in ('save9.ini', 'save10.ini'):
                self.options['route_version'] = max(7, self.options['route_version'])
            elif name in ('kid_icarus_after', 'kid_icarus'):
                self.options['route_version'] = max(6, self.options['route_version'])
            elif (pool == 'level_pool' and name in NEW_LEVELS) or (
                pool == 'boss_pool' and name in MINIBOSSES
            ):
                self.options['route_version'] = max(5, self.options['route_version'])
            elif (pool == 'level_pool' and name not in LEGACY_LEVELS) or (
                pool == 'boss_pool' and name in EXTRA_BOSSES
            ):
                self.options['route_version'] = max(4, self.options['route_version'])
            elif pool == 'boss_pool' and name in ('questionmark', 'ridley'):
                self.options['route_version'] = max(3, self.options['route_version'])
            selected = self.options[pool]
            if name in selected:
                selected.remove(name)
            else:
                selected.append(name)
            number = 'level_count' if pool == 'level_pool' else 'route_boss_count'
            self.options[number] = min(self.options[number], len(selected))
        self.message = ''

    def event(self, kind, a, b):
        if kind == 8:
            self.resolution_recommended = (a, b)
            self.dirty = True
            return
        if kind == 7:
            if 320 <= a <= 16384 and 240 <= b <= 16384 and self.display_size != (a, b):
                self.display_size = (a, b)
                self.dirty = True
            return
        if kind in (3, 5):
            from menu_layout import inverse

            point = inverse((a, b), self.presentation)
            if point is None:
                return
            a, b = point
        if kind == 4:
            if self.page != 'slots':
                return
            self.select(a)
            if b == 1:
                self.key(13)
            elif b == 2:
                self.key(46)
            elif b == 3:
                if not self.open_saved_result():
                    self.page = 'targets'
        elif kind == 1:
            self.key(a)
        elif kind == 2:
            self.char(a)
        elif kind == 3:
            self.click(a, b)
        elif kind == 5:
            self.hover(a, b)

    def open_interval(self):
        self.interval_parent = self.page
        seconds = self.options['extras'].get('shot_interval_seconds', 300)
        self.interval_fields = [str(seconds // 60), str(seconds % 60)]
        self.interval_selected = True
        self.page = 'interval'
        self.focus = 0
        self.message = ''

    def interval_key(self, key):
        if key == 27 or (key == 13 and self.focus == 3):
            self.page = getattr(self, 'interval_parent', 'new')
            self.focus = 5 if self.page == 'shots' else 8
            self.message = ''
            return
        if key in (9, 38, 40):
            self.focus = (self.focus + (-1 if key == 38 else 1)) % 4
            self.interval_selected = True
            return
        if self.focus < 2:
            if key in (8, 46):
                self.interval_fields[self.focus] = (
                    ''
                    if self.interval_selected or key == 46
                    else self.interval_fields[self.focus][:-1]
                )
                self.interval_selected = False
            elif key == 13:
                self.focus += 1
                self.interval_selected = True
        elif key == 13:
            minutes, seconds = (int(v or 0) for v in self.interval_fields)
            total = minutes * 60 + seconds
            if seconds > 59 or not 1 <= total <= 86400:
                self.message = tr(
                    'Sekunden: 0–59. Gesamtzeit: 1 Sekunde bis 24 Stunden.'
                )
                return
            upgrade(self.options)['shot_interval_seconds'] = total
            self.page = getattr(self, 'interval_parent', 'new')
            self.focus = 5 if self.page == 'shots' else 8
            self.message = tr('Zeitgrenze übernommen.')

    def preset_key(self, key):
        if key == 27 or (key == 13 and self.focus == 3):
            self.page = 'new'
            self.focus = 9
            return
        if key in (38, 40, 9):
            self.focus = (self.focus + (-1 if key == 38 else 1)) % 4
        elif key == 13:
            keep = {k: self.options[k] for k in ('mode', 'target_count', 'boss_count')}
            self.options = dict(
                difficulty=1,
                levels=True,
                items=True,
                characters=False,
                **keep,
                **defaults(),
                extras=self.extra_defaults(),
            )
            if self.options['mode'] == 'normal':
                for name, _, _, _ in EXTRAS:
                    self.options['extras'][name] = False
            if self.focus == 1:
                self.options['characters'] = True
                self.options['extras'].update(
                    shot_mode='death_and_spot', death_character=True
                )
            if self.focus == 2:
                self.options['extras'].update(
                    god_mode=True,
                    one_hp=True,
                    autofire=True,
                    skip_intro=True,
                    fast_chests=True,
                )
            if self.options['mode'] == 'normal':
                if self.focus == 0:
                    for name, _, _, _ in EXTRAS:
                        self.options['extras'][name] = False
                self.options = normalize(self.options)
            self.options = normalize(self.options)
            self.message = (tr('Standard'), tr('Chaos'), tr('Training'))[
                self.focus
            ] + tr(' übernommen. Alles bleibt einzeln einstellbar.')
            self.page = 'new'
            self.focus = 9

    def open_result(self, manifest):
        path = self.store.root / manifest['run_id'] / 'summary.json'
        if not path.exists():
            return False
        self.result = json.loads(path.read_text(encoding='utf-8'))
        self.result_manifest = manifest
        self.page = 'result'
        self.focus = 0
        self.message = ''
        self.dirty = True
        return True

    def result_key(self, key):
        if key == 4099 or (key == 13 and self.focus == 2):
            try:
                from seed_share import encode as share
                from runtime_versions import Rules
                from seed_share import encode_saved

                m = self.result_manifest
                rules = Rules(self.store, m)
                code = encode_saved(m['seed'], m['options'], rules.base, rules)
                self.clipboard_access().put(code)
                self.message = tr('Seed mit allen Einstellungen kopiert.')
            except Exception as e:
                self.message = tr('Nicht kopiert: ') + str(display(str(e)))
        elif key in (27, 113) or (key == 13 and self.focus == 1):
            self.page = 'slots'
            self.focus = 0
            self.action = ('result_back', self.slot, None)
        elif key == 13:
            self.reload()
            free = next((i for i in (1, 2, 3) if not self.saves[i]['exists']), None)
            if free is None:
                self.message = tr(
                    'Kein freier Slot. Zurück gehen und zuerst einen Spielstand löschen.'
                )
                return
            self.slot = free
            self.seed = self.result_manifest['seed']
            self.options = deepcopy(self.result_manifest['options'])
            self.page = 'new'
            self.focus = 6
            self.message = tr(
                'Derselbe Seed mit denselben Einstellungen. Enter startet im freien Slot.'
            )
            self.action = ('result_back', self.slot, None)

    def open_saved_result(self):
        m = self.store.current(self.slot)
        return bool(m and m['status'] == 'ready' and self.open_result(m))
