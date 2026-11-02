"""Normal-user Linux setup and Lutris entry point; no root-side downloads."""

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
from pathlib import Path

if __package__:
    from .lifecycle import wait_registration, launch_game
    from .language import tr
    from .lutris_artwork import install_artwork
    from .setup_window import SetupWindow, Cancelled
else:
    from lifecycle import wait_registration, launch_game
    from language import tr
    from lutris_artwork import install_artwork
    from setup_window import SetupWindow, Cancelled


HERE = Path(__file__).resolve().parent
DATA = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share")))
BASE = DATA / "boshy-randomizer-native"
SLUG = "boshy-randomizer-native"


def registered_game():
    """Read Lutris' own database; registration remains owned by Lutris."""
    database = DATA / "lutris/pga.db"
    if not database.exists():
        return None
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as db:
        if not db.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='games'"
        ).fetchone():
            return None  # Lutris may still be creating its first database.
        rows = db.execute(
            "SELECT id FROM games WHERE installer_slug=? AND installed=1", (SLUG,)
        ).fetchall()
    if len(rows) > 1:
        raise RuntimeError(
            tr(
                "Mehrere Boshy-Randomizer-Einträge in Lutris. Bitte den gewünschten Eintrag direkt in Lutris öffnen.",
                "Multiple Boshy Randomizer entries in Lutris. Please open the desired entry directly in Lutris.",
            )
        )
    return rows[0][0] if rows else None


def wine_environment(wine):
    return {
        **os.environ,
        "WINEPREFIX": str(BASE / "wineprefix"),
        "WINEDEBUG": "-all",
        "WINEDLLOVERRIDES": "winemenubuilder.exe=d;mscoree,mshtml=",
        "WINEESYNC": "0",
        "WINEFSYNC": "0",
        "WINE_OPENGL_DRIVER": "glx",
        "__GL_GSYNC_ALLOWED": "0",
        "__GL_VRR_ALLOWED": "0",
    }


