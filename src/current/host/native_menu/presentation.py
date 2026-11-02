from platform_support.fonts import font_path

"""Persistent language and audiovisual package, separate from immutable run plans."""

import configparser
import io
import tempfile
from pathlib import Path
from PIL import ImageFont
from menu_host.store import RC4, atomic, save
from native_menu.preferences import (
    LANGUAGES,
    load_language,
    load_preferences,
    save_preferences,
)
from native_menu.presentation_events import GROUP, INPUT_FILE, VIEW_FILE
from native_menu.options_locale import _picture

from music.packs import PACKS, PACK_NAMES
from music.death_text import animation as caption_animation
LANGUAGE_NAMES = ("Deutsch", "English", "Español", "Русский", "日本語")
LABELS = {
    "language": ("Sprache", "Language", "Idioma", "Язык", "言語"),
    "package": (
        "Musik & Tod",
        "Music & death",
        "Música y muerte",
        "Музыка и смерть",
        "音楽・死亡演出",
    ),
    "language-hint": (
        "Links/rechts: Sprache. Deine Auswahl bleibt nach Neustarts gespeichert.",
        "Left/right: language. Your selection is kept after restarting.",
        "Izquierda/derecha: idioma. La selección se conserva al reiniciar.",
        "Влево/вправо: язык. Выбор сохраняется после перезапуска.",
        "左右：言語。選択は再起動後も保存されます。",
    ),
    "package-hint": (
        "Links/rechts: Musik und Todesdarstellung. Gilt für alle Spielstände; verändert den Seed nicht.",
        "Left/right: music and death presentation. Applies to all saves without changing the seed.",
        "Izquierda/derecha: música y efectos de muerte. Todas las partidas; no cambia la semilla.",
        "Влево/вправо: музыка и эффекты смерти. Для всех сохранений, без изменения сида.",
        "左右：音楽と死亡演出。全セーブ共通。シードは変わりません。",
    ),
}


def write_config(path, groups):
    cfg = configparser.ConfigParser(interpolation=None)
    cfg.optionxform = str
    for name, values in groups.items():
        cfg[name] = {key: str(value) for key, value in values.items()}
    stream = io.StringIO()
    cfg.write(stream)
    atomic(path, RC4(b"BLOB", stream.getvalue().encode("latin1")))


UNAVAILABLE = (
    "{pack} fehlt oder ist beschädigt. Original ist aktiv. Bitte das Soundpaket erneut installieren.",
    "{pack} is missing or damaged. Original is active. Please reinstall the soundpack.",
    "{pack} falta o está dañado. Original está activo. Reinstala el paquete de sonido.",
    "{pack} отсутствует или повреждён. Включён Original. Переустановите звуковой пакет.",
    "{pack}が見つからないか破損しています。Originalに戻しました。サウンドパックを再インストールしてください。",
)


def artwork(folder, language, pack, notice=""):
    root = Path(folder) / "native-options"
    root.mkdir(exist_ok=True)
    font = font_path(language)
    texts = {
        "language-label": LABELS["language"][LANGUAGES.index(language)],
        "package-label": LABELS["package"][LANGUAGES.index(language)],
        "language-value": LANGUAGE_NAMES[LANGUAGES.index(language)],
        "package-value": PACK_NAMES[PACKS.index(pack)],
        **{
            key: LABELS[key][LANGUAGES.index(language)]
            for key in ("language-hint", "package-hint")
        },
    }
    if notice:
        texts["package-hint"] = notice
    for name, text in texts.items():
        hint = name.endswith("hint")
        value = name.endswith("value")
        size = (248, 140) if hint else (225, 49) if value else (113, 49)
        image = _picture(
            text,
            size,
            ImageFont.truetype(font, 12 if hint else 17 if value else 11),
            "white" if hint or value else "#101010",
            language=language,
            y=0 if hint else 8,
        )
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        atomic(root / (name + ".png"), buf.getvalue())


