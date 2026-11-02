"""Original Options room labels; keys and native controls remain unchanged."""

from menu_host.labels import LANGUAGES

# label object, selector object, optional value object, saved key, translations
ROWS = (
    (
        1338,
        1337,
        1336,
        "MusicVolume",
        (
            "Musiklautstärke",
            "Music volume",
            "Volumen de música",
            "Громкость музыки",
            "音楽の音量",
        ),
    ),
    (
        1340,
        1339,
        1348,
        "SpeechVolume",
        (
            "Sprachlautstärke",
            "Speech volume",
            "Volumen de voces",
            "Громкость речи",
            "ボイスの音量",
        ),
    ),
    (
        1364,
        1363,
        1365,
        "ScreenSize",
        ("Anzeige", "Display", "Pantalla", "Экран", "画面"),
    ),
    (
        1344,
        1343,
        None,
        "Controls",
        ("Steuerung", "Controls", "Controles", "Управление", "操作設定"),
    ),
    (
        1355,
        1354,
        1356,
        "SpecialJumpingSounds",
        (
            "Sprunggeräusche",
            "Jump sounds",
            "Sonidos de salto",
            "Звуки прыжка",
            "ジャンプ音",
        ),
    ),
    (
        1362,
        1360,
        1361,
        "SpecialShootingSounds",
        (
            "Schussgeräusche",
            "Shot sounds",
            "Sonidos de disparo",
            "Звуки выстрелов",
            "発射音",
        ),
    ),
    (
        1377,
        1379,
        1378,
        "DigDugWalkSound",
        ("Laufgeräusche", "Walk sounds", "Sonidos al caminar", "Звуки шагов", "歩行音"),
    ),
    (
        1375,
        1374,
        1376,
        "SpecialShootingGraphics",
        (
            "Schussgrafiken",
            "Shot graphics",
            "Gráficos de disparo",
            "Вид выстрелов",
            "弾の見た目",
        ),
    ),
    (
        1352,
        1350,
        1351,
        "MusicRestart",
        (
            "Musik neu starten",
            "Restart music",
            "Reiniciar música",
            "Перезапуск музыки",
            "音楽を再開",
        ),
    ),
    (
        1358,
        1357,
        1359,
        "BloodEffect",
        (
            "Koop-Todeseffekte",
            "Co-op death effects",
            "Efectos de muerte coop.",
            "Эффекты смерти в кооп.",
            "協力プレイの死亡演出",
        ),
    ),
    (
        1368,
        1367,
        1369,
        "BloodIntense",
        (
            "Blutmenge",
            "Blood intensity",
            "Cantidad de sangre",
            "Количество крови",
            "血の量",
        ),
    ),
    (
        1372,
        1371,
        1373,
        "FPS",
        (
            "FPS-Anzeige (F8)",
            "FPS display (F8)",
            "Mostrar FPS (F8)",
            "Счётчик FPS (F8)",
            "FPS表示 (F8)",
        ),
    ),
    (
        1380,
        1381,
        1382,
        "ONTRAN",
        (
            "Koop-Transparenz",
            "Co-op transparency",
            "Transparencia coop.",
            "Прозрачность в кооп.",
            "協力プレイの透明度",
        ),
    ),
    (
        1385,
        1384,
        1386,
        "FrameRate",
        (
            "Bildratenlimit",
            "Frame rate limit",
            "Límite de FPS",
            "Ограничение FPS",
            "フレームレート制限",
        ),
    ),
    (
        1388,
        1387,
        1347,
        "Mirror",
        (
            "Spiegelmodus",
            "Mirror mode",
            "Modo espejo",
            "Зеркальный режим",
            "ミラーモード",
        ),
    ),
    (
        1389,
        1390,
        1391,
        "ShowDeaths",
        (
            "Todeszähler",
            "Death counter",
            "Contador de muertes",
            "Счётчик смертей",
            "死亡回数表示",
        ),
    ),
    (
        1349,
        1346,
        None,
        "OnlineLicenseCharacter",
        (
            "Online-Figur",
            "Online character",
            "Personaje online",
            "Сетевой персонаж",
            "オンラインキャラ",
        ),
    ),
)
TOGGLES = frozenset(
    (
        "SpecialJumpingSounds",
        "SpecialShootingSounds",
        "DigDugWalkSound",
        "SpecialShootingGraphics",
        "MusicRestart",
        "BloodEffect",
        "FPS",
        "Mirror",
        "ShowDeaths",
    )
)
HINTS = {
    "volume": (
        "Mit Links/Rechts die Lautstärke ändern.",
        "Use left/right to change the volume.",
        "Usa izquierda/derecha para cambiar el volumen.",
        "Громкость: стрелки влево/вправо.",
        "左右キーで音量を変更します。",
    ),
    "ScreenSize": (
        "←/→: Auflösung. Enter: 4:3/16:9. F4: Vollbild.",
        "←/→: Resolution. Enter: 4:3/16:9. F4: Fullscreen.",
        "←/→: Resolución. Enter: 4:3/16:9. F4: Pantalla completa.",
        "←/→: Разрешение. Enter: 4:3/16:9. F4: Полный экран.",
        "←/→：解像度。Enter：4:3／16:9。F4：全画面。",
    ),
    "Controls": (
        "Enter öffnet die originale Tastenbelegung.",
        "Enter opens the original control setup.",
        "Enter abre la configuración original de controles.",
        "Enter: настройка исходного управления.",
        "Enterで元のキー設定を開きます。",
    ),
    "SpecialJumpingSounds": (
        "Figurenspezifische Sprunggeräusche ein-/ausschalten.",
        "Toggle character-specific jump sounds.",
        "Activa o desactiva los sonidos de salto del personaje.",
        "Звуки прыжка выбранного персонажа.",
        "キャラ固有のジャンプ音を切り替えます。",
    ),
    "SpecialShootingSounds": (
        "Figurenspezifische Schussgeräusche ein-/ausschalten.",
        "Toggle character-specific shot sounds.",
        "Activa o desactiva los sonidos de disparo del personaje.",
        "Звуки выстрелов выбранного персонажа.",
        "キャラ固有の発射音を切り替えます。",
    ),
    "DigDugWalkSound": (
        "Laufmusik und Laufgeräusch von Dig Dug ein-/ausschalten.",
        "Toggle Dig Dug walking music and sound.",
        "Activa o desactiva el sonido al caminar de Dig Dug.",
        "Музыка и звук ходьбы Dig Dug.",
        "Dig Dugの歩行音・音楽を切り替えます。",
    ),
    "SpecialShootingGraphics": (
        "Figurenspezifische Schussgrafiken ein-/ausschalten.",
        "Toggle character-specific shot graphics.",
        "Activa o desactiva los gráficos de disparo del personaje.",
        "Вид выстрелов выбранного персонажа.",
        "キャラ固有の弾の見た目を切り替えます。",
    ),
    "MusicRestart": (
        "Aus: Musik läuft bei Tod und Neustart weiter.",
        "Off: keep music playing through death and restart.",
        "Desactivado: la música continúa al morir y reiniciar.",
        "Выкл.: музыка продолжается после смерти и перезапуска.",
        "オフ：死亡・リスタート時も音楽を継続します。",
    ),
    "BloodEffect": (
        "Originale Blutdarstellung für andere Spieler im Koop-Modus.",
        "Original blood effects for other co-op players.",
        "Sangre original de otros jugadores en cooperativo.",
        "Эффекты крови других игроков в кооперативе.",
        "協力プレイで他プレイヤーの血を表示します。",
    ),
    "BloodIntense": (
        "Links/Rechts: Anzahl der Blutpartikel beim Tod.",
        "Left/right: number of blood particles on death.",
        "Izquierda/derecha: partículas de sangre al morir.",
        "Влево/вправо: количество частиц крови при смерти.",
        "左右：死亡時に出る血の粒子数。",
    ),
    "FPS": (
        "FPS-Anzeige im Spiel ein-/ausschalten; auch mit F8.",
        "Toggle the in-game FPS counter; also available with F8.",
        "Muestra u oculta los FPS; también con F8.",
        "Счётчик FPS в игре; также доступен по F8.",
        "ゲーム内FPS表示を切り替えます。F8も使えます。",
    ),
    "ONTRAN": (
        "Originale Koop-Transparenz: 0 sichtbar, 255 unsichtbar.",
        "Original co-op transparency: 0 visible, 255 invisible.",
        "Transparencia coop.: 0 visible, 255 invisible.",
        "Прозрачность: 0 — видимый, 255 — невидимый.",
        "協力プレイの透明度：0で表示、255で非表示。",
    ),
    "FrameRate": (
        "Originales Bildratenlimit: 50 bis 1000.",
        "Original frame rate limit: 50 to 1000.",
        "Límite original de FPS: de 50 a 1000.",
        "Исходное ограничение FPS: от 50 до 1000.",
        "元のフレームレート制限：50～1000。",
    ),
    "Mirror": (
        "Die originale Spiegelung der Spielwelt ein-/ausschalten.",
        "Toggle the original playfield mirroring.",
        "Activa o desactiva el modo espejo original.",
        "Зеркальное отражение игрового мира.",
        "元のゲーム画面の左右反転を切り替えます。",
    ),
    "ShowDeaths": (
        "Todeszähler während des Spielens anzeigen.",
        "Show the death counter during gameplay.",
        "Muestra el contador de muertes durante la partida.",
        "Показывать число смертей во время игры.",
        "プレイ中の死亡回数を表示します。",
    ),
    "OnlineLicenseCharacter": (
        "Originale Einstellung für eine gespeicherte Online-Figur.",
        "Original setting for a saved online character.",
        "Ajuste original para el personaje online guardado.",
        "Исходная настройка сохранённого сетевого персонажа.",
        "保存済みオンラインキャラの元の設定です。",
    ),
    "controls_keys": (
        "Taste 1: Springen\nTaste 2: Schießen\nTaste 3: Neustart",
        "Button 1: jump\nButton 2: shoot\nButton 3: restart",
        "Botón 1: saltar\nBotón 2: disparar\nBotón 3: reiniciar",
        "Кнопка 1: прыжок\nКнопка 2: выстрел\nКнопка 3: заново",
        "ボタン1：ジャンプ\nボタン2：発射\nボタン3：リスタート",
    ),
    "room_help": (
        "Pfeiltasten: Auswahl und Werte\nEnter: Bestätigen\nEsc: Zurück\n\nGesammelte CDs: Zifferntasten",
        "Arrow keys: select and adjust\nEnter: confirm\nEsc: back\n\nCollected CDs: number keys",
        "Flechas: elegir y ajustar\nEnter: confirmar\nEsc: volver\n\nCD obtenidos: teclas numéricas",
        "Стрелки: выбор и изменение\nEnter: подтвердить\nEsc: назад\n\nСобранные CD: цифровые клавиши",
        "方向キー：選択・変更\nEnter：決定\nEsc：戻る\n\n入手したCD：数字キー",
    ),
    "on": ("AN", "ON", "SÍ", "ВКЛ", "オン"),
    "off": ("AUS", "OFF", "NO", "ВЫКЛ", "オフ"),
}


def label(row, language):
    return row[4][LANGUAGES.index(language)]


def hint(key, language):
    return HINTS["volume" if key in ("MusicVolume", "SpeechVolume") else key][
        LANGUAGES.index(language)
    ]
