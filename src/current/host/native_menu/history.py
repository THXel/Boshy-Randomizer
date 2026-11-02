"""Verified user-facing changes, shared by the title card and paged history."""

from menu_host.labels import LANGUAGES

CAPTIONS = {
    "updates": (
        "Update-Verlauf",
        "Update history",
        "Historial de cambios",
        "История обновлений",
        "更新履歴",
    ),
    "menu_keys": (
        "Pfeiltasten: Auswahl\nEnter: Öffnen\nEntf: Save löschen",
        "Arrow keys: select\nEnter: choose\nDelete: erase save",
        "Flechas: elegir\nEnter: abrir\nSupr: borrar partida",
        "Стрелки: выбор\nEnter: открыть\nDelete: удалить",
        "方向キー：選択\nEnter：決定\nDelete：セーブ削除",
    ),
}
ENTRIES = (
    (
        "2026-11-02",
        (
            "1.0.1: Fenstergröße bleibt beim Reset und Raumwechsel erhalten",
            "1.0.1: Window size stays unchanged on resets and room changes",
            "1.0.1: El tamaño de ventana se conserva al reiniciar y cambiar de sala",
            "1.0.1: Размер окна сохраняется при сбросе и смене комнаты",
            "1.0.1：リセットや部屋移動でもウィンドウサイズを維持",
        ),
    ),
    (
        "2026-11-02",
        (
            "Version 1.0.0 – die erste Veröffentlichung",
            "Version 1.0.0 – the first release",
            "Versión 1.0.0 – primer lanzamiento",
            "Версия 1.0.0 — первый выпуск",
            "バージョン1.0.0 — 正式リリース",
        ),
    ),
    (
        "2026-11-02",
        (
            "Fünf Spielmodi, eigene Routen und teilbare Seeds",
            "Five modes, custom routes and shareable seeds",
            "Cinco modos, rutas propias y semillas para compartir",
            "Пять режимов, свои маршруты и общие сиды",
            "5つのモード・ルート設定・シード共有",
        ),
    ),
    (
        "2026-11-02",
        (
            "Drei Spielstände mit Vorschau und Charakterauswahl",
            "Three save slots with previews and character selection",
            "Tres partidas con vista previa y elección de personaje",
            "Три сохранения с обзором и выбором персонажа",
            "プレビュー付きの3つのセーブとキャラクター選択",
        ),
    ),
    (
        "2026-11-02",
        (
            "Target Select: Ziele direkt im Spiel aufklappen",
            "Target Select: open your checklist in-game",
            "Target Select: consulta tus objetivos en el juego",
            "Target Select: список целей прямо в игре",
            "Target Select：目標リストをゲーム内で表示",
        ),
    ),
    (
        "2026-11-02",
        (
            "Sprites, Hintergründe und Schüsse nach deinen Regeln",
            "Sprites, backgrounds and shots, your way",
            "Sprites, fondos y disparos a tu gusto",
            "Спрайты, фоны и выстрелы по твоим правилам",
            "スプライト・背景・弾を好みに合わせて変更",
        ),
    ),
    (
        "2026-11-02",
        (
            "Original- oder Undertale-Soundtrack mit Todeseffekten",
            "Original or Undertale soundtrack and death effects",
            "Música original o de Undertale y efectos de muerte",
            "Оригинальная музыка или Undertale и эффекты смерти",
            "オリジナル・Undertaleの音楽と死亡演出",
        ),
    ),
    (
        "2026-11-02",
        (
            "Sprache, Musik und Anzeige dauerhaft im Optionsraum",
            "Language, music and display saved in Options",
            "Idioma, música y pantalla guardados en Opciones",
            "Язык, музыка и экран сохраняются в настройках",
            "言語・音楽・画面設定をオプションで保存",
        ),
    ),
    (
        "2026-11-02",
        (
            "LiveTracker: Zeit, Tode, Items und Ziele im Blick",
            "LiveTracker: time, deaths, items and targets",
            "LiveTracker: tiempo, muertes, objetos y objetivos",
            "LiveTracker: время, смерти, предметы и цели",
            "LiveTracker：タイム・死亡回数・アイテム・目標",
        ),
    ),
    (
        "2026-11-02",
        (
            "Schnelles Speichern und Neustarten, Originalposition im Tower",
            "Responsive saves and resets; original Tower arrival",
            "Guardados y reinicios ágiles; entrada original a Tower",
            "Быстрое сохранение и перезапуск; исходная позиция в Tower",
            "素早いセーブ・リセットとTowerの本来の開始位置",
        ),
    ),
)


def entries(language):
    index = LANGUAGES.index(language)
    return [(date, captions[index]) for date, captions in ENTRIES]


TITLE_CARD = {
    "de": (
        "BOSHY RANDOMIZER 1.0.1",
        "02.11.2026 · Fenstergröße korrigiert",
        "Dein Run\n5 Modi · eigene Routen · Seeds teilen",
        "Dein Look\nSprites · Hintergründe · Schüsse",
        "Dein Sound\nOriginal · Undertale · eigene Packs",
        "Dein Fortschritt\nLiveTracker · Ziele direkt im Spiel",
    ),
    "en": (
        "BOSHY RANDOMIZER 1.0.1",
        "2026-11-02 · Window size fix",
        "Your run\n5 modes · custom routes · share seeds",
        "Your look\nSprites · backgrounds · shots",
        "Your sound\nOriginal · Undertale · custom packs",
        "Your progress\nLiveTracker · in-game targets",
    ),
    "es": (
        "BOSHY RANDOMIZER 1.0.1",
        "02-11-2026 · Tamaño de ventana corregido",
        "Tu partida\n5 modos · rutas propias · semillas",
        "Tu estilo\nSprites · fondos · disparos",
        "Tu música\nOriginal · Undertale · packs",
        "Tu progreso\nLiveTracker · objetivos en el juego",
    ),
    "ru": (
        "BOSHY RANDOMIZER 1.0.1",
        "02.11.2026 · Исправлен размер окна",
        "Твой забег\n5 режимов · маршруты · общие сиды",
        "Твой стиль\nСпрайты · фоны · выстрелы",
        "Твоя музыка\nОригинал · Undertale · пакеты",
        "Твой прогресс\nLiveTracker · цели в игре",
    ),
    "ja": (
        "BOSHY RANDOMIZER 1.0.1",
        "2026-11-02 · ウィンドウサイズを修正",
        "自分だけのラン\n5つのモード・ルート・シード共有",
        "自分だけの見た目\nスプライト・背景・弾",
        "自分だけの音楽\nオリジナル・Undertale・追加パック",
        "進行をひと目で\nLiveTracker・ゲーム内の目標",
    ),
}