class Presentation:
    def __init__(self, controller):
        self.c = controller
        self.language = load_language(controller.store.root)
        pack = load_preferences(controller.store.root).get(
            "presentation_pack", "original"
        )
        self.pack = pack if pack in PACKS else "original"
        from music.pack_health import PackHealth
        self.health = PackHealth()
        self.notice = ""
        self.generation = 0
        self.signature = None
        self.context = None
        self.music = {"Schema": 1, "Enabled": 0}
        self.write_input()
        self.prepare()

    def write_input(self):
        write_config(
            self.c.folder / INPUT_FILE,
            {
                GROUP: dict(
                    Schema=1,
                    Language=LANGUAGES.index(self.language),
                    Pack=PACKS.index(self.pack),
                    Request=0,
                    Field=0,
                )
            },
        )

    def prepare(self, plan=None):
        if plan and plan["options"].get("mode") == "target":
            from native_menu.target_hud import prepare as prepare_targets
            prepare_targets(self.c.folder, self.language)
        from visuals.embedded_blood import settings, PACK_ROOT
        from music.runtime import prepare as prepare_music

        from music.pack_health import PackUnavailable
        try:
            self.health.check(PACK_ROOT / self.pack, self.pack)
        except PackUnavailable:
            failed = self.pack
            self.pack = "original"
            self.notice = UNAVAILABLE[LANGUAGES.index(self.language)].format(
                pack=PACK_NAMES[PACKS.index(failed)])
            self.c.model.message = self.notice
            save_preferences(self.c.store.root, presentation_pack=self.pack)
            self.write_input()
        from visuals.death_screen import prepare as prepare_death
        prepare_death(self.c.folder, self.pack)

        # A selected external soundtrack works without shuffle; shuffle still
        # draws a reproducible sequence from the existing run seed.
        shuffle = bool(plan and plan["options"]["extras"].get("music", False))
        seed = plan["seed"] if shuffle else "presentation-default"
        enabled = bool(plan) and (shuffle or self.pack != "original")
        context = (self.pack, seed, shuffle, enabled)
        if self.context != context:
            with tempfile.TemporaryDirectory(
                prefix=".presentation-", dir=self.c.folder
            ) as tmp:
                rows, music = prepare_music(
                    tmp, seed, self.pack, PACK_ROOT / self.pack, enabled
                )
                dest = self.c.folder / "presentation-music"
                dest.mkdir(exist_ok=True)
                for row in rows:
                    source = Path(tmp) / "native-music" / row["file"]
                    target = dest / row["file"]
                    if not target.exists():
                        source.replace(target)
                self.music = {
                    key: (
                        value.replace("native-music\\", "presentation-music\\")
                        if isinstance(value, str)
                        else value
                    )
                    for key, value in music.items()
                }
            self.context = context
        from music.title import prepare as prepare_title, GROUP as TITLE_GROUP

        title_music = prepare_title(self.c.folder, self.pack, PACK_ROOT / self.pack)
        # Generation is the game's reload signal. Finish *all* Options artwork
        # before publishing it; the later menu refresh must not supply labels
        # after the game has already acknowledged this generation.
        from native_menu.options_locale import prepare as prepare_options_locale

        prepare_options_locale(self.c.folder, self.language)
        artwork(self.c.folder, self.language, self.pack, self.notice)
        from gameplay.dresser import prepare as prepare_dresser

        prepare_dresser(self.c.folder, self.language)
        self.generation += 1
        write_config(
            self.c.folder / VIEW_FILE,
            {
                GROUP: dict(
                    Schema=1,
                    Generation=self.generation,
                    Language=LANGUAGES.index(self.language),
                    Pack=PACKS.index(self.pack),
                ),
                "FusionMusicV1": self.music,
                TITLE_GROUP: title_music,
                "FusionBloodV1": {
                    **settings(self.pack),
                    "CaptionAnimation": caption_animation(self.language),
                },
            },
        )

    def current_plan(self):
        import json

        slot = getattr(self.c, "active_slot", None)
        return (
            json.loads((self.c.store.folder(slot) / "plan.json").read_text())
            if slot
            else None
        )

    def tick(self):
        path = self.c.folder / INPUT_FILE
        signature = path.stat().st_mtime_ns
        if self.signature == signature:
            return
        try:
            cfg = save(path)
            lang = cfg.getint(GROUP, "Language")
            pack = cfg.getint(GROUP, "Pack")
            if not 0 <= lang < len(LANGUAGES) or not 0 <= pack < len(PACKS):
                return
        except (OSError, ValueError, configparser.Error):
            return
        self.signature = signature
        changes = {}
        if LANGUAGES[lang] != self.language:
            self.language = LANGUAGES[lang]
            changes["language"] = self.language
        if PACKS[pack] != self.pack:
            self.pack = PACKS[pack]
            self.notice = ""
            changes["presentation_pack"] = self.pack
        if not changes:
            return
        self.prepare(self.current_plan())
        if "presentation_pack" in changes:
            changes["presentation_pack"] = self.pack
        save_preferences(self.c.store.root, **changes)
        self.c.model.language = self.language
        self.c.mail.publish()
