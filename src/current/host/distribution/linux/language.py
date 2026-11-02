"""Setup translations with the same five locales as the game."""

import json
import locale
from pathlib import Path

TEXT = json.loads(
    Path(__file__).with_name("translations.json").read_text(encoding="utf-8")
)


def language():
    code = (locale.getlocale()[0] or "en").split("_")[0].lower()
    return code if code in ("de", "en", "es", "ru", "ja") else "en"


def tr(german, english):
    code = language()
    if code == "de":
        return german
    if code == "en":
        return english
    return TEXT.get(english, [english] * 3)[("es", "ru", "ja").index(code)]
