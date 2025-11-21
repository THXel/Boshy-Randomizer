==============================================================
                    BOSHY RANDOMIZER
        Erstellt von THXel & der Boshy Speedrun Community
                          © 2025 THXel
==============================================================

Moderner Randomizer für „I Wanna Be The Boshy“
Zufällige Routen • Live Tracker • Seed-System • Klare GUI

--------------------------------------------------------------
FEATURES
--------------------------------------------------------------
• Zufällige Level- und Bossreihenfolge
• Stabiles Handling von Items und Collectables
• Zufällige Charaktere – beim Start oder pro Stage
• Target Collect Mode – Sammle alle Ziele, Route verborgen
• Live Tracker – Achievements, Items, Bosse, Charaktere
• Endscreen-Statistiken inkl. Route Code
• Deterministische Seeds – identische Runs reproduzierbar
• Automatisches Setup – Python, Module, Fonts, Spielimport

--------------------------------------------------------------
VORAUSSETZUNGEN
--------------------------------------------------------------
• Windows 10 oder neuer
• Internetverbindung für die erste Einrichtung
• Eine legale Kopie von „I Wanna Be The Boshy“ (ZIP von Grynsoft)

--------------------------------------------------------------
DOWNLOAD & INSTALLATION
--------------------------------------------------------------

ZIP-Download:
https://github.com/THXel/Boshy-Randomizer/archive/refs/heads/Boshy-Randomizer.zip

1) Lade die ZIP-Datei herunter.

2) Entpacke die ZIP-Datei an einem beliebigen Ort, z. B.:
   C:\Games\Boshy Randomizer\

   Nach dem Entpacken sollte der Ordner so aussehen:

      Boshy Randomizer/
       ├─ Custom/
       ├─ INI/
       ├─ PY/
       ├─ Installer Files...
       └─ Boshy Randomizer Installer.exe

3) Starte den Installer:
   Boshy Randomizer Installer.exe

   Der Installer führt automatisch aus:
   • Kopieren aller Randomizer-Dateien
   • Installation von Python 3.x (falls nicht vorhanden)
   • Installation aller benötigten Module
   • Installation der „its-boshy-time“-Schriftart
   • Abfrage deiner IWBTB-ZIP
   • Entpacken des Spiels in /IWBTB
   • Anlegen von Startmenü-Verknüpfungen

4) Starte den Randomizer:
   Startmenü → Boshy Randomizer

   Der Launcher prüft automatisch:
   • ob das IWBTB-Spiel korrekt importiert wurde
   • ob Python installiert ist
   • ob alle Module vorhanden sind
   • ob alle Randomizer-Dateien existieren

   Bei Problemen erscheint eine klare Debug-Meldung.

--------------------------------------------------------------
GAMEPLAY & MODI
--------------------------------------------------------------

RUN-START
• Jeder Run beginnt im Tutorial.
• Danach wechselt das Spiel je nach GUI:
  – Zufällige Route
  – Target Collect Mode

CHARAKTER-RANDOMIZER
• Standardcharakter: Dark Boshy
• Optional:
  – Zufällig beim Run-Start
  – Zufällig pro Stage
• Während Random Character aktiv ist:
  Das F3-Charaktermenü ist deaktiviert.

--------------------------------------------------------------
TARGET COLLECT MODE
--------------------------------------------------------------

• Routensteuerung wird ausgeblendet.
• Alle notwendigen optionalen Level werden aktiviert.
• Ziele werden Seed-basiert ausgewählt.
• Wenn alle Ziele gesammelt wurden:
  Solgryn erscheint automatisch als Endboss.

WICHTIG:
Nur diese optionalen Bereiche dürfen deaktiviert werden:
• Boberman
• Questionmark (?)
• Ridley

Alle anderen optionalen Bereiche müssen aktiv bleiben,
um alle Items erreichen zu können.

--------------------------------------------------------------
SYSTEMVERHALTEN
--------------------------------------------------------------

• Es wird ausschließlich SaveFile1 verwendet.
• SaveFile1 darf NICHT gelöscht werden.
• SaveFile2 und SaveFile3 werden immer überschrieben.
• Achievements und Unlockables bleiben für den gesamten Run erhalten.
• Der Teleport-Raum funktioniert normal, aber:
  Um weiterzukommen, MUSS das Level gespielt werden,
  das der Randomizer vorgibt. Überspringen ist nicht möglich.

--------------------------------------------------------------
SEED-SYSTEM
--------------------------------------------------------------

Ein Seed definiert:
• Level- und Bossreihenfolge
• komplette Routenstruktur
• optionale Charakter-RNG
• die Zielauswahl im Target Mode

Ein Seed wird angezeigt:
• im Lade-Overlay
• im Run-Start-Overlay
• im Endscreen
• im Debug-Log

Seeds können geteilt werden, um identische Runs zu spielen.

--------------------------------------------------------------
BEKANNTE HINWEISE
--------------------------------------------------------------

• Einige Trigger sind absichtlich leicht versetzt.
• Benutzerdefinierte Savefiles oder Mods können stören.

--------------------------------------------------------------
TECHNISCHE INFORMATIONEN
--------------------------------------------------------------

• Python 3.11
• Verwendete Bibliotheken:
  pygetwindow, pyautogui, pillow, numpy, tkinter

Debug-Log-Datei:
INI/randomizer_debug.log

--------------------------------------------------------------
SUPPORT
--------------------------------------------------------------

Twitch:
https://twitch.tv/THXel

Discord:
https://discord.gg/ZXgTFjGw

--------------------------------------------------------------
HAFTUNGSAUSSCHLUSS
--------------------------------------------------------------

Dieses Projekt ist inoffiziell und steht in keiner Verbindung zu
Solgryn (Grynsoft) oder offiziellen IWBTB-Veröffentlichungen.

Nutzung auf eigene Gefahr.
Viel Spaß – It's Boshy Time!
--------------------------------------------------------------
