"""Presentation-only localization. Game IDs, names, seeds and logs are never rewritten."""
from functools import lru_cache
import json
import os
from pathlib import Path
import re
import string
import sys

SUPPORTED = ('en', 'de', 'ru', 'es', 'ja')
ROOT = Path(__file__).resolve().parent


def _code(value):
    return str(value).strip().split('.', 1)[0].split('@', 1)[0].replace('-', '_').split('_', 1)[0].lower()


def detect_language(environ=None, system_locale=None):
    """Explicit override, gettext preferences, message locale, then OS configuration.

    An unsupported first locale falls back to English. LANGUAGE is an ordered
    preference list and may contain a supported secondary language.
    """
    env = os.environ if environ is None else environ
    if env.get('BOSHY_LANGUAGE'):
        language = _code(env['BOSHY_LANGUAGE'])
        return language if language in SUPPORTED else 'en'
    if env.get('LANGUAGE'):
        for value in env['LANGUAGE'].split(':'):
            language = _code(value)
            if language in SUPPORTED:
                return language
        return 'en'
    for key in ('LC_ALL', 'LC_MESSAGES', 'LANG'):
        if env.get(key):
            language = _code(env[key])
            return language if language in SUPPORTED else 'en'
    if system_locale is None:
        for path in ('/etc/default/locale', '/etc/locale.conf'):
            try:
                text = Path(path).read_text(encoding='utf-8')
            except OSError:
                continue
            values = dict(re.findall(r'^(LANG|LC_MESSAGES)=["\']?([^"\'\n]+)', text, re.M))
            system_locale = values.get('LC_MESSAGES', values.get('LANG'))
            if system_locale:
                break
    language = _code(system_locale or 'en')
    return language if language in SUPPORTED else 'en'


LANGUAGE = detect_language()


class Localized(str):
    """Avoid looking up an already translated value a second time."""


@lru_cache(maxsize=5)
def catalog(language):
    try:
        data = json.loads((ROOT / 'locales' / (language + '.json')).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        if language == 'en':
            raise RuntimeError('Required English language catalog is missing or invalid.')
        return {}
    if not isinstance(data, dict):
        raise RuntimeError('Invalid language catalog: ' + language)
    return data


def tr(message, *args):
    if isinstance(message, Localized) and not args:
        return message
    fallback = catalog('en').get(message, message)
    translated = catalog(LANGUAGE).get(message, fallback)
    if not isinstance(translated, str) or not translated:
        translated = fallback
    if args:
        try:
            translated = translated.format(*args)
        except (IndexError, KeyError, ValueError):
            translated = fallback.format(*args)
    return Localized(translated)


def display(value):
    """Localize known display values supplied by immutable rule modules.

    Only complete known messages and these explicitly defined label templates
    are matched. No substring replacement in names, seeds or diagnostic data.
    """
    if isinstance(value, Localized):
        return value
    text = str(value)
    if text in catalog('en'):
        return tr(text)
    if ', ' in text and '(Raum ' in text:
        return Localized(', '.join(str(display(v)) for v in text.split(', ')))
    room = re.fullmatch(r'(.+) \(Raum ([0-9]+)\)', text)
    if room:
        return tr('{0} (Raum {1})', display(room.group(1)), room.group(2))
    for pattern, message in (
        (r'Welt ([0-9½]+) · (.+)', 'Welt {0} · {1}'),
        (r'Szene ([0-9]+|None)', 'Szene {0}'),
        (r'Zufällig bis ([0-9]+:[0-9]{2}) · Enter', 'Zufällig bis {0} · Enter'),
    ):
        match = re.fullmatch(pattern, text)
        if match:
            return tr(message, *match.groups())
    if text.startswith('Schussstil: '):
        return Localized(tr('Schussstil: ') + str(display(text[len('Schussstil: '):])))
    for message, pattern in _display_patterns():
        match = pattern.fullmatch(text)
        if match:
            return tr(message, *(display(v) for v in match.groups()))
    # A list of diagnostic exit rooms may include multiple independent labels.
    if ', ' in text and '(Raum ' in text:
        return Localized(', '.join(str(display(v)) for v in text.split(', ')))
    return text


@lru_cache(maxsize=1)
def _display_patterns():
    patterns = []
    for message in catalog('en'):
        fields = list(string.Formatter().parse(message))
        names = [field for _, field, _, _ in fields if field is not None]
        if names and names == [str(i) for i in range(len(names))]:
            pattern = ''.join(re.escape(literal) + ('(.+?)' if field is not None else '')
                              for literal, field, _, _ in fields)
            patterns.append((message, re.compile(pattern)))
    return patterns


@lru_cache(maxsize=1)
def font_path():
    candidates = ([
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',
    ] if LANGUAGE == 'ja' else []) + ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf']
    for name in candidates:
        if Path(name).is_file():
            if LANGUAGE == 'ja' and 'DejaVu' in name:
                raise RuntimeError('Japanese requires Noto Sans CJK: install fonts-noto-cjk.')
            return name
    raise RuntimeError('Install fonts-dejavu-core and fonts-noto-cjk.')


def font_family():
    return 'Noto Sans CJK JP' if LANGUAGE == 'ja' else 'DejaVu Sans'


def configure_tk(root):
    import tkinter.font as font
    for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont', 'TkTooltipFont'):
        try:
            font.nametofont(name, root=root).configure(family=font_family())
        except Exception:
            pass


if __name__ == '__main__':
    print(tr(sys.argv[1]) if len(sys.argv) > 1 else LANGUAGE)
