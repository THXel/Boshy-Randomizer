"""Shared native menu captions, separated from navigation and run mutations."""

from native_menu.shot_labels import CAPTIONS as SHOT_CAPTIONS
from native_menu.feature_labels import CAPTIONS as FEATURE_CAPTIONS
from native_menu.appearance_labels import CAPTIONS as APPEARANCE_CAPTIONS
from native_menu import display

CAPTIONS = {
    "level_count": (
        "Anzahl Level",
        "Number of levels",
        "Número de niveles",
        "Количество уровней",
        "ステージ数",
    ),
    "route_boss_count": (
        "Anzahl Bosse",
        "Number of bosses",
        "Número de jefes",
        "Количество боссов",
        "ボス数",
    ),
    "start_character": (
        "Startcharakter",
        "Starting character",
        "Personaje inicial",
        "Начальный персонаж",
        "開始キャラクター",
    ),
    "auto_character": (
        "Automatisch",
        "Automatic",
        "Automático",
        "Автоматически",
        "自動",
    ),
    "mode": (
        "Spielmodus",
        "Run mode",
        "Modo de partida",
        "Режим забега",
        "ゲームモード",
    ),
    "randomizer": (
        "Randomizer",
        "Randomizer",
        "Aleatorio",
        "Рандомайзер",
        "ランダマイザー",
    ),
    "boss_rush": (
        "Boss Rush",
        "Boss Rush",
        "Solo jefes",
        "Марафон боссов",
        "ボスラッシュ",
    ),
    "level_rush": (
        "Level Rush",
        "Level Rush",
        "Solo niveles",
        "Марафон уровней",
        "ステージラッシュ",
    ),
    "route_required": (
        "Mindestens ein Level oder Boss muss ausgewählt bleiben.",
        "Keep at least one level or boss selected.",
        "Selecciona al menos un nivel o jefe.",
        "Оставьте хотя бы один уровень или босса.",
        "ステージかボスを最低1つ選んでください。",
    ),
    "clipboard_failed": (
        "Zwischenablage nicht verfügbar. Bitte erneut versuchen.",
        "Clipboard unavailable. Please try again.",
        "Portapapeles no disponible. Inténtalo de nuevo.",
        "Буфер обмена недоступен. Повторите попытку.",
        "クリップボードを利用できません。もう一度お試しください。",
    ),
    "operation_failed": (
        "Der Vorgang konnte nicht abgeschlossen werden. Details stehen im Fehlerprotokoll.",
        "The operation could not be completed. Details are in the error log.",
        "No se pudo completar la operación. Consulta el registro de errores.",
        "Не удалось завершить операцию. Подробности в журнале ошибок.",
        "処理を完了できませんでした。詳細はエラーログをご確認ください。",
    ),
    "settings": ("Einstellungen", "Settings", "Ajustes", "Настройки", "設定"),
    "back": ("Zurück", "Back", "Volver", "Назад", "戻る"),
    "language": ("Sprache", "Language", "Idioma", "Язык", "言語"),
    "exit": ("Beenden", "Quit", "Salir", "Выход", "終了"),
    "page": ("Seite", "Page", "Página", "Страница", "ページ"),
    "copy_seed": (
        "Seed kopieren (F6)",
        "Copy seed (F6)",
        "Copiar semilla (F6)",
        "Копировать сид (F6)",
        "シードをコピー (F6)",
    ),
    "import_seed": (
        "Seed einfügen (F7)",
        "Paste seed (F7)",
        "Pegar semilla (F7)",
        "Вставить сид (F7)",
        "シードを貼り付け (F7)",
    ),
    "renew_seed": (
        "Neuer Seed (F5)",
        "New seed (F5)",
        "Nueva semilla (F5)",
        "Новый сид (F5)",
        "新しいシード (F5)",
    ),
    "locked": (
        "Einstellungen gehören zum gespeicherten Lauf.",
        "Settings belong to the saved run.",
        "Los ajustes pertenecen a la partida guardada.",
        "Настройки закреплены за сохранённым забегом.",
        "設定は保存済みルートに固定されています。",
    ),
    "copied": (
        "Seed kopiert.",
        "Seed copied.",
        "Semilla copiada.",
        "Сид скопирован.",
        "シードをコピーしました。",
    ),
    "invalid_seed": (
        "Seed konnte nicht übernommen werden.",
        "Could not import seed.",
        "No se pudo importar la semilla.",
        "Не удалось импортировать сид.",
        "シードを読み込めませんでした。",
    ),
}

CAPTIONS.update(APPEARANCE_CAPTIONS)
from native_menu.target_labels import CAPTIONS as TARGET_CAPTIONS

CAPTIONS.update(TARGET_CAPTIONS)


from native_menu import history

CAPTIONS.update(history.CAPTIONS)
CAPTIONS.update(FEATURE_CAPTIONS)
CAPTIONS.update(SHOT_CAPTIONS)
CAPTIONS.update(display.CAPTIONS)
from native_menu.preset_labels import CAPTIONS as PRESET_CAPTIONS

CAPTIONS.update(PRESET_CAPTIONS)
CAPTIONS["diagnostics"] = (
    "Diagnose",
    "Diagnostics",
    "Diagnóstico",
    "Диагностика",
    "診断",
)

# Explicit state words remain readable when color or small glyphs are hard to see.
CAPTIONS.update(
    {
        "state_on": ("AN", "ON", "SÍ", "ВКЛ", "オン"),
        "state_off": ("AUS", "OFF", "NO", "ВЫКЛ", "オフ"),
        "current_seed": (
            "Aktueller Seed",
            "Current seed",
            "Semilla actual",
            "Текущий сид",
            "現在のシード",
        ),
        "collected_items": ("Gegenstände", "Items", "Objetos", "Предметы", "アイテム"),
        "collected_characters": (
            "Charaktere",
            "Characters",
            "Personajes",
            "Персонажи",
            "キャラクター",
        ),
        "nothing_collected": (
            "Noch keine",
            "None yet",
            "Aún ninguno",
            "Пока нет",
            "まだなし",
        ),
        "music": (
            "Musik mischen",
            "Shuffle music",
            "Mezclar música",
            "Случайная музыка",
            "音楽シャッフル",
        ),
    }
)

CAPTIONS.update({
    "font_size": ("Menüschrift", "Menu text", "Texto del menú", "Шрифт меню", "メニュー文字"),
    "font_normal": ("Normal", "Standard", "Normal", "Обычный", "標準"),
    "font_large": ("Groß", "Large", "Grande", "Крупный", "大"),
})
