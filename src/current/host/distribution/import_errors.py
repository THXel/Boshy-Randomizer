"""Actionable installer messages for rejected originals; no source paths echoed."""

import errno


class OriginalImportError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


MESSAGES = {
    "file_count": (
        "Der gewählte Ordner oder das ZIP enthält mehr als 20.000 Dateien. Wähle den eigentlichen Boshy-Spielordner ohne Sicherungs- und Cache-Unterordner oder ein unverändertes Original-ZIP.",
        "The selected folder or ZIP contains more than 20,000 files. Select the actual Boshy game folder without backup/cache folders, or an unmodified original ZIP.",
    ),
    "file_size": (
        "Eine Datei im gewählten Ordner oder ZIP ist größer als 500 MB. Wähle den eigentlichen Originalspielordner oder das Original-ZIP ohne zusätzliche Dateien.",
        "A file in the selected folder or ZIP exceeds 500 MB. Select the original game folder or ZIP without unrelated files.",
    ),
    "total_size": (
        "Der gewählte Ordner oder das entpackte ZIP ist größer als 2 GB. Wähle nur den Originalspielordner oder das unveränderte Original-ZIP.",
        "The selected folder or expanded ZIP exceeds 2 GB. Select only the original game folder or the unmodified original ZIP.",
    ),
    "multiple_games": (
        "Es wurden mehrere Boshy-Spielkopien gefunden. Wähle genau den Unterordner einer einzigen Originalkopie oder ein Original-ZIP mit nur einem Spiel.",
        "More than one Boshy game copy was found. Select the subfolder of one original copy, or an original ZIP containing only one game.",
    ),
    "missing_game": (
        "Die Datei „I Wanna Be The Boshy.exe“ wurde nicht gefunden. Wähle den Ordner mit dieser Datei oder das unveränderte Original-ZIP.",
        "I Wanna Be The Boshy.exe was not found. Select the folder containing that file, or the unmodified original ZIP.",
    ),
    "unsupported_game": (
        "Die Spiel-Datei entspricht nicht dem unterstützten Original. Wähle das unveränderte Original, nicht eine bereits modifizierte Randomizer-Version.",
        "The game file does not match the supported original. Select the unmodified original, not an already modified Randomizer version.",
    ),
    "links": (
        "Der ausgewählte Ordner oder das ZIP enthält Verknüpfungen. Wähle eine echte entpackte Originalkopie oder das unveränderte Original-ZIP.",
        "The selected folder or ZIP contains links. Select a real extracted original copy or the unmodified original ZIP.",
    ),
    "source_type": (
        "Bitte wähle einen entpackten Originalspielordner oder eine ZIP-Datei.",
        "Please select an extracted original game folder or a ZIP file.",
    ),
    "unsafe_path": (
        "Das Original enthält einen nicht unterstützten Dateipfad. Verwende eine unveränderte Originalkopie als ZIP oder entpackten Ordner.",
        "The original contains an unsupported file path. Use an unmodified original ZIP or extracted folder.",
    ),
    "duplicate_path": (
        "Das Original enthält doppelte oder nur durch Großschreibung unterschiedliche Dateipfade. Verwende eine unveränderte Originalkopie.",
        "The original contains duplicate file paths or paths differing only in letter case. Use an unmodified original copy.",
    ),
    "disk_full": (
        "Auf dem Installationslaufwerk ist nicht genügend freier Speicher verfügbar. Gib Speicher frei und starte die Einrichtung erneut.",
        "The installation drive does not have enough free space. Free some space and run Setup again.",
    ),
    "access": (
        "Eine benötigte Datei ist nicht zugänglich. Schließe das Spiel und prüfe die Zugriffsrechte des ausgewählten Ordners.",
        "A required file is inaccessible. Close the game and check access permissions for the selected folder.",
    ),
    "generic": (
        "Die Einrichtung konnte nicht abgeschlossen werden. Schließe das Spiel und wähle ein unverändertes Original-ZIP oder einen Originalspielordner. Der technische Bericht enthält weitere Einzelheiten.",
        "Setup could not finish. Close the game and select an unmodified original ZIP or game folder. The technical report contains more details.",
    ),
}


MESSAGES["cancelled"] = (
    "Installation abgebrochen. Die aktive Version und Spielstände bleiben erhalten.",
    "Installation cancelled. The active version and saves have been kept.",
)

