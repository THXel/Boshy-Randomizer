# Localization

The randomizer UI supports `en`, `de`, `ru`, `es` and `ja`.

Detection order: `BOSHY_LANGUAGE` (explicit override), the ordered `LANGUAGE` preference list, `LC_ALL`, `LC_MESSAGES`, `LANG`, then `/etc/default/locale` or `/etc/locale.conf` when environment locale information is absent. Locale suffixes and region codes are normalized; unsupported locales use English. A missing translation also falls back to the required English catalog.

For example, `BOSHY_LANGUAGE=ja ./start-linux.sh` selects Japanese. Normal desktop launches inherit the desktop language. This override changes display only; it is not stored in a shared seed.

Catalogs are UTF-8 JSON in `assets/locales/`. German source messages serve as gettext-style lookup IDs. Numbered placeholders must occur exactly as in the English catalog. Proper names, save keys, seed text and raw debug data must never be translated.

The custom menu is rendered to Unicode-capable images. Japanese uses Noto Sans CJK (`fonts-noto-cjk` on Debian/Mint), with a Droid CJK fallback for bitmap rendering. Other languages use DejaVu Sans (`fonts-dejavu-core`). Tk widgets use Noto Sans CJK JP for Japanese. Install the Noto package for reliable Japanese text across both renderers.

The original game message window uses an ANSI text engine. `menu_updates.json` and the message window heading deliberately remain English in every language. Original game artwork/text and its Options screen are not replaced.

Translate only at presentation boundaries. Frozen rule modules and canonical machine-readable debug reports remain unchanged. Use `tr()` for literal templates and `display()` only for known display values from those modules.
