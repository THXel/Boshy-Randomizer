"""Localized Undertale encouragement; presentation only, outside the run seed."""
LANGUAGES = ("de", "en", "es", "ru", "ja")
MESSAGES = {
    "de": "Boshy!\nBleib entschlossen...",
    "en": "Boshy!\nStay determined...",
    "es": "¡Boshy!\nMantén tu determinación...",
    "ru": "Boshy!\nНе теряй решимости...",
    "ja": "Boshy!\nケツイを ちからに。",
}
ANIMATIONS = {language: 16 + index for index, language in enumerate(LANGUAGES)}


def animation(language):
    return ANIMATIONS.get(language, ANIMATIONS["en"])