TRANSLATIONS = {
    "file_count": (
        "Hay más de 20.000 archivos. Selecciona solo la carpeta del juego original o su ZIP, sin copias ni cachés.",
        "Более 20 000 файлов. Выбери только папку оригинала или ZIP без копий и кэша.",
        "ファイルが20,000個を超えています。バックアップやキャッシュを除いたオリジナルのフォルダーまたはZIPを選択してください。",
    ),
    "file_size": (
        "Un archivo supera los 500 MB. Selecciona el original sin archivos adicionales.",
        "Файл превышает 500 МБ. Выбери оригинал без лишних файлов.",
        "500 MBを超えるファイルがあります。追加ファイルのないオリジナルを選択してください。",
    ),
    "total_size": (
        "El contenido supera los 2 GB. Selecciona solo el juego original.",
        "Размер превышает 2 ГБ. Выбери только оригинальную игру.",
        "内容が2 GBを超えています。オリジナルゲームのみを選択してください。",
    ),
    "multiple_games": (
        "Se encontraron varias copias. Selecciona una única copia del original.",
        "Найдено несколько копий. Выбери одну копию оригинала.",
        "複数のゲームが見つかりました。オリジナルを1つだけ含むフォルダーまたはZIPを選択してください。",
    ),
    "missing_game": (
        "No se encontró I Wanna Be The Boshy.exe. Selecciona la carpeta que lo contiene o el ZIP original.",
        "Файл I Wanna Be The Boshy.exe не найден. Выбери папку с ним или ZIP оригинала.",
        "I Wanna Be The Boshy.exeが見つかりません。このファイルを含むフォルダーまたは元のZIPを選択してください。",
    ),
    "unsupported_game": (
        "El juego no coincide con el original compatible. Selecciona una copia sin modificar.",
        "Игра не совпадает с поддерживаемым оригиналом. Выбери неизменённую копию.",
        "対応するオリジナルと一致しません。未改変のゲームを選択してください。",
    ),
    "links": (
        "La carpeta o el ZIP contiene enlaces. Selecciona una copia real del original.",
        "Папка или ZIP содержит ссылки. Выбери настоящую копию оригинала.",
        "フォルダーまたはZIPにリンクが含まれています。オリジナルの実体を選択してください。",
    ),
    "source_type": (
        "Selecciona una carpeta del juego original o un archivo ZIP.",
        "Выбери папку оригинальной игры или ZIP-архив.",
        "オリジナルゲームのフォルダーまたはZIPを選択してください。",
    ),
    "unsafe_path": (
        "Hay una ruta no compatible. Usa una copia original sin modificar.",
        "Неподдерживаемый путь. Используй неизменённую копию оригинала.",
        "対応していないパスが含まれています。未改変のオリジナルを使用してください。",
    ),
    "duplicate_path": (
        "Hay rutas duplicadas o que solo difieren en mayúsculas. Usa una copia original sin modificar.",
        "Есть одинаковые пути или отличающиеся только регистром. Используй неизменённый оригинал.",
        "重複するパスまたは大文字・小文字のみ異なるパスがあります。未改変のオリジナルを使用してください。",
    ),
    "disk_full": (
        "No hay espacio libre suficiente. Libera espacio e inténtalo de nuevo.",
        "Недостаточно свободного места. Освободи место и повтори попытку.",
        "空き容量が不足しています。空き容量を増やして再試行してください。",
    ),
    "access": (
        "No se puede acceder a un archivo. Cierra el juego y comprueba los permisos.",
        "Нет доступа к файлу. Закрой игру и проверь права доступа.",
        "必要なファイルにアクセスできません。ゲームを終了し、アクセス権を確認してください。",
    ),
    "generic": (
        "No se completó la instalación. Cierra el juego y selecciona el original sin modificar. Consulta el informe para más detalles.",
        "Установка не завершена. Закрой игру и выбери неизменённый оригинал. Подробности в отчёте.",
        "セットアップを完了できませんでした。ゲームを終了し、未改変のオリジナルを選択してください。詳細はレポートを確認してください。",
    ),
    "cancelled": (
        "Instalación cancelada. La versión activa y las partidas se conservan.",
        "Установка отменена. Текущая версия и сохранения оставлены.",
        "インストールを中止しました。現在のバージョンとセーブデータは保持されています。",
    ),
}
for _code, _texts in TRANSLATIONS.items():
    MESSAGES[_code] += _texts


def explanation(error, language="english"):
    code = getattr(error, "code", "generic")
    if (
        getattr(error, "errno", None) == errno.ENOSPC
        or getattr(error, "winerror", None) == 112
    ):
        code = "disk_full"
    elif isinstance(error, PermissionError):
        code = "access"
    index = {"german": 0, "english": 1, "spanish": 2, "russian": 3, "japanese": 4}.get(
        language, 1
    )
    return MESSAGES.get(code, MESSAGES["generic"])[index]