def prepare(mode, status, progress=None):
    if os.geteuid() == 0:
        raise RuntimeError(
            tr(
                "Bitte Boshy Randomizer als normalen Benutzer starten.",
                "Please run Boshy Randomizer as your normal user.",
            )
        )
    if not shutil.which("lutris"):
        raise RuntimeError(
            tr(
                "Lutris fehlt. Bitte das DEB mit der Softwareverwaltung installieren.",
                "Lutris is missing. Please install the DEB using your software manager.",
            )
        )
    from wine_setup import ensure_runner

    BASE.mkdir(parents=True, exist_ok=True)
    (BASE / "evidence").mkdir(exist_ok=True)
    if progress is None:
        wine = ensure_runner(status)
    else:
        wine = ensure_runner(status, progress=progress)
    env = wine_environment(wine)
    prefix = BASE / "wineprefix"
    install = prefix / "drive_c/Program Files/Boshy Randomizer"
    marker = BASE / "installed-package.json"
    expected = json.loads((HERE / "package-info.json").read_text())
    current = json.loads(marker.read_text()) if marker.exists() else {}
    if mode == "remove":
        uninstaller = install / "unins000.exe"
        if uninstaller.exists():
            status(
                tr(
                    "Boshy Randomizer wird deinstalliert …",
                    "Uninstalling Boshy Randomizer …",
                )
            )
            subprocess.run([str(wine), str(uninstaller)], env=env, check=True)
            if (install / "active.json").exists():
                raise RuntimeError(
                    tr("Deinstallation abgebrochen.", "Uninstallation cancelled.")
                )
        marker.unlink(missing_ok=True)
        return "remove"
    if mode == "setup" or current != expected or not (install / "active.json").exists():
        status(
            tr(
                "Installationspaket wird geprüft …",
                "Checking the installation package …",
            )
        )
        if (
            hashlib.sha256(
                (HERE / "BoshyRandomizer-Setup.exe").read_bytes()
            ).hexdigest()
            != expected["setup_sha256"]
        ):
            raise RuntimeError(
                tr(
                    "Das Installationspaket ist beschädigt. Bitte das DEB erneut installieren.",
                    "The setup package is damaged. Please reinstall the DEB.",
                )
            )
        status(
            tr(
                "Boshy Randomizer einrichten: Im nächsten Fenster das Originalspiel auswählen.",
                "Set up Boshy Randomizer: select your original game in the next window.",
            )
        )
        if progress is not None:
            progress("wizard", 0, 0)
        with (BASE / "evidence/setup.log").open("w") as log:
            result = subprocess.run(
                [
                    str(wine),
                    str(HERE / "BoshyRandomizer-Setup.exe"),
                    "/DIR=C:\\Program Files\\Boshy Randomizer",
                    "/MERGETASKS=!desktopicon",
                    "/NORESTART",
                ],
                env=env,
                stdout=log,
                stderr=log,
                check=False,
            )
        if result.returncode in (1, 2):
            raise Cancelled()
        result.check_returncode()
        pointer = install / "active.json"
        if (
            not pointer.exists()
            or json.loads(pointer.read_text())["version"] != expected["version"]
        ):
            raise RuntimeError(
                tr(
                    "Einrichtung nicht abgeschlossen. Die bisherige Version bleibt erhalten.",
                    "Setup was not completed. The previous version has been kept.",
                )
            )
        marker.write_text(json.dumps(expected), encoding="utf-8")
    status(
        tr(
            "Lutris-Eintrag und Spielsymbol werden vorbereitet …",
            "Preparing the Lutris entry and game artwork …",
        )
    )
    game_id = registered_game()
    install_artwork(HERE, BASE, game_id)
    if game_id is not None:
        return str(game_id)
    config = json.loads((HERE / "lutris-settings.json").read_text())
    config["wine"]["version"] = wine.parents[1].name
    config["system"].setdefault("env", {})["WINEDLLOVERRIDES"] = (
        "winemenubuilder.exe=d;mscoree,mshtml="
    )
    config["game"] = {
        "arch": "win64",
        "exe": str(install / "BoshyRandomizer.exe"),
        "prefix": str(prefix),
        "args": "",
    }
    document = {
        "name": "Boshy Randomizer",
        "game_slug": "boshy-randomizer",
        "slug": SLUG,
        "runner": "wine",
        "version": "Randomizer",
        "script": {**config, "installer": []},
    }
    installer = BASE / "lutris-installer.json"
    installer.write_text(json.dumps(document, indent=2), encoding="utf-8")
    subprocess.Popen(["lutris", "-i", str(installer)])
    status(
        tr(
            "Bitte die Einrichtung in Lutris abschließen.",
            "Please finish setup in Lutris.",
        )
    )
    try:
        game_id = wait_registration(registered_game, progress or (lambda *args: None))
    except TimeoutError:
        raise RuntimeError(
            tr(
                "Noch kein Lutris-Eintrag gefunden. Schließe die Einrichtung in Lutris ab und versuche es erneut.",
                "No Lutris entry found yet. Finish setup in Lutris and try again.",
            )
        ) from None
    install_artwork(HERE, BASE, int(game_id))
    return game_id


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--setup", action="store_true")
    parser.add_argument("--remove", action="store_true")
    args = parser.parse_args()
    mode = "remove" if args.remove else "setup" if args.setup else "run"

    def work(status, progress):
        import fcntl

        BASE.mkdir(parents=True, exist_ok=True)
        with (BASE / ".setup.lock").open("a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise RuntimeError(
                    tr(
                        "Eine Einrichtung läuft bereits. Bitte zum anderen Installationsfenster wechseln.",
                        "Setup is already running. Please switch to the other setup window.",
                    )
                ) from None
            return prepare(mode, status, progress)

    def launch(game_id, status, progress):
        status(tr("Boshy Randomizer wird gestartet …", "Starting Boshy Randomizer …"))
        try:
            launch_game(DATA, BASE, game_id, progress)
        except TimeoutError:
            raise RuntimeError(
                tr(
                    "Das Spielfenster ist noch nicht erschienen. Prüfe Lutris und das Startprotokoll, bevor du erneut startest.",
                    "The game window has not appeared yet. Check Lutris and the launch log before trying again.",
                )
            ) from None

    SetupWindow(work, mode, BASE / "evidence", tr, launch_work=launch).run()


if __name__ == "__main__":
    main()
