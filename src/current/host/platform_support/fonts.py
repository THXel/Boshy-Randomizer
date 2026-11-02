"""Identical bundled fonts on both platforms, with private Linux fallbacks."""

import os
from pathlib import Path
from app_paths import LAB


def font_path(language="en"):
    name = "NotoSansCJK-Regular.ttc" if language == "ja" else "DejaVuSans.ttf"
    bundled = LAB / "resources/fonts" / name
    if bundled.is_file():
        return str(bundled)
    if os.name != "nt":
        folder = (
            "/usr/share/fonts/opentype/noto"
            if language == "ja"
            else "/usr/share/fonts/truetype/dejavu"
        )
        path = Path(folder) / name
        if path.is_file():
            return str(path)
    raise FileNotFoundError("Required application font is missing: " + name)
