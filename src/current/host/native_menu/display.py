"""Local presentation preferences and aspect-preserving window geometry.

The game world stays 640x480. 16:9 is an explicit presentation stretch only.
Display preferences are independent of route seeds and saved run progress.
"""

from dataclasses import dataclass
from native_menu.preferences import load_preferences, save_preferences

ASPECTS = ("4:3", "16:9")
HEIGHTS = (480, 720, 1080, 1440, 2160)


@dataclass(frozen=True)
class Settings:
    aspect: str = "4:3"
    height: int = 480
    fullscreen: bool = False

    def __post_init__(self):
        if (
            type(self.fullscreen) is not bool
            or self.aspect not in ASPECTS
            or type(self.height) is not int
            or self.height not in HEIGHTS
        ):
            raise ValueError("Invalid display preference")

    @property
    def size(self):
        n, d = (int(x) for x in self.aspect.split(":"))
        width = (
            854
            if self.aspect == "16:9" and self.height == 480
            else round(self.height * n / d)
        )
        return (width, self.height)

    def fit(self, available):
        """Largest requested rectangle fitting the monitor; never crop content."""
        width, height = self.size
        if self.fullscreen:
            n, d = map(int, self.aspect.split(":"))
            height = available[1]
            width = height * n / d
        scale = min(1, available[0] / width, available[1] / height)
        return (max(1, round(width * scale)), max(1, round(height * scale)))

    def changed(self, field, direction):
        if field == "aspect":
            return Settings(
                ASPECTS[(ASPECTS.index(self.aspect) + direction) % len(ASPECTS)],
                self.height,
                self.fullscreen,
            )
        if field == "height":
            return Settings(
                self.aspect,
                HEIGHTS[(HEIGHTS.index(self.height) + direction) % len(HEIGHTS)],
                self.fullscreen,
            )
        if field == "fullscreen":
            return Settings(self.aspect, self.height, not self.fullscreen)
        raise ValueError(field)


def load(root):
    data = load_preferences(root).get("display", {})
    try:
        return Settings(data["aspect"], data["height"], data.get("fullscreen", False))
    except (KeyError, ValueError, TypeError):
        return Settings()


def save(root, settings):
    save_preferences(
        root,
        display=dict(
            aspect=settings.aspect,
            height=settings.height,
            fullscreen=settings.fullscreen,
        ),
    )


CAPTIONS = {
    "fullscreen": (
        "Fenstervollbild (F4)",
        "Borderless fullscreen (F4)",
        "Pantalla completa (F4)",
        "Полный экран (F4)",
        "全画面（F4）",
    ),
    "display": ("Anzeige", "Display", "Pantalla", "Экран", "画面"),
    "aspect": (
        "Seitenverhältnis",
        "Aspect ratio",
        "Relación de aspecto",
        "Соотношение сторон",
        "アスペクト比",
    ),
    "resolution": ("Auflösung", "Resolution", "Resolución", "Разрешение", "解像度"),
    "aspect_original": (
        "4:3 · Original",
        "4:3 · Original",
        "4:3 · Original",
        "4:3 · Оригинал",
        "4:3 · オリジナル",
    ),
    "aspect_stretched": (
        "16:9 · Gestreckt",
        "16:9 · Stretched",
        "16:9 · Estirado",
        "16:9 · Растянутый",
        "16:9 · 引き伸ばし",
    ),
    "display_hint": (
        "Nur die Darstellung ändert sich. Spielfläche und Seed bleiben gleich.",
        "Changes presentation only. Playfield and seed stay the same.",
        "Solo cambia la presentación. El área de juego y la semilla se conservan.",
        "Меняется только отображение. Игровое поле и сид сохраняются.",
        "表示のみ変更します。ゲーム領域とシードは変わりません。",
    ),
}


def prepare_options(folder, settings):
    """Publish presentation into the original options file, preserving controls."""
    import configparser
    import io
    from menu_host.store import RC4, atomic

    path = folder / "options.ini"
    cfg = configparser.ConfigParser(interpolation=None)
    # Ini++ writes lowercase keys; merge case-insensitively to avoid stale duplicates.
    cfg.optionxform = str.lower
    if path.exists():
        from native_menu.preferences import read_native_settings

        cfg = read_native_settings(path)
    if not cfg.has_section("Options"):
        cfg.add_section("Options")
    # Original ShowDeaths display defaults to ON, but its left-arrow handler
    # defaults to OFF when the key is absent. Materialize the visible default.
    if not any(k.lower() == "showdeaths" for k in cfg["Options"]):
        cfg["Options"]["ShowDeaths"] = "1"
    if not any(k.lower() == "musicrestart" for k in cfg["Options"]):
        cfg["Options"]["MusicRestart"] = "0"
    cfg["Options"].update(
        {
            "DisplayConfigured": "1",
            "DisplayFullscreen": str(int(settings.fullscreen)),
            "DisplayIndex": str(HEIGHTS.index(settings.height)),
            "DisplayHeight": str(settings.height),
            "DisplayAspect": str(ASPECTS.index(settings.aspect)),
            "ScreenSize": str(settings.size[0]),
        }
    )
    stream = io.StringIO()
    cfg.write(stream)
    atomic(path, RC4(b"BLOB", stream.getvalue().encode("latin1")))


def from_options(folder):
    from menu_host.store import save as read_save

    path = folder / "options.ini"
    if not path.exists():
        return None
    cfg = read_save(path)
    if cfg.getint("Options", "DisplayConfigured", fallback=0) != 1:
        return None
    aspect = cfg.getint("Options", "DisplayAspect", fallback=0)
    if aspect not in (0, 1):
        raise ValueError("Display aspect")
    return Settings(
        ASPECTS[aspect],
        cfg.getint("Options", "DisplayHeight", fallback=480),
        cfg.getint("Options", "DisplayFullscreen", fallback=0) == 1,
    )
